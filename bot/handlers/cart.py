"""Обработчики корзины: добавление, удаление, просмотр, оформление заказа."""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from bot.services import db
from bot.services.payment import create_payment
from bot.keyboards import cart_kb, main_menu_kb

router = Router()

# Корзина хранится в памяти бота (dict[telegram_id] -> list[course_id]).
# Для production-среды лучше хранить в Redis или БД.


def _get_cart(bot: Bot, user_id: int) -> list[int]:
    """Получить корзину пользователя из bot-данных."""
    key = f"cart:{user_id}"
    if not hasattr(bot, "_cart_data"):
        bot._cart_data = {}
    return bot._cart_data.get(key, [])


def _set_cart(bot: Bot, user_id: int, cart: list[int]) -> None:
    if not hasattr(bot, "_cart_data"):
        bot._cart_data = {}
    bot._cart_data[f"cart:{user_id}"] = cart


# Делаем корзину доступной через bot.get() для других хендлеров
# Monkey-patch Bot.get для совместимости
_original_bot_class = Bot

def _bot_get_cart(bot: Bot, key: str, default=None):
    if not hasattr(bot, "_cart_data"):
        bot._cart_data = {}
    return bot._cart_data.get(key, default)

Bot.get = _bot_get_cart


# ─── Добавить в корзину ──────────────────────────────────────

@router.callback_query(F.data.startswith("cart_add:"))
async def add_to_cart(callback: CallbackQuery) -> None:
    course_id = int(callback.data.split(":")[1])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    cart = _get_cart(callback.bot, callback.from_user.id)
    if course_id in cart:
        await callback.answer("Курс уже в корзине")
        return

    cart.append(course_id)
    _set_cart(callback.bot, callback.from_user.id, cart)
    await callback.answer(f"✅ «{course.title}» добавлен в корзину")


# ─── Убрать из корзины ────────────────────────────────────────

@router.callback_query(F.data.startswith("cart_remove:"))
async def remove_from_cart(callback: CallbackQuery) -> None:
    course_id = int(callback.data.split(":")[1])
    cart = _get_cart(callback.bot, callback.from_user.id)
    if course_id in cart:
        cart.remove(course_id)
        _set_cart(callback.bot, callback.from_user.id, cart)
        await callback.answer("Удалено из корзины")
    else:
        await callback.answer("Курса нет в корзине")

    # Обновляем отображение корзины
    await show_cart(callback)


# ─── Просмотр корзины ─────────────────────────────────────────

@router.callback_query(F.data == "cart")
async def show_cart(callback: CallbackQuery) -> None:
    cart_ids = _get_cart(callback.bot, callback.from_user.id)
    if not cart_ids:
        await callback.message.edit_text(
            "🛒 Корзина пуста.\n\nДобавь курсы из каталога!",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    courses = []
    for cid in cart_ids:
        course = await db.get_course(cid)
        if course and course.is_active:
            courses.append(course)

    if not courses:
        _set_cart(callback.bot, callback.from_user.id, [])
        await callback.message.edit_text(
            "🛒 Корзина пуста.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    total = sum(float(c.price) for c in courses)
    lines = ["🛒 <b>Корзина</b>\n"]
    for c in courses:
        lines.append(f"• {c.title} — {c.price:.0f} ₽")
    lines.append(f"\n<b>Итого: {total:.0f} ₽</b>")
    lines.append("\nНажми ❌ чтобы убрать курс, или 💳 Оплатить:")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=cart_kb(courses),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Оформление заказа ────────────────────────────────────────

@router.callback_query(F.data == "checkout")
async def checkout(callback: CallbackQuery) -> None:
    cart_ids = _get_cart(callback.bot, callback.from_user.id)
    if not cart_ids:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    user = await db.get_or_create_user(
        telegram_id=callback.from_user.id,
        full_name=callback.from_user.full_name,
        username=callback.from_user.username,
    )

    order = await db.create_order(user, cart_ids)
    if not order:
        await callback.answer("Не удалось создать заказ", show_alert=True)
        return

    # Создаём платёж в ЮKassa
    course_titles = ", ".join(item.course.title for item in order.items)
    description = f"Оплата курсов: {course_titles}"[:128]

    payment_data = create_payment(
        amount=float(order.total_amount),
        order_id=order.id,
        description=description,
    )

    # Сохраняем запись о платеже в БД
    await db.create_payment_record(
        order_id=order.id,
        yookassa_id=payment_data["id"],
        amount=float(order.total_amount),
    )

    # Очищаем корзину
    _set_cart(callback.bot, callback.from_user.id, [])

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате", url=payment_data["confirmation_url"])],
        [InlineKeyboardButton(text="« Главное меню", callback_data="main_menu")],
    ])

    await callback.message.edit_text(
        f"✅ Заказ #{order.id} создан!\n\n"
        f"Сумма: <b>{order.total_amount:.0f} ₽</b>\n\n"
        "Нажми кнопку ниже для перехода к оплате:",
        reply_markup=kb,
        parse_mode="HTML",
    )
    await callback.answer()
