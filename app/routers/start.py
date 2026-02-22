from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db.queries import upsert_user
from app.keyboards.user_kb import main_menu_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )
    await message.answer(
        "Assalomu alaykum! Carville CA qo'llab-quvvatlash botiga xush kelibsiz.\n"
        "Quyidagi menyudan tanlang:",
        reply_markup=main_menu_kb(),
    )
