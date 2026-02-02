"""Webhook для приёма уведомлений от ЮKassa."""

import json
import logging

from aiohttp import web

from bot.services import db

logger = logging.getLogger(__name__)


async def yookassa_webhook(request: web.Request) -> web.Response:
    """
    Обработка webhook-уведомлений от ЮKassa.
    ЮKassa отправляет POST-запрос при изменении статуса платежа.
    """
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return web.Response(status=400, text="Bad JSON")

    event = body.get("event")
    payment_obj = body.get("object", {})
    yookassa_id = payment_obj.get("id")

    if not yookassa_id:
        return web.Response(status=400, text="No payment id")

    logger.info("Webhook получен: event=%s, payment_id=%s", event, yookassa_id)

    bot = request.app.get("bot")

    if event == "payment.succeeded":
        payment = await db.confirm_payment(yookassa_id)
        if payment:
            # Получаем заказ с деталями для уведомления пользователя
            order = await db.get_order_with_items(payment.order_id)
            if order and bot:
                # Собираем ссылки на материалы
                lines = ["🎉 <b>Оплата прошла успешно!</b>\n"]
                lines.append(f"Заказ #{order.id}\n")
                lines.append("Вот ссылки на материалы курсов:\n")
                for item in order.items:
                    lines.append(
                        f"📖 <b>{item.course.title}</b>\n"
                        f"   🔗 {item.course.material_url}"
                    )

                try:
                    await bot.send_message(
                        chat_id=order.user.telegram_id,
                        text="\n".join(lines),
                        parse_mode="HTML",
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    logger.error("Ошибка при отправке уведомления: %s", e)

    elif event == "payment.canceled":
        payment = await db.cancel_payment(yookassa_id)
        if payment:
            order = await db.get_order_with_items(payment.order_id)
            if order and bot:
                try:
                    await bot.send_message(
                        chat_id=order.user.telegram_id,
                        text=f"❌ Оплата заказа #{order.id} отменена.\n"
                             "Попробуй ещё раз через /start → Корзина.",
                    )
                except Exception as e:
                    logger.error("Ошибка при отправке уведомления: %s", e)

    # ЮKassa ожидает 200 OK
    return web.Response(status=200, text="OK")


def setup_webhook_routes(app: web.Application) -> None:
    """Регистрация маршрутов webhook."""
    app.router.add_post("/webhook/yookassa", yookassa_webhook)
