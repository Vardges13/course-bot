"""Конфигурация бота — загрузка переменных из .env."""

from pathlib import Path
from dataclasses import dataclass, field

from dotenv import load_dotenv
import os

# Загружаем .env из корня проекта
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass
class Config:
    bot_token: str = field(default_factory=lambda: os.getenv("BOT_TOKEN", ""))
    yookassa_shop_id: str = field(default_factory=lambda: os.getenv("YOOKASSA_SHOP_ID", ""))
    yookassa_secret: str = field(default_factory=lambda: os.getenv("YOOKASSA_SECRET", ""))
    admin_ids: list[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
    ])
    webhook_host: str = field(default_factory=lambda: os.getenv("WEBHOOK_HOST", ""))
    webhook_port: int = field(default_factory=lambda: int(os.getenv("WEBHOOK_PORT", "8080")))
    database_url: str = field(default_factory=lambda: os.getenv(
        "DATABASE_URL", "sqlite+aiosqlite:///data/bot.db"
    ))


config = Config()
