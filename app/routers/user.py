from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.db.queries import (
    upsert_user,
    get_operator_by_id,
    create_question,
    create_live_session,
    get_active_session_for_user,
    get_all_operators,
)
from app.keyboards.user_kb import main_menu_kb, question_type_kb, cancel_kb, live_chat_kb
from app.keyboards.operator_kb import question_notification_kb, session_notification_kb
from app.states import QuestionState, LiveChatState

router = Router()


async def _ensure_user(message: Message) -> dict:
    """Upsert the user and return their DB row."""
    return await upsert_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        full_name=message.from_user.full_name,
    )


# ── Main menu ────────────────────────────────────────────────────────────────

@router.message(F.text == "Menda savol bor")
async def menu_have_question(message: Message, state: FSMContext):
    user = await _ensure_user(message)
    active = await get_active_session_for_user(user["id"])
    if active:
        await message.answer(
            "Siz allaqachon aktiv chatdasiz. Avval uni yakunlang."
        )
        return
    await message.answer(
        "Nima qilmoqchisiz?",
        reply_markup=question_type_kb(),
    )


@router.message(F.text == "Orqaga")
async def menu_back(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Asosiy menyu:", reply_markup=main_menu_kb())


# ── Ask a question flow ───────────────────────────────────────────────────────

@router.message(F.text == "Savol qoldirish")
async def start_question(message: Message, state: FSMContext):
    await state.set_state(QuestionState.waiting_for_question_text)
    await message.answer(
        "Savolingizni yozing:",
        reply_markup=cancel_kb(),
    )


@router.message(F.text == "Bekor qilish", QuestionState.waiting_for_question_text)
async def cancel_question(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())


@router.message(QuestionState.waiting_for_question_text)
async def receive_question(message: Message, state: FSMContext, bot: Bot):
    user = await _ensure_user(message)
    question = await create_question(user_id=user["id"], text=message.text)

    await state.clear()
    await message.answer(
        "Savolingiz qabul qilindi. Operatorlar tez orada javob beradi.",
        reply_markup=main_menu_kb(),
    )

    # Broadcast to all operators
    operators = await get_all_operators()
    q_id = question["id"]
    notification = (
        f"❓ <b>Yangi savol #{q_id}</b>\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}\n\n"
        f"{message.text}"
    )
    for op in operators:
        try:
            await bot.send_message(
                op["telegram_id"],
                notification,
                reply_markup=question_notification_kb(q_id),
            )
        except Exception:
            pass


# ── Live chat flow ────────────────────────────────────────────────────────────

@router.message(F.text == "Operatorga bog'lanish")
async def start_live_chat(message: Message, state: FSMContext, bot: Bot):
    user = await _ensure_user(message)

    # Guard: already in a session
    active = await get_active_session_for_user(user["id"])
    if active:
        await message.answer("Siz allaqachon aktiv chatdasiz.")
        return

    session = await create_live_session(user_id=user["id"])
    await state.set_state(LiveChatState.in_live_chat)
    await state.update_data(session_id=session["id"])

    await message.answer(
        "Operator qidirilmoqda... Iltimos kuting.\n"
        "Chatdan chiqish uchun tugmani bosing.",
        reply_markup=live_chat_kb(),
    )

    # Broadcast to all operators
    operators = await get_all_operators()
    s_id = session["id"]
    notification = (
        f"📞 <b>Yangi jonli chat #{s_id}</b>\n"
        f"👤 Foydalanuvchi: {message.from_user.full_name}"
    )
    for op in operators:
        try:
            await bot.send_message(
                op["telegram_id"],
                notification,
                reply_markup=session_notification_kb(s_id),
            )
        except Exception:
            pass


@router.message(F.text == "Chatdan chiqish", LiveChatState.in_live_chat)
async def user_leave_chat(message: Message, state: FSMContext):
    from app.db.queries import close_live_session
    data = await state.get_data()
    session_id = data.get("session_id")
    if session_id:
        await close_live_session(session_id)
    await state.clear()
    await message.answer(
        "Chat yakunlandi.",
        reply_markup=main_menu_kb(),
    )


@router.message(LiveChatState.in_live_chat)
async def user_in_live_chat(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await state.clear()
        await message.answer("Xatolik yuz berdi.", reply_markup=main_menu_kb())
        return

    from app.db.queries import get_session_by_id, get_operator_by_id as _get_op
    session = await get_session_by_id(session_id)
    if not session or session["status"] != "active":
        await message.answer(
            "Operator hali qabul qilmagan. Kuting yoki 'Chatdan chiqish' tugmasini bosing."
        )
        return

    operator = await _get_op(session["operator_id"])
    if operator:
        try:
            await bot.send_message(
                operator["telegram_id"],
                f"👤 <b>Foydalanuvchi:</b> {message.text}",
            )
        except Exception:
            pass
