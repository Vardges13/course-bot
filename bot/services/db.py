"""Сервис работы с базой данных — CRUD-операции."""

from decimal import Decimal
from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from bot.models import (
    async_session, User, Course, Order, OrderItem, Payment,
)


# ─── Пользователи ────────────────────────────────────────────

async def get_or_create_user(
    telegram_id: int, full_name: str, username: str | None = None
) -> User:
    """Получить пользователя или создать нового."""
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if user is None:
            user = User(telegram_id=telegram_id, full_name=full_name, username=username)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user


async def get_user_by_telegram_id(telegram_id: int) -> User | None:
    async with async_session() as session:
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# ─── Курсы ────────────────────────────────────────────────────

async def get_active_courses() -> list[Course]:
    """Список активных курсов."""
    async with async_session() as session:
        stmt = select(Course).where(Course.is_active.is_(True)).order_by(Course.id)
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_course(course_id: int) -> Course | None:
    async with async_session() as session:
        return await session.get(Course, course_id)


async def add_course(title: str, description: str, price: float, material_url: str) -> Course:
    async with async_session() as session:
        course = Course(
            title=title, description=description,
            price=price, material_url=material_url, is_active=True,
        )
        session.add(course)
        await session.commit()
        await session.refresh(course)
        return course


async def delete_course(course_id: int) -> bool:
    """Мягкое удаление — помечаем курс неактивным."""
    async with async_session() as session:
        course = await session.get(Course, course_id)
        if course is None:
            return False
        course.is_active = False
        await session.commit()
        return True


# ─── Заказы ───────────────────────────────────────────────────

async def create_order(user: User, course_ids: list[int]) -> Order | None:
    """Создать заказ из списка id курсов. Возвращает None, если курсы не найдены."""
    async with async_session() as session:
        stmt = select(Course).where(Course.id.in_(course_ids), Course.is_active.is_(True))
        result = await session.execute(stmt)
        courses = list(result.scalars().all())
        if not courses:
            return None

        total = sum(Decimal(str(c.price)) for c in courses)
        order = Order(user_id=user.id, total_amount=float(total), status="pending")
        session.add(order)
        await session.flush()

        for c in courses:
            item = OrderItem(order_id=order.id, course_id=c.id, price=float(c.price))
            session.add(item)

        await session.commit()
        # Перезагружаем с items
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.course))
            .where(Order.id == order.id)
        )
        result = await session.execute(stmt)
        return result.scalar_one()


async def get_order_with_items(order_id: int) -> Order | None:
    async with async_session() as session:
        stmt = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.course),
                selectinload(Order.user),
            )
            .where(Order.id == order_id)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def mark_order_paid(order_id: int) -> Order | None:
    async with async_session() as session:
        order = await session.get(Order, order_id)
        if order:
            order.status = "paid"
            await session.commit()
            await session.refresh(order)
        return order


# ─── Платежи ──────────────────────────────────────────────────

async def create_payment_record(
    order_id: int, yookassa_id: str, amount: float
) -> Payment:
    async with async_session() as session:
        payment = Payment(
            order_id=order_id, yookassa_id=yookassa_id,
            amount=amount, status="pending",
        )
        session.add(payment)
        await session.commit()
        await session.refresh(payment)
        return payment


async def confirm_payment(yookassa_id: str) -> Payment | None:
    """Подтверждение платежа по yookassa_id. Обновляет статус платежа и заказа."""
    async with async_session() as session:
        stmt = select(Payment).where(Payment.yookassa_id == yookassa_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if payment is None:
            return None

        payment.status = "succeeded"
        payment.paid_at = datetime.now(timezone.utc)

        # Обновляем заказ
        order = await session.get(Order, payment.order_id)
        if order:
            order.status = "paid"

        await session.commit()
        await session.refresh(payment)
        return payment


async def cancel_payment(yookassa_id: str) -> Payment | None:
    async with async_session() as session:
        stmt = select(Payment).where(Payment.yookassa_id == yookassa_id)
        result = await session.execute(stmt)
        payment = result.scalar_one_or_none()
        if payment is None:
            return None
        payment.status = "canceled"
        order = await session.get(Order, payment.order_id)
        if order:
            order.status = "cancelled"
        await session.commit()
        await session.refresh(payment)
        return payment


# ─── Статистика ───────────────────────────────────────────────

async def get_sales_stats() -> dict:
    """Статистика продаж для админ-панели."""
    async with async_session() as session:
        # Общее число заказов
        total_orders = (await session.execute(
            select(func.count(Order.id))
        )).scalar() or 0

        # Оплаченные заказы
        paid_orders = (await session.execute(
            select(func.count(Order.id)).where(Order.status == "paid")
        )).scalar() or 0

        # Сумма продаж
        total_revenue = (await session.execute(
            select(func.sum(Payment.amount)).where(Payment.status == "succeeded")
        )).scalar() or 0

        # Число пользователей
        total_users = (await session.execute(
            select(func.count(User.id))
        )).scalar() or 0

        return {
            "total_orders": total_orders,
            "paid_orders": paid_orders,
            "total_revenue": float(total_revenue),
            "total_users": total_users,
        }


async def get_purchased_courses(user: User) -> list[Course]:
    """Список курсов, оплаченных пользователем."""
    async with async_session() as session:
        stmt = (
            select(Course)
            .join(OrderItem, OrderItem.course_id == Course.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.user_id == user.id, Order.status == "paid")
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
