from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def question_notification_kb(q_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✏️ Javob berish",
        callback_data=f"answer_question:{q_id}",
    ))
    return builder.as_markup()


def question_claimed_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Javob berildi ✅", callback_data="noop"))
    return builder.as_markup()


def session_notification_kb(s_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="📞 Qabul qilish",
        callback_data=f"accept_session:{s_id}",
    ))
    return builder.as_markup()


def session_claimed_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Qabul qilindi ✅", callback_data="noop"))
    return builder.as_markup()


def end_chat_kb(s_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="🔴 Chatni yakunlash",
        callback_data=f"end_session:{s_id}",
    ))
    return builder.as_markup()
