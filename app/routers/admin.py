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
)
from app.filters import IsAdmin
from app.keyboards.admin_kb import admin_menu_kb, stats_period_kb, operator_list_kb
from app.keyboards.user_kb import main_menu_kb
from app.states import AdminState

router = Router()
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

PERIOD_LABELS = {"day": "Bugun", "week": "Hafta", "month": "Oy"}


# ── /admin ────────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🛠 Admin panel:", reply_markup=admin_menu_kb())


# ── Add operator ──────────────────────────────────────────────────────────────

@router.message(F.text == "Operator qo'shish")
async def start_add_operator(message: Message, state: FSMContext):
    await state.set_state(AdminState.waiting_for_new_operator_id)
    await message.answer(
        "Yangi operator Telegram ID sini yuboring (raqam):",
        reply_markup=main_menu_kb(),
    )


@router.message(AdminState.waiting_for_new_operator_id)
async def receive_operator_id(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.lstrip("-").isdigit():
        await message.answer("Iltimos, faqat raqam kiriting.")
        return

    await state.update_data(new_operator_telegram_id=int(text))
    await state.set_state(AdminState.waiting_for_new_operator_name)
    await message.answer("Operator to'liq ismini yuboring:")


@router.message(AdminState.waiting_for_new_operator_name)
async def receive_operator_name(message: Message, state: FSMContext):
    data = await state.get_data()
    tg_id = data["new_operator_telegram_id"]
    full_name = message.text.strip()

    success = await add_operator(telegram_id=tg_id, full_name=full_name)
    await state.clear()

    if success:
        await message.answer(
            f"✅ Operator qo'shildi:\n{full_name} (ID: {tg_id})",
            reply_markup=admin_menu_kb(),
        )
    else:
        await message.answer(
            f"❌ Xatolik: bu ID allaqachon operator sifatida ro'yxatdan o'tgan.",
            reply_markup=admin_menu_kb(),
        )


# ── Remove operator ───────────────────────────────────────────────────────────

@router.message(F.text == "Operator o'chirish")
async def start_remove_operator(message: Message):
    operators = await get_all_operators()
    if not operators:
        await message.answer("Hech qanday operator yo'q.")
        return
    await message.answer(
        "O'chirmoqchi bo'lgan operatorni tanlang:",
        reply_markup=operator_list_kb(operators),
    )


@router.callback_query(F.data.startswith("remove_operator:"))
async def cb_remove_operator(callback: CallbackQuery):
    op_id = int(callback.data.split(":")[1])
    await remove_operator(op_id)

    operators = await get_all_operators()
    if operators:
        await callback.message.edit_reply_markup(reply_markup=operator_list_kb(operators))
        await callback.answer("Operator o'chirildi.")
    else:
        await callback.message.edit_text("Barcha operatorlar o'chirildi.")
        await callback.answer()


# ── Statistics ────────────────────────────────────────────────────────────────

@router.message(F.text == "Statistika")
async def show_stats_menu(message: Message):
    await message.answer("Davrni tanlang:", reply_markup=stats_period_kb())


@router.callback_query(F.data.startswith("stats:"))
async def cb_stats(callback: CallbackQuery):
    period = callback.data.split(":")[1]
    label = PERIOD_LABELS.get(period, period)

    stats = await get_stats(period)
    activity = await get_operator_activity(period)

    lines = [
        f"📊 <b>Statistika — {label}</b>\n",
        f"❓ Savollar: {stats['total_questions']} (javoblangan: {stats['answered_questions']}, kutayotgan: {stats['pending_questions']})",
        f"💬 Jonli chatlar: {stats['total_sessions']}",
        f"⏱ O'rtacha chat davomiyligi: {stats['avg_session_duration']} s\n",
        "<b>Operator faoliyati:</b>",
    ]
    for op in activity:
        lines.append(f"  {op['full_name']}: {op['answered_count']} ta javob")

    await callback.answer()
    await callback.message.answer("\n".join(lines))
