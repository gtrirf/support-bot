from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def admin_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Operator qo'shish", callback_data="admin:add_operator")
    builder.button(text="➖ Operator o'chirish", callback_data="admin:remove_operator")
    builder.button(text="📊 Statistika", callback_data="admin:stats")
    builder.adjust(2, 1)
    return builder.as_markup()


def admin_cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="admin:cancel")
    builder.adjust(1)
    return builder.as_markup()


def back_to_admin_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Admin panel", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()


def stats_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📅 Bugun", callback_data="stats:day")
    builder.button(text="📆 Hafta", callback_data="stats:week")
    builder.button(text="🗓 Oy", callback_data="stats:month")
    builder.button(text="🔙 Orqaga", callback_data="admin:menu")
    builder.adjust(3, 1)
    return builder.as_markup()


def operator_list_kb(operators: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for op in operators:
        builder.button(
            text=f"❌ {op['full_name']}",
            callback_data=f"remove_operator:{op['id']}",
        )
    builder.button(text="🔙 Orqaga", callback_data="admin:menu")
    builder.adjust(1)
    return builder.as_markup()
