from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.config import settings


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user:
            return event.from_user.id in settings.admins
        return False
