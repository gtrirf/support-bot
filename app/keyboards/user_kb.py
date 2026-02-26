from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_menu_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❓ Savol yoki murojaat", callback_data="menu:question_type")
    builder.adjust(1)
    return builder.as_markup()


def question_type_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Savol qoldirish", callback_data="action:ask_question")
    builder.button(text="💬 Operator bilan chat", callback_data="action:live_chat")
    builder.button(text="🔙 Orqaga", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def cancel_question_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Bekor qilish", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def submit_question_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Yuborish", callback_data="question:submit")
    builder.button(text="❌ Bekor qilish", callback_data="menu:main")
    builder.adjust(2)
    return builder.as_markup()


def rating_kb(entity_type: str, entity_id: int, operator_db_id: int) -> InlineKeyboardMarkup:
    """entity_type: 'q' for question, 's' for live session."""
    builder = InlineKeyboardBuilder()
    stars_labels = ["1 ⭐", "2 ⭐⭐", "3 ⭐⭐⭐", "4 ⭐⭐⭐⭐", "5 ⭐⭐⭐⭐⭐"]
    for i, label in enumerate(stars_labels, start=1):
        builder.button(
            text=label,
            callback_data=f"rate:{entity_type}:{entity_id}:{operator_db_id}:{i}",
        )
    builder.adjust(5)
    return builder.as_markup()


def live_chat_kb(session_id: int) -> InlineKeyboardMarkup:
    """Shown to user while waiting for operator or in active chat."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🚪 Chatdan chiqish", callback_data=f"chat:leave:{session_id}")
    builder.adjust(1)
    return builder.as_markup()
