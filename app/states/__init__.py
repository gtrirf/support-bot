from aiogram.fsm.state import State, StatesGroup


class QuestionState(StatesGroup):
    waiting_for_question_text = State()
    waiting_for_answer_text = State()


class LiveChatState(StatesGroup):
    in_live_chat = State()
    operator_in_live_chat = State()


class AdminState(StatesGroup):
    waiting_for_new_operator_id = State()
    waiting_for_new_operator_name = State()
