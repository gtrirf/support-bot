from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.queries import upsert_user
from app.keyboards.user_kb import main_menu_kb, live_chat_kb
from app.states import LiveChatState

router = Router()

WELCOME_TEXT = (
    "👋 <b>Assalomu alaykum!</b>\n\n"
    "Carville CA qo'llab-quvvatlash botiga xush kelibsiz.\n"
    "Murojaat turini tanlang:"
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )

    current_state = await state.get_state()
    if current_state == LiveChatState.in_live_chat:
        data = await state.get_data()
        session_id = data.get("session_id")
        await message.answer(
            "💬 <b>Siz hozir operator bilan chatdasiz.</b>\n\n"
            "Chatdan chiqish uchun quyidagi tugmani bosing:",
            reply_markup=live_chat_kb(session_id) if session_id else None,
        )
        return

    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())
