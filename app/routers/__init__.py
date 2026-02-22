from aiogram import Router

from .admin import router as admin_router
from .operator import router as operator_router
from .user import router as user_router
from .start import router as start_router


def setup_routers() -> Router:
    router = Router()
    # Admin first (highest priority), then operator, user, start
    router.include_router(admin_router)
    router.include_router(operator_router)
    router.include_router(user_router)
    router.include_router(start_router)
    return router
