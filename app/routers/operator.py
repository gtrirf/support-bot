import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Message, CallbackQuery

from app.db.queries import (
    claim_question,
    answer_question,
    get_question_by_id,
    get_user_by_id,
    claim_live_session,
    close_live_session,
    get_session_by_id,
    get_unanswered_questions,
    get_waiting_sessions,
    get_operator_by_telegram_id,
)
from app.filters import IsOperator
from app.keyboards.operator_kb import (
    question_claimed_kb,
    session_claimed_kb,
    end_chat_kb,
)
from app.keyboards.user_kb import main_menu_kb
from app.states import QuestionState, LiveChatState
from app.utils.storage_holder import get_storage

router = Router()
router.message.filter(IsOperator())
router.callback_query.filter(IsOperator())


# ── /panel ────────────────────────────────────────────────────────────────────

@router.message(Command("panel"))
async def cmd_panel(message: Message):
    questions = await get_unanswered_questions()
    sessions = await get_waiting_sessions()

    lines = ["<b>📋 Operator paneli</b>\n"]

    if questions:
        lines.append(f"<b>Javoblanmagan savollar ({len(questions)}):</b>")
        for q in questions:
            lines.append(f"  #{q['id']}: {q['text'][:80]}")
    else:
        lines.append("Javoblanmagan savollar yo'q.")

    lines.append("")

    if sessions:
        lines.append(f"<b>Kutayotgan chatlar ({len(sessions)}):</b>")
        for s in sessions:
            lines.append(f"  #{s['id']} (foydalanuvchi id: {s['user_id']})")
    else:
        lines.append("Kutayotgan chatlar yo'q.")

    await message.answer("\n".join(lines))


# ── Answer question flow ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("answer_question:"))
async def cb_answer_question(callback: CallbackQuery, state: FSMContext, bot: Bot):
    q_id = int(callback.data.split(":")[1])
    operator = await get_operator_by_telegram_id(callback.from_user.id)

    claimed = await claim_question(question_id=q_id, operator_id=operator["id"])
    if not claimed:
        await callback.message.edit_reply_markup(reply_markup=question_claimed_kb())
        await callback.answer("Bu savol allaqachon boshqa operator tomonidan qabul qilindi.", show_alert=True)
        return

    question = await get_question_by_id(q_id)
    user = await get_user_by_id(question["user_id"])

    await state.set_state(QuestionState.waiting_for_answer_text)
    await state.update_data(question_id=q_id, user_telegram_id=user["telegram_id"])

    await callback.message.edit_reply_markup(reply_markup=question_claimed_kb())
    await callback.answer()
    await callback.message.answer(
        f"📝 Savol #{q_id}:\n{question['text']}\n\nJavobingizni yozing:"
    )


@router.message(QuestionState.waiting_for_answer_text)
async def receive_answer(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    q_id = data["question_id"]
    user_telegram_id = data["user_telegram_id"]

    await answer_question(question_id=q_id, answer_text=message.text)
    await state.clear()

    await message.answer(f"✅ Javob #{q_id} yuborildi.")

    try:
        question = await get_question_by_id(q_id)
        await bot.send_message(
            user_telegram_id,
            f"💬 <b>Savolingizga javob:</b>\n\n"
            f"<i>Savol:</i> {question['text']}\n\n"
            f"<i>Javob:</i> {message.text}",
        )
    except Exception as e:
        logging.error(f"Failed to send answer to user {user_telegram_id}: {e}")


# ── Accept live session flow ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept_session:"))
async def cb_accept_session(callback: CallbackQuery, state: FSMContext, bot: Bot):
    s_id = int(callback.data.split(":")[1])
    operator = await get_operator_by_telegram_id(callback.from_user.id)

    claimed = await claim_live_session(session_id=s_id, operator_id=operator["id"])
    if not claimed:
        await callback.message.edit_reply_markup(reply_markup=session_claimed_kb())
        await callback.answer("Bu chat allaqachon boshqa operator tomonidan qabul qilindi.", show_alert=True)
        return

    session = await get_session_by_id(s_id)
    user = await get_user_by_id(session["user_id"])

    await state.set_state(LiveChatState.operator_in_live_chat)
    await state.update_data(session_id=s_id, user_telegram_id=user["telegram_id"])

    await callback.message.edit_reply_markup(reply_markup=session_claimed_kb())
    await callback.answer()
    await callback.message.answer(
        f"✅ Chat #{s_id} qabul qilindi. Foydalanuvchi bilan gaplasha olasiz.\n"
        f"Chatni yakunlash uchun quyidagi tugmani bosing.",
        reply_markup=end_chat_kb(s_id),
    )

    # Notify user
    try:
        await bot.send_message(
            user["telegram_id"],
            f"✅ Operator ulandi! Savolingizni yozing.",
        )
    except Exception as e:
        logging.error(f"Failed to notify user {user['telegram_id']}: {e}")


# ── Live chat relay (operator → user) ─────────────────────────────────────────

@router.message(LiveChatState.operator_in_live_chat)
async def operator_relay_message(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    user_telegram_id = data.get("user_telegram_id")
    if not user_telegram_id:
        await message.answer("Xatolik: foydalanuvchi topilmadi.")
        return

    try:
        await bot.send_message(
            user_telegram_id,
            f"🎧 <b>Operator:</b> {message.text}",
        )
    except Exception as e:
        logging.error(f"Failed to relay message to user {user_telegram_id}: {e}")
        await message.answer("Xabar foydalanuvchiga yuborilmadi.")


# ── End session ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("end_session:"))
async def cb_end_session(callback: CallbackQuery, state: FSMContext, bot: Bot):
    s_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_telegram_id = data.get("user_telegram_id")

    await close_live_session(s_id)
    await state.clear()

    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Chat yakunlandi.")

    # Notify user and clear their FSM state
    if user_telegram_id:
        try:
            await bot.send_message(
                user_telegram_id,
                "Chat operator tomonidan yakunlandi. Rahmat!",
                reply_markup=main_menu_kb(),
            )
        except Exception as e:
            logging.error(f"Failed to notify user {user_telegram_id} of session end: {e}")

        try:
            storage = get_storage()
            key = StorageKey(
                bot_id=bot.id,
                chat_id=user_telegram_id,
                user_id=user_telegram_id,
            )
            from aiogram.fsm.context import FSMContext as _FSMContext
            user_ctx = _FSMContext(storage=storage, key=key)
            await user_ctx.clear()
        except Exception as e:
            logging.error(f"Failed to clear user FSM state for {user_telegram_id}: {e}")


# ── noop callback (already-claimed buttons) ───────────────────────────────────

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()
