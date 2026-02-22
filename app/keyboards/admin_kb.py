from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def admin_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Operator qo'shish"))
    builder.add(KeyboardButton(text="Operator o'chirish"))
    builder.add(KeyboardButton(text="Statistika"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def stats_period_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Bugun", callback_data="stats:day"))
    builder.add(InlineKeyboardButton(text="Hafta", callback_data="stats:week"))
    builder.add(InlineKeyboardButton(text="Oy", callback_data="stats:month"))
    builder.adjust(3)
    return builder.as_markup()


def operator_list_kb(operators: list) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for op in operators:
        builder.add(InlineKeyboardButton(
            text=f"❌ {op['full_name']}",
            callback_data=f"remove_operator:{op['id']}",
        ))
    builder.adjust(1)
    return builder.as_markup()
