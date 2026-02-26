from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def question_notification_kb(q_id: int, user_db_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="✏️ Javob berish",
        callback_data=f"answer_question:{q_id}",
    ))
    builder.add(InlineKeyboardButton(
        text="👤 Profil",
        callback_data=f"profile:user:{user_db_id}",
    ))
    builder.adjust(2)
    return builder.as_markup()


def question_claimed_kb(user_db_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Javob berildi ✅", callback_data="noop"))
    builder.add(InlineKeyboardButton(
        text="👤 Profil",
        callback_data=f"profile:user:{user_db_id}",
    ))
    builder.adjust(2)
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


def end_chat_kb(s_id: int, user_db_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="👤 Profil",
        callback_data=f"profile:user:{user_db_id}",
    ))
    builder.add(InlineKeyboardButton(
        text="🔴 Chatni yakunlash",
        callback_data=f"end_session:{s_id}",
    ))
    builder.adjust(2)
    return builder.as_markup()


def ended_chat_kb(user_db_id: int) -> InlineKeyboardMarkup:
    """Shown after chat is closed — only profile button remains."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(
        text="👤 Profil",
        callback_data=f"profile:user:{user_db_id}",
    ))
    return builder.as_markup()


def submit_answer_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data="answer:submit")
    builder.button(text="❌ Bekor qilish", callback_data="answer:cancel")
    builder.adjust(2)
    return builder.as_markup()
