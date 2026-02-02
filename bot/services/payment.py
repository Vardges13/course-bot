"""Сервис оплаты через ЮKassa."""

import uuid

from yookassa import Configuration, Payment as YooPayment

from bot.config import config

# Инициализация SDK
Configuration.account_id = config.yookassa_shop_id
Configuration.secret_key = config.yookassa_secret


def create_payment(amount: float, order_id: int, description: str) -> dict:
    """
    Создать платёж в ЮKassa.
    Возвращает dict с ключами: id, confirmation_url.
    """
    idempotency_key = str(uuid.uuid4())
    payment = YooPayment.create(
        {
            "amount": {
                "value": f"{amount:.2f}",
                "currency": "RUB",
            },
            "confirmation": {
                "type": "redirect",
                "return_url": f"{config.webhook_host}/payment/success?order_id={order_id}",
            },
            "capture": True,
            "description": description,
            "metadata": {
                "order_id": str(order_id),
            },
        },
        idempotency_key,
    )
    return {
        "id": payment.id,
        "confirmation_url": payment.confirmation.confirmation_url,
    }


def get_payment_info(payment_id: str) -> dict:
    """Получить информацию о платеже."""
    payment = YooPayment.find_one(payment_id)
    return {
        "id": payment.id,
        "status": payment.status,
        "amount": payment.amount.value,
        "metadata": payment.metadata,
    }
