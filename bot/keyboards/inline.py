"""Инлайн-клавиатуры бота."""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.models import Course


# ─── Главное меню ─────────────────────────────────────────────

def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📚 Каталог курсов", callback_data="catalog"),
    )
    builder.row(
        InlineKeyboardButton(text="🛒 Корзина", callback_data="cart"),
    )
    builder.row(
        InlineKeyboardButton(text="📦 Мои курсы", callback_data="my_courses"),
    )
    return builder.as_markup()


# ─── Каталог ──────────────────────────────────────────────────

def catalog_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.row(
            InlineKeyboardButton(
                text=f"{course.title} — {course.price:.0f} ₽",
                callback_data=f"course:{course.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="« Назад", callback_data="main_menu"))
    return builder.as_markup()


def course_detail_kb(course_id: int, in_cart: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if in_cart:
        builder.row(
            InlineKeyboardButton(
                text="❌ Убрать из корзины", callback_data=f"cart_remove:{course_id}"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text="🛒 В корзину", callback_data=f"cart_add:{course_id}"
            )
        )
    builder.row(InlineKeyboardButton(text="« Каталог", callback_data="catalog"))
    return builder.as_markup()


# ─── Корзина ──────────────────────────────────────────────────

def cart_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.row(
            InlineKeyboardButton(
                text=f"❌ {course.title}",
                callback_data=f"cart_remove:{course.id}",
            )
        )
    if courses:
        builder.row(
            InlineKeyboardButton(text="💳 Оплатить", callback_data="checkout")
        )
    builder.row(InlineKeyboardButton(text="« Главное меню", callback_data="main_menu"))
    return builder.as_markup()


# ─── Админ ────────────────────────────────────────────────────

def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить курс", callback_data="admin:add_course"),
    )
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить курс", callback_data="admin:delete_course"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика продаж", callback_data="admin:stats"),
    )
    return builder.as_markup()


def admin_courses_delete_kb(courses: list[Course]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for course in courses:
        builder.row(
            InlineKeyboardButton(
                text=f"🗑 {course.title}",
                callback_data=f"admin:del:{course.id}",
            )
        )
    builder.row(InlineKeyboardButton(text="« Админ-панель", callback_data="admin:menu"))
    return builder.as_markup()


def back_to_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="« Админ-панель", callback_data="admin:menu"))
    return builder.as_markup()
