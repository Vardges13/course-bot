"""Обработчики /start, главное меню, каталог, «Мои курсы»."""

import os
from pathlib import Path

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.services import db
from bot.keyboards import main_menu_kb, catalog_kb, course_detail_kb

router = Router()

WELCOME_PHOTO = Path(__file__).parent.parent.parent / "webapp" / "vardges.jpg"

WELCOME_TEXT = (
    "🎓 <b>VARDGES ACADEMY</b>\n"
    "<i>Для предпринимателей и экспертов</i>\n\n"
    "Привет! 👋\n\n"
    "Здесь — практические курсы от <b>Вардгеса Арутюняна</b>, "
    "предпринимателя с 15-летним опытом в реальном бизнесе.\n\n"
    "🎯 <b>Для кого:</b>\n"
    "→ Предприниматели, которые хотят выйти в онлайн\n"
    "→ Эксперты, которые хотят упаковать знания в продукт\n"
    "→ Все, кто устал от теории и хочет результат\n\n"
    "📚 <b>Чему научишься:</b>\n"
    "💰 Продажи и переговоры\n"
    "🚀 Из офлайна в онлайн\n"
    "🤖 ИИ-инструменты для бизнеса\n"
    "📱 Контент и продвижение\n"
    "⭐ Личный бренд из регионов\n\n"
    "<i>«Реальный бизнес × ИИ × Здравый смысл»</i>\n\n"
    "👇 <b>Нажми «Меню» чтобы начать:</b>"
)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Приветствие + фото + главное меню."""
    user = await db.get_or_create_user(
        telegram_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username,
    )

    text = WELCOME_TEXT.format(name=user.full_name)

    if WELCOME_PHOTO.exists():
        photo = FSInputFile(WELCOME_PHOTO)
        await message.answer_photo(
            photo=photo,
            caption=text,
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )
    else:
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=main_menu_kb(),
        )


@router.callback_query(F.data == "main_menu")
async def show_main_menu(callback: CallbackQuery) -> None:
    try:
        await callback.message.edit_caption(
            caption="🎓 <b>VARDGES ACADEMY</b>\n\n👇 <b>Выбери действие:</b>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_text(
            "🎓 <b>VARDGES ACADEMY</b>\n\n👇 <b>Выбери действие:</b>",
            reply_markup=main_menu_kb(),
            parse_mode="HTML",
        )
    await callback.answer()


@router.callback_query(F.data == "about")
async def show_about(callback: CallbackQuery) -> None:
    text = (
        "🎓 <b>О VARDGES ACADEMY</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👤 <b>Вардгес Арутюнян</b>\n"
        "Предприниматель из Курска\n"
        "15+ лет в реальном бизнесе\n\n"
        "🏢 Туризм, отели, продажи — всё прошёл сам.\n"
        "Не инфоцыган. Не теоретик. Практик.\n\n"
        "📌 <b>Принципы:</b>\n"
        "→ Реальный опыт > красивые слайды\n"
        "→ Результат > процесс\n"
        "→ Здравый смысл > хайп\n"
        "→ Практика с первого дня\n\n"
        "📱 Instagram: @vardges13\n"
        "✈️ Telegram: @vardges13"
    )
    from bot.keyboards import about_back_kb
    try:
        await callback.message.edit_caption(
            caption=text,
            reply_markup=about_back_kb(),
            parse_mode="HTML",
        )
    except Exception:
        await callback.message.edit_text(
            text,
            reply_markup=about_back_kb(),
            parse_mode="HTML",
            disable_web_page_preview=True,
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
