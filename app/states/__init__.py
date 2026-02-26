from aiogram.fsm.state import State, StatesGroup


class QuestionState(StatesGroup):
    collecting_messages = State()
    collecting_answer_messages = State()


class LiveChatState(StatesGroup):
    in_live_chat = State()
    operator_in_live_chat = State()


class AdminState(StatesGroup):
    waiting_for_new_operator_id = State()
    waiting_for_new_operator_name = State()
