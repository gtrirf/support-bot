import json
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
    ended_chat_kb,
    submit_answer_kb,
)
from app.keyboards.user_kb import main_menu_kb, live_chat_kb
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
        lines.append(f"<b>❓ Javoblanmagan savollar ({len(questions)}):</b>")
        for q in questions:
            lines.append(f"  #{q['id']}: {q['text'][:80]}")
    else:
        lines.append("✅ Javoblanmagan savollar yo'q.")

    lines.append("")

    if sessions:
        lines.append(f"<b>💬 Kutayotgan chatlar ({len(sessions)}):</b>")
        for s in sessions:
            lines.append(f"  #{s['id']} (foydalanuvchi id: {s['user_id']})")
    else:
        lines.append("✅ Kutayotgan chatlar yo'q.")

    await message.answer("\n".join(lines))


# ── Answer question flow ──────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("answer_question:"))
async def cb_answer_question(callback: CallbackQuery, state: FSMContext, bot: Bot):
    q_id = int(callback.data.split(":")[1])
    operator = await get_operator_by_telegram_id(callback.from_user.id)

    # Fetch question+user before claim so we always have user_db_id for the profile button
    question = await get_question_by_id(q_id)
    user = await get_user_by_id(question["user_id"])

    claimed = await claim_question(question_id=q_id, operator_id=operator["id"])
    if not claimed:
        await callback.message.edit_reply_markup(
            reply_markup=question_claimed_kb(user["id"])
        )
        await callback.answer(
            "Bu savol allaqachon boshqa operator tomonidan qabul qilindi.",
            show_alert=True,
        )
        return

    await state.set_state(QuestionState.collecting_answer_messages)
    await state.update_data(
        question_id=q_id,
        user_telegram_id=user["telegram_id"],
        op_chat_id=callback.message.chat.id,
        collected_answer_ids=[],
        first_answer_text="",
    )

    await callback.message.edit_reply_markup(
        reply_markup=question_claimed_kb(user["id"])
    )
    await callback.answer()

    # Forward the user's original messages to this operator
    if question.get("messages_json"):
        try:
            msg_data = json.loads(question["messages_json"])
            for msg_id in msg_data.get("msg_ids", []):
                await bot.forward_message(
                    chat_id=callback.message.chat.id,
                    from_chat_id=msg_data["chat_id"],
                    message_id=msg_id,
                )
        except Exception as e:
            logging.error(f"Failed to forward question messages to operator: {e}")

    sent = await callback.message.answer(
        f"📝 <b>Savol #{q_id} uchun javob yozing</b>\n\n"
        "Matn, rasm, video, audio, sticker — har qanday turdagi xabarlar.\n"
        "Hammasi tayyor bo'lgach <b>Yuborish</b> tugmasini bosing.",
        reply_markup=submit_answer_kb(),
    )
    await state.update_data(answer_menu_msg_id=sent.message_id)


@router.message(QuestionState.collecting_answer_messages)
async def collect_answer_message(message: Message, state: FSMContext):
    data = await state.get_data()
    ids = data.get("collected_answer_ids", [])
    ids.append(message.message_id)

    first_answer_text = data.get("first_answer_text", "")
    if not first_answer_text and message.text:
        first_answer_text = message.text[:500]

    await state.update_data(collected_answer_ids=ids, first_answer_text=first_answer_text)

    answer_menu_msg_id = data.get("answer_menu_msg_id")
    count = len(ids)
    if answer_menu_msg_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=answer_menu_msg_id,
                text=(
                    f"📝 <b>Javob xabarlari: {count} ta</b>\n\n"
                    "Yana xabar yuborishingiz yoki <b>Yuborish</b> tugmasini bosishingiz mumkin."
                ),
                reply_markup=submit_answer_kb(),
            )
        except Exception:
            pass


@router.callback_query(F.data == "answer:submit", QuestionState.collecting_answer_messages)
async def submit_answer(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    collected_ids = data.get("collected_answer_ids", [])

    if not collected_ids:
        await callback.answer("Avval xabar yuboring!", show_alert=True)
        return

    q_id = data["question_id"]
    user_telegram_id = data["user_telegram_id"]
    op_chat_id = data["op_chat_id"]
    first_answer_text = data.get("first_answer_text") or f"[{len(collected_ids)} ta xabar]"

    await answer_question(question_id=q_id, answer_text=first_answer_text)
    await state.clear()

    await callback.message.edit_text(f"✅ <b>Javob #{q_id} muvaffaqiyatli yuborildi.</b>")
    await callback.answer()

    try:
        await bot.send_message(
            user_telegram_id,
            "💬 <b>Savolingizga javob keldi!</b>",
        )
        for msg_id in collected_ids:
            await bot.copy_message(
                chat_id=user_telegram_id,
                from_chat_id=op_chat_id,
                message_id=msg_id,
            )
    except Exception as e:
        logging.error(f"Failed to send answer to user {user_telegram_id}: {e}")


@router.callback_query(F.data == "answer:cancel", QuestionState.collecting_answer_messages)
async def answer_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Javob bekor qilindi.")
    await callback.answer()


# ── Accept live session flow ──────────────────────────────────────────────────

@router.callback_query(F.data.startswith("accept_session:"))
async def cb_accept_session(callback: CallbackQuery, state: FSMContext, bot: Bot):
    s_id = int(callback.data.split(":")[1])
    operator = await get_operator_by_telegram_id(callback.from_user.id)

    claimed = await claim_live_session(session_id=s_id, operator_id=operator["id"])
    if not claimed:
        await callback.message.edit_reply_markup(reply_markup=session_claimed_kb())
        await callback.answer(
            "Bu chat allaqachon boshqa operator tomonidan qabul qilindi.",
            show_alert=True,
        )
        return

    session = await get_session_by_id(s_id)
    user = await get_user_by_id(session["user_id"])
    user_tg_id = user["telegram_id"]
    user_db_id = user["id"]

    await state.set_state(LiveChatState.operator_in_live_chat)
    await state.update_data(
        session_id=s_id,
        user_telegram_id=user_tg_id,
        user_db_id=user_db_id,
    )

    await callback.message.edit_reply_markup(reply_markup=session_claimed_kb())
    await callback.answer()
    await callback.message.answer(
        f"✅ <b>Chat #{s_id} qabul qilindi.</b>\n\n"
        f"Foydalanuvchi bilan yozishishni boshlashingiz mumkin.\n"
        f"Chatni yakunlash uchun quyidagi tugmani bosing.",
        reply_markup=end_chat_kb(s_id, user_db_id),
    )

    # Edit user's live chat message to show operator connected
    user_menu_msg_id = await _get_user_menu_msg_id(bot, user_tg_id)
    if user_menu_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=user_tg_id,
                message_id=user_menu_msg_id,
                text=(
                    "✅ <b>Operator ulandi!</b>\n\n"
                    "Operator bilan yozishishni boshlashingiz mumkin.\n"
                    "Chatdan chiqish uchun quyidagi tugmani bosing."
                ),
                reply_markup=live_chat_kb(s_id),
            )
        except Exception as e:
            logging.error(f"Failed to edit user live chat message: {e}")
    else:
        try:
            await bot.send_message(
                user_tg_id,
                "✅ <b>Operator ulandi!</b> Savolingizni yozing.",
            )
        except Exception as e:
            logging.error(f"Failed to notify user {user_tg_id}: {e}")


# ── Live chat relay (operator → user) ─────────────────────────────────────────

@router.message(LiveChatState.operator_in_live_chat)
async def operator_relay_message(message: Message, state: FSMContext):
    data = await state.get_data()
    user_telegram_id = data.get("user_telegram_id")
    if not user_telegram_id:
        await message.answer("Xatolik: foydalanuvchi topilmadi.")
        return

    try:
        await message.copy_to(user_telegram_id)
    except Exception as e:
        logging.error(f"Failed to relay message to user {user_telegram_id}: {e}")
        await message.answer("Xabar foydalanuvchiga yuborilmadi.")


# ── End session ───────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("end_session:"))
async def cb_end_session(callback: CallbackQuery, state: FSMContext, bot: Bot):
    s_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    user_telegram_id = data.get("user_telegram_id")
    user_db_id = data.get("user_db_id")

    await close_live_session(s_id)
    await state.clear()

    await callback.answer()
    await callback.message.edit_reply_markup(
        reply_markup=ended_chat_kb(user_db_id) if user_db_id else None
    )
    await callback.message.answer("✅ Chat yakunlandi.")

    if user_telegram_id:
        user_menu_msg_id = None
        try:
            storage = get_storage()
            key = StorageKey(
                bot_id=bot.id,
                chat_id=user_telegram_id,
                user_id=user_telegram_id,
            )
            from aiogram.fsm.context import FSMContext as _FSMContext
            user_ctx = _FSMContext(storage=storage, key=key)
            user_data = await user_ctx.get_data()
            user_menu_msg_id = user_data.get("menu_msg_id")
            await user_ctx.clear()
        except Exception as e:
            logging.error(f"Failed to clear user FSM state for {user_telegram_id}: {e}")

        if user_menu_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=user_telegram_id,
                    message_id=user_menu_msg_id,
                    text=(
                        "✅ <b>Chat yakunlandi!</b>\n\n"
                        "Operator tomonidan chat yopildi. Rahmat!\n"
                        "Yana murojaat qilish uchun quyidagi tugmani bosing."
                    ),
                    reply_markup=main_menu_kb(),
                )
            except Exception as e:
                logging.error(f"Failed to edit user menu message: {e}")
        else:
            try:
                await bot.send_message(
                    user_telegram_id,
                    "✅ <b>Chat operator tomonidan yakunlandi.</b>\n\nRahmat!",
                    reply_markup=main_menu_kb(),
                )
            except Exception as e:
                logging.error(f"Failed to notify user {user_telegram_id}: {e}")


# ── User profile view ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("profile:user:"))
async def cb_view_user_profile(callback: CallbackQuery):
    user_db_id = int(callback.data.split(":")[2])
    user = await get_user_by_id(user_db_id)

    if not user:
        await callback.answer("Foydalanuvchi topilmadi.", show_alert=True)
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    username_text = f"@{user['username']}" if user.get("username") else "—"
    text = (
        f"👤 <b>Foydalanuvchi profili</b>\n\n"
        f"📋 Ism: <b>{user['full_name']}</b>\n"
        f"🔗 Username: {username_text}\n"
        f"🆔 Telegram ID: <code>{user['telegram_id']}</code>\n"
        f"📅 Ro'yxatdan o'tgan: {user['created_at']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="👤 Profilni ochish",
            url=f"tg://user?id={user['telegram_id']}",
        )
    ]])
    await callback.answer()
    await callback.message.answer(text, reply_markup=kb)


# ── noop callback (already-claimed buttons) ───────────────────────────────────

@router.callback_query(F.data == "noop")
async def cb_noop(callback: CallbackQuery):
    await callback.answer()


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_user_menu_msg_id(bot: Bot, user_tg_id: int) -> int | None:
    """Read menu_msg_id from user's FSM state without modifying it."""
    try:
        storage = get_storage()
        key = StorageKey(bot_id=bot.id, chat_id=user_tg_id, user_id=user_tg_id)
        from aiogram.fsm.context import FSMContext as _FSMContext
        user_ctx = _FSMContext(storage=storage, key=key)
        data = await user_ctx.get_data()
        return data.get("menu_msg_id")
    except Exception as e:
        logging.error(f"Failed to read user FSM data for {user_tg_id}: {e}")
        return None
