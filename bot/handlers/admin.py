"""Админ-панель: управление курсами и статистика."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.config import config
from bot.services import db
from bot.keyboards import admin_menu_kb, admin_courses_delete_kb, back_to_admin_kb

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


class AddCourseStates(StatesGroup):
    """Состояния FSM для добавления курса."""
    waiting_title = State()
    waiting_description = State()
    waiting_price = State()
    waiting_url = State()


# ─── Вход в админку ───────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer(
        "🔧 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin:menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    await state.clear()
    await callback.message.edit_text(
        "🔧 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


# ─── Добавление курса (FSM) ──────────────────────────────────

@router.callback_query(F.data == "admin:add_course")
async def admin_add_course_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    await state.set_state(AddCourseStates.waiting_title)
    await callback.message.edit_text(
        "📝 Введи <b>название</b> нового курса:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddCourseStates.waiting_title)
async def admin_add_course_title(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await message.answer("📝 Введи <b>описание</b> курса:", parse_mode="HTML")
    await state.set_state(AddCourseStates.waiting_description)


@router.message(AddCourseStates.waiting_description)
async def admin_add_course_description(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    await state.update_data(description=message.text.strip())
    await message.answer("💰 Введи <b>цену</b> в рублях (число):", parse_mode="HTML")
    await state.set_state(AddCourseStates.waiting_price)


@router.message(AddCourseStates.waiting_price)
async def admin_add_course_price(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    try:
        price = float(message.text.strip().replace(",", "."))
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введи корректную цену (положительное число).")
        return
    await state.update_data(price=price)
    await message.answer(
        "🔗 Введи <b>ссылку на материалы</b> курса (URL):", parse_mode="HTML"
    )
    await state.set_state(AddCourseStates.waiting_url)


@router.message(AddCourseStates.waiting_url)
async def admin_add_course_url(message: Message, state: FSMContext) -> None:
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    data = await state.get_data()

    course = await db.add_course(
        title=data["title"],
        description=data["description"],
        price=data["price"],
        material_url=url,
    )
    await state.clear()
    await message.answer(
        f"✅ Курс <b>«{course.title}»</b> добавлен!\n"
        f"ID: {course.id}\n"
        f"Цена: {course.price:.0f} ₽",
        reply_markup=back_to_admin_kb(),
        parse_mode="HTML",
    )


# ─── Удаление курса ──────────────────────────────────────────

@router.callback_query(F.data == "admin:delete_course")
async def admin_delete_course_list(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    courses = await db.get_active_courses()
    if not courses:
        await callback.answer("Нет активных курсов.", show_alert=True)
        return
    await callback.message.edit_text(
        "🗑 Выбери курс для удаления:",
        reply_markup=admin_courses_delete_kb(courses),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:del:"))
async def admin_delete_course(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return
    course_id = int(callback.data.split(":")[2])
    deleted = await db.delete_course(course_id)
    if deleted:
        await callback.answer("✅ Курс удалён")
    else:
        await callback.answer("Курс не найден", show_alert=True)

    # Обновляем список
    courses = await db.get_active_courses()
    if courses:
        await callback.message.edit_text(
            "🗑 Выбери курс для удаления:",
            reply_markup=admin_courses_delete_kb(courses),
        )
    else:
        await callback.message.edit_text(
            "Все курсы удалены.",
            reply_markup=back_to_admin_kb(),
        )


# ─── Статистика ───────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Доступ запрещён.", show_alert=True)
        return

    stats = await db.get_sales_stats()
    text = (
        "📊 <b>Статистика продаж</b>\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📦 Заказов всего: {stats['total_orders']}\n"
        f"✅ Оплаченных: {stats['paid_orders']}\n"
        f"💰 Выручка: {stats['total_revenue']:.0f} ₽"
    )
    await callback.message.edit_text(
        text, reply_markup=back_to_admin_kb(), parse_mode="HTML"
    )
    await callback.answer()
