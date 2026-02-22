from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.db.queries import get_operator_by_telegram_id


class IsOperator(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        if event.from_user:
            operator = await get_operator_by_telegram_id(event.from_user.id)
            return operator is not None
        return False
