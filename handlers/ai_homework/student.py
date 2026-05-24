"""Student interactive exercise session — FSM flow"""
import json
import logging

from sqlalchemy import select
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from models import Student, Homework
from bot.utils.helpers import safe_parse_callback_int
from .exercise_common import _back_to_homework_kb, _build_feedback, _show_feedback, _show_feedback_from_message
from .exercise_display import _show_exercise
from .exercise_handlers import ex_option as _ex_option, ex_toggle as _ex_toggle, ex_confirm as _ex_confirm
from .student_answers import _show_results, _save_attempt

logger = logging.getLogger(__name__)


class StudentExerciseStates(StatesGroup):
    EXERCISE = State()


async def ex_start(query: CallbackQuery, state: FSMContext, session) -> None:
    hw_id = safe_parse_callback_int(query.data, delimiter="_", position=-1)
    if hw_id is None:
        await query.answer("Invalid homework", show_alert=True)
        return

    homework = await session.get(Homework, hw_id)
    if not homework or not homework.json_content:
        await query.answer("No interactive exercises found", show_alert=True)
        return

    user_id = query.from_user.id
    result = await session.execute(select(Student).filter_by(telegram_id=user_id))
    student = result.scalar_one_or_none()
    if not student or homework.student_id != student.id:
        await query.answer("Homework not found", show_alert=True)
        return

    try:
        data = json.loads(homework.json_content)
        exercises = data.get("exercises", [])
    except (json.JSONDecodeError, KeyError):
        await query.answer("Invalid exercise data", show_alert=True)
        return

    if not exercises:
        await query.answer("No exercises in this homework", show_alert=True)
        return

    await state.set_state(StudentExerciseStates.EXERCISE)
    await state.update_data(
        homework_id=hw_id,
        student_id=student.id,
        exercises=exercises,
        current_idx=0,
        results=[],
        total=len(exercises),
    )

    await query.message.edit_text(
        text=f"\U0001f3ae <b>Interactive Exercises</b>\n\n"
        f"Homework #{hw_id}\n"
        f"Total exercises: {len(exercises)}\n\n"
        "Let's begin! \U0001f44d",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f3af Start", callback_data="ex_nx")],
            [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
        ]),
    )


async def ex_option(query: CallbackQuery, state: FSMContext, session=None) -> None:
    await _ex_option(query, state)


async def ex_toggle(query: CallbackQuery, state: FSMContext, session=None) -> None:
    await _ex_toggle(query, state)


async def ex_confirm(query: CallbackQuery, state: FSMContext, session=None) -> None:
    await _ex_confirm(query, state)


async def ex_text_answer(message: Message, state: FSMContext, session) -> None:
    from .student_answers import ex_text_answer as _ex_text_answer
    await _ex_text_answer(message, state, session)


async def ex_next(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    if "current_idx" not in data or "total" not in data:
        await state.clear()
        await query.message.edit_text("Session expired. Please start again.")
        return
    idx: int = data["current_idx"]
    total: int = data["total"]
    results: list[dict] = data.get("results", [])

    if not results:
        await _show_exercise(query, state)
        return

    next_idx = idx + 1
    if next_idx >= total:
        await _show_results(query, state, session)
        return

    await state.update_data(current_idx=next_idx)
    await _show_exercise(query, state)


async def ex_restart(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    exercises = data.get("exercises", [])
    if not exercises:
        await query.answer("No exercises to restart", show_alert=True)
        return

    await state.update_data(current_idx=0, results=[], selected=[], order_selected=[],
                            syn_pair_idx=0, syn_pair_results=[], cloze_gap_idx=0, cloze_gap_results=[])
    await _show_exercise(query, state)


async def ex_end(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    hw_id = data.get("homework_id")
    student_id = data.get("student_id")
    results: list[dict] = data.get("results", [])
    total: int = data.get("total", 0)
    correct_count = sum(1 for r in results if r.get("correct") is True)

    if results:
        await _save_attempt(hw_id, student_id, results, correct_count, total, session)

    await state.clear()

    if hw_id:
        await query.message.edit_text(
            text="Exercise session ended.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back to Homework", callback_data=f"view_hw_{hw_id}")],
            ]),
        )
    else:
        await query.message.edit_text("Exercise session ended.")
