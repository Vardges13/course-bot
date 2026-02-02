"""Обработчики /start, главное меню, каталог, «Мои курсы»."""

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from bot.services import db
from bot.keyboards import main_menu_kb, catalog_kb, course_detail_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие + главное меню."""
    user = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )
    await message.answer(
        f"Привет, {user.full_name}! 👋\n\n"
        "Я бот с онлайн-курсами. Выбери, что тебе интересно:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Главное меню — выбери действие:",
        reply_markup=main_menu_kb(),
    )
    await callback.answer()


# ─── Каталог ──────────────────────────────────────────────────

@router.callback_query(F.data == "catalog")
async def show_catalog(callback: CallbackQuery) -> None:
    courses = await db.get_active_courses()
    if not courses:
        await callback.answer("Курсов пока нет 😔", show_alert=True)
        return
    await callback.message.edit_text(
        "📚 <b>Каталог курсов</b>\n\nВыбери курс для подробностей:",
        reply_markup=catalog_kb(courses),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("course:"))
async def show_course_detail(callback: CallbackQuery) -> None:
    course_id = int(callback.data.split(":")[1])
    course = await db.get_course(course_id)
    if not course:
        await callback.answer("Курс не найден", show_alert=True)
        return

    # Проверяем, есть ли курс уже в корзине
    cart: list[int] = callback.bot.get(f"cart:{callback.from_user.id}", [])
    in_cart = course_id in cart

    text = (
        f"📖 <b>{course.title}</b>\n\n"
        f"{course.description}\n\n"
        f"💰 Цена: <b>{course.price:.0f} ₽</b>"
    )
    await callback.message.edit_text(
        text,
        reply_markup=course_detail_kb(course_id, in_cart=in_cart),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Мои курсы ────────────────────────────────────────────────

@router.callback_query(F.data == "my_courses")
async def show_my_courses(callback: CallbackQuery) -> None:
    user = await db.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    courses = await db.get_purchased_courses(user)
    if not courses:
        await callback.answer("У тебя пока нет купленных курсов", show_alert=True)
        return

    lines = ["📦 <b>Мои курсы</b>\n"]
    for c in courses:
        lines.append(f"• <b>{c.title}</b>\n  🔗 {c.material_url}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
    await callback.answer()
