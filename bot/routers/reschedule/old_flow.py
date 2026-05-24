"""Old reschedule flow (legacy) - teacher initiated"""
import logging
from datetime import datetime, date, time, timedelta, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Teacher, Student, Lesson
from bot.utils.helpers import get_student, sanitize_input, safe_parse_callback_int

logger = logging.getLogger(__name__)
router = Router()


class OldReschedule(StatesGroup):
    select_lesson = State()
    reason = State()
    new_time = State()


@router.message(Command('reschedule'))
async def old_reschedule_start(message: Message, state: FSMContext, session: AsyncSession):
    """Legacy: Start reschedule flow"""
    student = await get_student(session, message.from_user.id)
    if not student:
        await message.answer("You are not registered as a student.")
        return

    today = datetime.now(timezone.utc).date()
    result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time)
    )
    lessons = result.scalars().all()
    if not lessons:
        await message.answer("You have no scheduled lessons.")
        return

    keyboard = [
        [InlineKeyboardButton(
            text=f"{l.date} {l.time.strftime('%H:%M')}",
            callback_data=f"OLD-RESCH-LESSON-{l.id}"
        )] for l in lessons
    ]
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="CANCEL-CONV")])
    await message.answer(
        "\u23f3 Select lesson to reschedule:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(OldReschedule.select_lesson)


@router.callback_query(OldReschedule.select_lesson, F.data.startswith('OLD-RESCH-LESSON-'))
async def old_reschedule_select_lesson(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    lesson_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    await state.update_data(lesson_id=lesson_id)
    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to lessons", callback_data="OLD-RESCH-BACK-lesson"),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")]
    ]
    await query.message.edit_text(
        "\u23f3 Enter reason for rescheduling the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(OldReschedule.reason)


@router.callback_query(F.data == "OLD-RESCH-BACK-lesson")
async def old_reschedule_back_to_lesson(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to lesson selection in old reschedule flow"""
    await query.answer()
    student = await get_student(session, query.from_user.id)
    if not student:
        await query.message.edit_text("You are not registered as a student.")
        await state.clear()
        return

    today = datetime.now(timezone.utc).date()
    result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time)
    )
    lessons = result.scalars().all()
    if not lessons:
        await query.message.edit_text("You have no scheduled lessons.")
        await state.clear()
        return

    keyboard = [
        [InlineKeyboardButton(text=f"{l.date} {l.time.strftime('%H:%M')}", callback_data=f"OLD-RESCH-LESSON-{l.id}")]
        for l in lessons
    ]
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="CANCEL-CONV")])
    await query.message.edit_text(
        "\u23f3 Select lesson to reschedule:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(OldReschedule.select_lesson)


@router.message(OldReschedule.reason, F.text)
async def old_reschedule_reason(message: Message, state: FSMContext, session: AsyncSession):
    text = message.text
    if not text or len(text.strip()) < 5:
        await message.answer("\u23f3 Invalid reason: Input must be at least 5 characters.\n\nEnter reason:\n\nUse /cancel to exit this conversation.")
        return
    if len(text) > 500:
        await message.answer("\u23f3 Invalid reason: Input must not exceed 500 characters.\n\nEnter reason:\n\nUse /cancel to exit this conversation.")
        return
    await state.update_data(reason=sanitize_input(text))

    keyboard = [
        [InlineKeyboardButton(text=f"{hour}:00", callback_data=f"OLD-RESCH-TIME-{hour}")]
        for hour in range(6, 24)
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="OLD-RESCH-BACK-reason"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ])
    await message.answer(
        "\u23f3 Select new time:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(OldReschedule.new_time)


@router.callback_query(F.data == "OLD-RESCH-BACK-reason")
async def old_reschedule_back_to_reason(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to reason entry in old reschedule flow"""
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to lessons", callback_data="OLD-RESCH-BACK-lesson"),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")]
    ]
    await query.message.edit_text(
        "\u23f3 Enter reason for rescheduling the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(OldReschedule.reason)


@router.callback_query(OldReschedule.new_time, F.data.startswith('OLD-RESCH-TIME-'))
async def old_reschedule_confirm(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    hour = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if hour is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    reason = data.get('reason')
    if not lesson_id or not reason:
        await query.message.edit_text("Session expired. Please start over.")
        await state.clear()
        return

    result = await session.execute(select(Lesson).options(selectinload(Lesson.student), selectinload(Lesson.teacher)).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        await query.message.edit_text("Lesson not found.")
        await state.clear()
        return

    student = await get_student(session, query.from_user.id)
    if not student or lesson.student_id != student.id:
        await query.message.edit_text("You can only reschedule your own lessons.")
        await state.clear()
        return

    if lesson.date < datetime.now(timezone.utc).date():
        await query.message.edit_text("Cannot reschedule a lesson in the past.")
        await state.clear()
        return

    new_time = time(hour, 0)

    result = await session.execute(
        select(Lesson).filter(
            Lesson.teacher_id == lesson.teacher_id,
            Lesson.date == lesson.date,
            Lesson.time == new_time
        )
    )
    if result.scalar_one_or_none():
        await query.message.edit_text(f"On {lesson.date} at {hour}:00 the teacher already has a lesson scheduled.")
        await state.clear()
        return

    result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == lesson.student_id,
            Lesson.date == lesson.date,
            Lesson.time == new_time
        )
    )
    if result.scalar_one_or_none():
        await query.message.edit_text(f"On {lesson.date} at {hour}:00 the student already has a lesson scheduled.")
        await state.clear()
        return

    teacher = lesson.teacher
    if teacher and teacher.telegram_id:
        keyboard = [
            [InlineKeyboardButton(text="Reschedule", callback_data=f"ACCEPT-RESCHEDULE-{lesson.id}-{hour}")],
            [InlineKeyboardButton(text="Decline", callback_data=f"DECLINE-RESCHEDULE-{lesson.id}")]
        ]
        await query.bot.send_message(
            chat_id=teacher.telegram_id,
            text=f"Student {lesson.student.name} requests to reschedule lesson from {lesson.time.strftime('%H:%M')} to {hour}:00 for reason: {reason}. Do you agree?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )

    await state.clear()
    await query.message.edit_text("Request to reschedule lesson sent to teacher.")
