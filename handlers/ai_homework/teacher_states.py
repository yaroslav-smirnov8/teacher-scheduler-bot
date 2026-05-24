"""AI Homework FSM states"""
from aiogram.fsm.state import State, StatesGroup


class AIHomeworkStates(StatesGroup):
    SELECT_MODE = State()
    SELECT_STUDENT = State()
    ENTER_TOPIC = State()
    SELECT_LEVEL = State()
    SELECT_FOCUS = State()
    ENTER_COUNT = State()
    PROVIDE_CONTEXT = State()
    WAITING_JSON = State()
    PREVIEW = State()
    EDIT_TEXT = State()
