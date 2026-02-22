from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def main_menu_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Menda savol bor"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)


def question_type_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Savol qoldirish"))
    builder.add(KeyboardButton(text="Operatorga bog'lanish"))
    builder.add(KeyboardButton(text="Orqaga"))
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)


def cancel_kb() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Bekor qilish"))
    return builder.as_markup(resize_keyboard=True)


def live_chat_kb() -> ReplyKeyboardMarkup:
    """Shown to user while waiting for operator or in active chat."""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="Chatdan chiqish"))
    return builder.as_markup(resize_keyboard=True)


def remove_kb() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
