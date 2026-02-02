"""Точка входа — запуск бота и webhook-сервера."""

import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.models import init_db
from bot.handlers import register_routers
from bot.handlers.payment import setup_webhook_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def on_startup(app: web.Application) -> None:
    """Инициализация при старте."""
    logger.info("Инициализация базы данных...")
    await init_db()
    logger.info("БД готова.")


async def on_shutdown(app: web.Application) -> None:
    """Очистка при остановке."""
    bot: Bot = app["bot"]
    await bot.session.close()
    logger.info("Бот остановлен.")


async def main() -> None:
    """Главная функция запуска."""
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()
    register_routers(dp)

    # aiohttp-сервер для webhook ЮKassa
    app = web.Application()
    app["bot"] = bot
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    setup_webhook_routes(app)

    # Запускаем webhook-сервер в фоне
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.webhook_port)
    await site.start()
    logger.info("Webhook-сервер запущен на порту %s", config.webhook_port)

    # Запускаем polling
    logger.info("Бот запущен, polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
