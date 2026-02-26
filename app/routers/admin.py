import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.db.queries import (
    add_operator,
    remove_operator,
    get_all_operators,
    get_stats,
    get_operator_activity,
    get_user_by_id,
)
from app.filters import IsAdmin
from app.keyboards.admin_kb import (
    admin_menu_kb,
    admin_cancel_kb,
    back_to_admin_kb,
    stats_period_kb,
    operator_list_kb,
)
from app.states import AdminState

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PERIOD_LABELS = {"day": "Bugun", "week": "Hafta", "month": "Oy"}
ADMIN_MENU_TEXT = "🛠 <b>Admin panel</b>\n\nBoshqaruv bo'limini tanlang:"


# ── /admin command ────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(ADMIN_MENU_TEXT, reply_markup=admin_menu_kb())


# ── Admin menu navigation ─────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:menu")
async def cb_admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(ADMIN_MENU_TEXT, reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:cancel")
async def cb_admin_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(ADMIN_MENU_TEXT, reply_markup=admin_menu_kb())
    await callback.answer("Bekor qilindi.")


# ── Add operator ──────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:add_operator")
async def cb_add_operator(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.waiting_for_new_operator_id)
    await state.update_data(menu_msg_id=callback.message.message_id)
    await callback.message.edit_text(
        "➕ <b>Yangi operator qo'shish</b>\n\n"
        "Operator Telegram ID sini yuboring <i>(faqat raqam)</i>:",
        reply_markup=admin_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminState.waiting_for_new_operator_id)
async def receive_operator_id(message: Message, state: FSMContext, bot: Bot):
    text = message.text.strip()
    if not text.lstrip("-").isdigit():
        await message.answer("⚠️ Iltimos, faqat raqam kiriting.")
        return

    data = await state.get_data()
    menu_msg_id = data.get("menu_msg_id")
    await state.update_data(new_operator_telegram_id=int(text))
    await state.set_state(AdminState.waiting_for_new_operator_name)

    try:
        await message.delete()
    except Exception:
        pass

    if menu_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=menu_msg_id,
                text=(
                    f"➕ <b>Yangi operator qo'shish</b>\n\n"
                    f"Telegram ID: <code>{text}</code>\n\n"
                    f"Endi operator to'liq ismini yuboring:"
                ),
                reply_markup=admin_cancel_kb(),
            )
        except Exception as e:
            logging.error(f"Failed to edit admin menu message: {e}")


@router.message(AdminState.waiting_for_new_operator_name)
async def receive_operator_name(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tg_id = data["new_operator_telegram_id"]
    menu_msg_id = data.get("menu_msg_id")
    full_name = message.text.strip()

    success = await add_operator(telegram_id=tg_id, full_name=full_name)
    await state.clear()

    try:
        await message.delete()
    except Exception:
        pass

    if success:
        result_text = (
            f"✅ <b>Operator muvaffaqiyatli qo'shildi!</b>\n\n"
            f"👤 {full_name}\n"
            f"🆔 <code>{tg_id}</code>"
        )
    else:
        result_text = (
            f"❌ <b>Xatolik!</b>\n\n"
            f"Bu Telegram ID (<code>{tg_id}</code>) allaqachon "
            f"operator sifatida ro'yxatdan o'tgan."
        )

    if menu_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=menu_msg_id,
                text=result_text,
                reply_markup=back_to_admin_kb(),
            )
        except Exception as e:
            logging.error(f"Failed to edit admin menu message: {e}")


# ── Remove operator ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:remove_operator")
async def cb_remove_operator_menu(callback: CallbackQuery):
    operators = await get_all_operators()
    if not operators:
        await callback.answer("Hech qanday operator yo'q.", show_alert=True)
        return
    await callback.message.edit_text(
        "➖ <b>Operator o'chirish</b>\n\nO'chirmoqchi bo'lgan operatorni tanlang:",
        reply_markup=operator_list_kb(operators),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("remove_operator:"))
async def cb_remove_operator(callback: CallbackQuery):
    op_id = int(callback.data.split(":")[1])
    await remove_operator(op_id)

    operators = await get_all_operators()
    if operators:
        await callback.message.edit_reply_markup(reply_markup=operator_list_kb(operators))
        await callback.answer("✅ Operator o'chirildi.")
    else:
        await callback.message.edit_text(
            "✅ <b>Barcha operatorlar o'chirildi.</b>",
            reply_markup=back_to_admin_kb(),
        )
        await callback.answer()


# ── Statistics ────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin:stats")
async def cb_stats_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📊 <b>Statistika</b>\n\nHisobot davrini tanlang:",
        reply_markup=stats_period_kb(),
    )
    await callback.answer()


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


# ── Statistics ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("stats:"))
async def cb_stats(callback: CallbackQuery):
    period = callback.data.split(":")[1]
    label = PERIOD_LABELS.get(period, period)

    stats = await get_stats(period)
    activity = await get_operator_activity(period)

    lines = [
        f"📊 <b>Statistika — {label}</b>\n",
        f"❓ Savollar: <b>{stats['total_questions']}</b>",
        f"  ✅ Javoblangan: {stats['answered_questions']}",
        f"  ⏳ Kutayotgan: {stats['pending_questions']}",
        f"",
        f"💬 Jonli chatlar: <b>{stats['total_sessions']}</b>",
        f"⏱ O'rtacha davomiylik: <b>{stats['avg_session_duration']}s</b>",
        f"",
        f"<b>Operator faolligi:</b>",
    ]
    if activity:
        for i, op in enumerate(activity, 1):
            lines.append(f"  {i}. {op['full_name']}: {op['answered_count']} ta javob")
    else:
        lines.append("  —")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=stats_period_kb(),
    )
    await callback.answer()
