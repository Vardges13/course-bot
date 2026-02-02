"""Регистрация всех роутеров."""

from aiogram import Router

from bot.handlers.start import router as start_router
from bot.handlers.cart import router as cart_router
from bot.handlers.admin import router as admin_router


def register_routers(main_router: Router) -> None:
    """Подключить все роутеры к главному."""
    main_router.include_router(start_router)
    main_router.include_router(cart_router)
    main_router.include_router(admin_router)
