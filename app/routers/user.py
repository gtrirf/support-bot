import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.db.queries import (
    upsert_user,
    create_question,
    create_live_session,
    get_active_session_for_user,
    get_all_operators,
    get_session_by_id,
    get_operator_by_id,
    close_live_session,
)
from app.keyboards.user_kb import (
    main_menu_kb,
    question_type_kb,
    cancel_question_kb,
    live_chat_kb,
)
from app.keyboards.operator_kb import question_notification_kb, session_notification_kb
from app.states import QuestionState, LiveChatState

router = Router()

MAIN_MENU_TEXT = (
    "🏠 <b>Asosiy menyu</b>\n\n"
    "Murojaat turini tanlang:"
)


async def _upsert(user_id: int, username: str | None, full_name: str) -> dict:
    return await upsert_user(
        telegram_id=user_id, username=username, full_name=full_name
    )


# ── Navigation ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:main")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:question_type")
async def cb_question_type(callback: CallbackQuery):
    user = await _upsert(
        callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )
    active = await get_active_session_for_user(user["id"])
    if active:
        await callback.answer(
            "Siz allaqachon aktiv chatdasiz! Avval chatdan chiqing.", show_alert=True
        )
        return
    await callback.message.edit_text(
        "📋 <b>Nima qilmoqchisiz?</b>\n\nKerakli amalni tanlang:",
        reply_markup=question_type_kb(),
    )
    await callback.answer()


# ── Ask a question flow ───────────────────────────────────────────────────────

@router.callback_query(F.data == "action:ask_question")
async def cb_ask_question(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QuestionState.waiting_for_question_text)
    await state.update_data(menu_msg_id=callback.message.message_id)
    await callback.message.edit_text(
        "📝 <b>Savol yozing</b>\n\n"
        "Savolingizni yozing — operatorlar ko'rib chiqib, tez orada javob berishadi.\n\n"
        "<i>Bekor qilish uchun tugmani bosing.</i>",
        reply_markup=cancel_question_kb(),
    )
    await callback.answer()


@router.message(QuestionState.waiting_for_question_text)
async def receive_question(message: Message, state: FSMContext, bot: Bot):
    user = await _upsert(
        message.from_user.id, message.from_user.username, message.from_user.full_name
    )
    question = await create_question(user_id=user["id"], text=message.text)

    data = await state.get_data()
    menu_msg_id = data.get("menu_msg_id")
    await state.clear()

    # Edit the persistent menu message to show success
    if menu_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=menu_msg_id,
                text=(
                    "✅ <b>Savolingiz qabul qilindi!</b>\n\n"
                    "Operatorlar tez orada javob beradi.\n"
                    "Javob kelganda sizga xabar yuboriladi."
                ),
                reply_markup=main_menu_kb(),
            )
        except Exception:
            pass

    # Broadcast to all operators
    operators = await get_all_operators()
    q_id = question["id"]
    notification = (
        f"❓ <b>Yangi savol #{q_id}</b>\n"
        f"👤 {message.from_user.full_name}\n\n"
        f"<i>{message.text}</i>"
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

@router.callback_query(F.data == "action:live_chat")
async def cb_live_chat(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user = await _upsert(
        callback.from_user.id, callback.from_user.username, callback.from_user.full_name
    )
    active = await get_active_session_for_user(user["id"])
    if active:
        await callback.answer(
            "Siz allaqachon aktiv chatdasiz!", show_alert=True
        )
        return

    session = await create_live_session(user_id=user["id"])
    s_id = session["id"]

    await state.set_state(LiveChatState.in_live_chat)
    await state.update_data(session_id=s_id, menu_msg_id=callback.message.message_id)

    await callback.message.edit_text(
        "🔍 <b>Operator qidirilmoqda...</b>\n\n"
        "Operator ulangach, xabarlaringizni yuboring.\n"
        "Chatdan chiqish uchun quyidagi tugmani bosing.",
        reply_markup=live_chat_kb(s_id),
    )
    await callback.answer()

    # Broadcast to all operators
    operators = await get_all_operators()
    notification = (
        f"📞 <b>Yangi chat so'rovi #{s_id}</b>\n"
        f"👤 {callback.from_user.full_name}"
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


@router.callback_query(F.data.startswith("chat:leave:"))
async def cb_leave_chat(callback: CallbackQuery, state: FSMContext):
    s_id = int(callback.data.split(":")[2])
    await close_live_session(s_id)
    await state.clear()
    await callback.message.edit_text(MAIN_MENU_TEXT, reply_markup=main_menu_kb())
    await callback.answer("Chat yakunlandi.")


@router.message(LiveChatState.in_live_chat)
async def user_in_live_chat(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    session_id = data.get("session_id")
    if not session_id:
        await state.clear()
        return

    session = await get_session_by_id(session_id)
    if not session or session["status"] != "active":
        await message.answer(
            "⏳ <i>Operator hali ulanmagan. Kuting yoki chatdan chiqing.</i>",
        )
        return

    operator = await get_operator_by_id(session["operator_id"])
    if operator:
        try:
            await bot.send_message(
                operator["telegram_id"],
                f"👤 <b>Foydalanuvchi:</b> {message.text}",
            )
        except Exception as e:
            logging.error(f"Failed to relay user message: {e}")
