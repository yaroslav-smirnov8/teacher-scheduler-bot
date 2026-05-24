"""Shared utilities for student interactive exercise session"""
import logging
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


def _back_to_homework_kb(hw_id: int) -> list[list[InlineKeyboardButton]]:
    return [[InlineKeyboardButton(text="\u2b05\ufe0f Back to Homework", callback_data=f"view_hw_{hw_id}")]]


def _build_feedback(is_correct: bool, answer: str, correct: str, explanation: str) -> str:
    icon = "\u2705" if is_correct else "\u274c"
    lines = [
        f"{icon} <b>{'Correct!' if is_correct else 'Not quite'}</b>",
        f"\nYour answer: {answer}",
        f"Correct answer: {correct}",
    ]
    if explanation:
        lines.append(f"\n\U0001f4dd {explanation}")
    return "\n".join(lines)


async def _show_feedback(query_or_msg, state: FSMContext, feedback: str) -> None:
    data = await state.get_data()
    if "current_idx" not in data or "total" not in data:
        await state.clear()
        msg = "Session expired. Please start again."
        if isinstance(query_or_msg, CallbackQuery):
            await query_or_msg.message.edit_text(msg)
        else:
            await query_or_msg.answer(msg)
        return
    idx: int = data["current_idx"]
    total: int = data["total"]
    is_last = idx + 1 >= total

    next_label = "\U0001f3af See Results" if is_last else "\u23ed\ufe0f Next"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=next_label, callback_data="ex_nx")],
        [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
    ])

    if isinstance(query_or_msg, CallbackQuery):
        await query_or_msg.message.edit_text(text=feedback, reply_markup=keyboard)
    else:
        await query_or_msg.answer(text=feedback, reply_markup=keyboard)


async def _show_feedback_from_message(message: Message, state: FSMContext, feedback: str) -> None:
    await _show_feedback(message, state, feedback)
