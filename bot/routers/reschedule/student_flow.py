"""Student-initiated reschedule request flow"""
import logging
from datetime import datetime, date, time, timedelta, timezone
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Teacher, Student, Lesson, RescheduleRequest
from services.reschedule_service import RescheduleService
from services.notification_service import NotificationService
from bot.keyboards.calendar_kb import create_calendar
from bot.utils.helpers import get_student, sanitize_input, safe_parse_callback_int

logger = logging.getLogger(__name__)
router = Router()


class StudentReschedule(StatesGroup):
    select_lesson = State()
    enter_reason = State()
    select_date = State()
    select_time = State()
    confirm = State()


@router.callback_query(StudentReschedule.select_lesson, F.data.startswith('RESCH-LESSON-'))
async def reschedule_select_lesson(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    lesson_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    lesson = await session.get(Lesson, lesson_id)
    student = await get_student(session, query.from_user.id)
    if not lesson or not student or lesson.student_id != student.id:
        await query.message.edit_text("⚠️ Lesson not found.")
        await state.clear()
        return

    await state.update_data(reschedule_lesson_id=lesson_id)
    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to lessons", callback_data="RESCH-BACK-lesson"),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")]
    ]
    await query.message.edit_text(
        "\u23f3 Enter reason for rescheduling the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(StudentReschedule.enter_reason)


@router.callback_query(F.data == "RESCH-BACK-lesson")
async def reschedule_back_to_lesson(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to lesson selection in reschedule flow"""
    await query.answer()
    student = await get_student(session, query.from_user.id)
    if not student:
        await query.message.edit_text("⚠️ You are not registered as a student.")
        await state.clear()
        return

    lessons = await RescheduleService.get_student_future_lessons(session, student.id)
    if not lessons:
        await query.message.edit_text("📭 You have no upcoming lessons to reschedule.")
        await state.clear()
        return

    keyboard = [
        [InlineKeyboardButton(text=f"{l.date} {l.time.strftime('%H:%M')}", callback_data=f"RESCH-LESSON-{l.id}")]
        for l in lessons
    ]
    keyboard.append([InlineKeyboardButton(text="Cancel", callback_data="CANCEL-CONV")])
    await query.message.edit_text(
        "\u23f3 Select lesson to reschedule:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(StudentReschedule.select_lesson)


@router.message(StudentReschedule.enter_reason, F.text)
async def reschedule_enter_reason(message: Message, state: FSMContext, session: AsyncSession):
    text = message.text
    if not text or len(text.strip()) < 5:
        await message.answer("\u23f3 Invalid reason: minimum 5 characters.\n\nEnter reason:\n\nUse /cancel to exit this conversation.")
        return
    if len(text) > 500:
        await message.answer("\u23f3 Invalid reason: maximum 500 characters.\n\nEnter reason:\n\nUse /cancel to exit this conversation.")
        return
    await state.update_data(reschedule_reason=sanitize_input(text))

    now = datetime.now(timezone.utc)
    calendar_markup = create_calendar(now.year, now.month)
    extra_row = [
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="RESCH-BACK-reason"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ]
    calendar_markup.inline_keyboard.append(extra_row)
    await message.answer(
        "\u23f3 Select new date for the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=calendar_markup
    )
    await state.set_state(StudentReschedule.select_date)


@router.callback_query(F.data == "RESCH-BACK-reason")
async def reschedule_back_to_reason(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to reason entry in reschedule flow"""
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to lessons", callback_data="RESCH-BACK-lesson"),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")]
    ]
    await query.message.edit_text(
        "\u23f3 Enter reason for rescheduling the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(StudentReschedule.enter_reason)


@router.callback_query(StudentReschedule.select_date, F.data.startswith('CALENDAR-DAY-'))
async def reschedule_select_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    _, date_info = query.data.split("CALENDAR-DAY-", 1)
    year, month, day = map(int, date_info.split('-'))
    await state.update_data(reschedule_date=(year, month, day))

    keyboard = [
        [InlineKeyboardButton(text=f"{hour}:00", callback_data=f"RESCH-TIME-{hour}")]
        for hour in range(6, 24)
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="RESCH-BACK-date"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ])
    await query.message.edit_text(
        "\u23f3 Select new time:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(StudentReschedule.select_time)


@router.callback_query(StudentReschedule.select_date, F.data.startswith('PREV-MONTH-'))
@router.callback_query(StudentReschedule.select_date, F.data.startswith('NEXT-MONTH-'))
async def reschedule_select_date_nav(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Navigate calendar months in reschedule date selection"""
    await query.answer()
    parts = query.data.split('-', 2)
    year, month = map(int, parts[2].split('-'))
    calendar_markup = create_calendar(year, month)
    extra_row = [
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="RESCH-BACK-reason"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ]
    calendar_markup.inline_keyboard.append(extra_row)
    await query.message.edit_text(
        "\u23f3 Select new date for the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=calendar_markup
    )


@router.callback_query(F.data == "RESCH-BACK-date")
async def reschedule_back_to_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to date selection in reschedule flow"""
    await query.answer()
    now = datetime.now(timezone.utc)
    data = await state.get_data()
    if 'reschedule_date' in data:
        y, m, _ = data['reschedule_date']
        calendar_markup = create_calendar(y, m)
    else:
        calendar_markup = create_calendar(now.year, now.month)
    extra_row = [
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="RESCH-BACK-reason"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ]
    calendar_markup.inline_keyboard.append(extra_row)
    await query.message.edit_text(
        "\u23f3 Select new date for the lesson:\n\nUse /cancel to exit this conversation.",
        reply_markup=calendar_markup
    )
    await state.set_state(StudentReschedule.select_date)


@router.callback_query(F.data == "RESCH-BACK-time")
async def reschedule_back_to_time(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to time selection in reschedule flow"""
    await query.answer()
    keyboard = [
        [InlineKeyboardButton(text=f"{hour}:00", callback_data=f"RESCH-TIME-{hour}")]
        for hour in range(6, 24)
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="RESCH-BACK-date"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ])
    await query.message.edit_text(
        "\u23f3 Select new time:\n\nUse /cancel to exit this conversation.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )
    await state.set_state(StudentReschedule.select_time)


@router.callback_query(StudentReschedule.select_time, F.data.startswith('RESCH-TIME-'))
async def reschedule_select_time(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    hour = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if hour is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    await state.update_data(reschedule_time=hour)

    data = await state.get_data()
    lesson_id = data.get('reschedule_lesson_id')
    reschedule_date = data.get('reschedule_date')
    if not lesson_id or not reschedule_date or 'reschedule_time' not in data or 'reschedule_reason' not in data:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    year, month, day = reschedule_date
    new_hour = data['reschedule_time']
    reason = data['reschedule_reason']

    result = await session.execute(select(Lesson).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        await query.message.edit_text("⚠️ Lesson not found.")
        await state.clear()
        return

    text = (f"\u23f3 Reschedule lesson:\n\n"
            f"OLD: {lesson.date} {lesson.time.strftime('%H:%M')}\n"
            f"NEW: {day}-{month}-{year} {new_hour}:00\n\n"
            f"Reason: {reason}\n\n"
            f"Confirm?\n\nUse /cancel to exit this conversation.")

    keyboard = [
        [InlineKeyboardButton(text="\u2705 Confirm", callback_data="RESCH-CONFIRM-yes")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="RESCH-BACK-time"),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="RESCH-CONFIRM-no")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(StudentReschedule.confirm)


@router.callback_query(StudentReschedule.confirm, F.data.startswith('RESCH-CONFIRM-'))
async def reschedule_confirm(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    choice = query.data.split('-')[-1]
    if choice == 'no':
        await state.clear()
        await query.message.edit_text("❌ Reschedule request cancelled.")
        return

    data = await state.get_data()
    lesson_id = data.get('reschedule_lesson_id')
    reschedule_date = data.get('reschedule_date')
    new_hour = data.get('reschedule_time')
    reason = data.get('reschedule_reason')
    if not lesson_id or not reschedule_date or new_hour is None or not reason:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    year, month, day = reschedule_date

    try:
        result = await session.execute(select(Lesson).filter_by(id=lesson_id))
        lesson = result.scalar_one_or_none()
        if not lesson:
            await state.clear()
            await query.message.edit_text("⚠️ Lesson not found.")
            return

        success, message, request = await RescheduleService.create_reschedule_request(
            session, lesson_id, lesson.student_id, lesson.teacher_id,
            lesson.date, lesson.time, date(year, month, day), time(new_hour, 0), reason
        )
        if not success:
            await state.clear()
            await query.message.edit_text(f"Error: {message}")
            return

        result = await session.execute(select(Teacher).filter_by(id=lesson.teacher_id))
        teacher = result.scalar_one_or_none()
        result = await session.execute(select(Student).filter_by(id=lesson.student_id))
        student = result.scalar_one_or_none()

        if teacher and student:
            keyboard = [
                [InlineKeyboardButton(text="\u2705 Approve", callback_data=f"APPROVE-RESCH-{request.id}")],
                [InlineKeyboardButton(text="\u274c Decline", callback_data=f"DECLINE-RESCH-{request.id}")]
            ]
            try:
                await NotificationService.notify_teacher_reschedule_request_new(
                    query.bot, teacher, student,
                    lesson.date, lesson.time,
                    date(year, month, day), time(new_hour, 0),
                    reason, InlineKeyboardMarkup(inline_keyboard=keyboard)
                )
            except Exception as e:
                logger.error(f"Error sending notification to teacher: {e}")

        await state.clear()
        await query.message.edit_text(f"Reschedule request sent to teacher. {message}")

    except Exception as e:
        logger.error(f"Error confirming reschedule: {e}")
        await state.clear()
        await query.message.edit_text("Error: Failed to confirm reschedule. Please try again.")
