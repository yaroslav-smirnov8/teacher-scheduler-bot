"""Convert single lesson to recurring flow handlers"""
import logging
from datetime import datetime, date, time, timezone
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from database import SessionLocal
from models import Teacher, Student, Lesson, RecurringPattern
from services.recurring_service import RecurringLessonService
from services.notification_service import NotificationService
from handlers.recurring.constants import (
    CONVERT_SELECT_FREQUENCY, CONVERT_SELECT_END_DATE, CONVERT_CONFIRM,
    CONV_BACK_FREQ, CONV_BACK_END_DATE, CONV_BACK_LESSON,
    _append_back_button,
)
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)


async def convert_to_recurring_start(query: CallbackQuery, state: FSMContext, session) -> None:
    """Start converting a single lesson to recurring"""
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return

    lesson_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return

    result = await session.execute(select(Lesson).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson or lesson.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only convert your own lessons.")
        await state.clear()
        return

    await state.update_data(convert_lesson_id=lesson_id)

    keyboard = [
        [InlineKeyboardButton(text="Weekly", callback_data="CONV-FREQ-weekly")],
        [InlineKeyboardButton(text="Biweekly", callback_data="CONV-FREQ-biweekly")],
        [InlineKeyboardButton(text="Monthly", callback_data="CONV-FREQ-monthly")],
    ]
    await _append_back_button(keyboard, CONV_BACK_LESSON)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text("Select frequency:", reply_markup=reply_markup)
    await state.set_state(CONVERT_SELECT_FREQUENCY)


async def convert_select_frequency(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle frequency selection for convert"""
    frequency = query.data.split('-')[-1]
    await state.update_data(convert_frequency=frequency)
    await _show_convert_end_date(query, state)


async def _show_convert_end_date(query: CallbackQuery, state: FSMContext) -> None:
    """Show end date calendar for convert flow (used for Back navigation)"""
    from bot.keyboards.calendar_kb import create_calendar
    now = datetime.now(timezone.utc)
    calendar_markup = create_calendar(now.year, now.month)
    extra_row = [
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=CONV_BACK_FREQ),
        InlineKeyboardButton(text="\u23ed\ufe0f No end date", callback_data="CONV-END-NONE"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CONV-CONFIRM-no")
    ]
    calendar_markup.inline_keyboard.append(extra_row)
    await query.message.edit_text(
        "Select end date (or 'No end date'):",
        reply_markup=calendar_markup
    )
    await state.set_state(CONVERT_SELECT_END_DATE)


async def convert_select_end_date(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle end date selection for convert"""
    from bot.keyboards.calendar_kb import create_calendar

    if query.data.startswith('CALENDAR-DAY-'):
        _, date_info = query.data.split("CALENDAR-DAY-", 1)
        year, month, day = map(int, date_info.split('-'))
        await state.update_data(convert_end_date=date(year, month, day))
    elif query.data.startswith('PREV-MONTH-') or query.data.startswith('NEXT-MONTH-'):
        parts = query.data.split('-', 2)
        year, month = map(int, parts[2].split('-'))
        calendar_markup = create_calendar(year, month)
        extra_row = [
            InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=CONV_BACK_FREQ),
            InlineKeyboardButton(text="\u23ed\ufe0f No end date", callback_data="CONV-END-NONE"),
            InlineKeyboardButton(text="\u274c Cancel", callback_data="CONV-CONFIRM-no")
        ]
        calendar_markup.inline_keyboard.append(extra_row)
        await query.message.edit_text("Select end date:", reply_markup=calendar_markup)
        return
    else:
        await state.update_data(convert_end_date=None)

    data = await state.get_data()
    lesson_id = data.get('convert_lesson_id')
    frequency = data.get('convert_frequency')
    if not lesson_id or not frequency:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    end_date = data.get('convert_end_date')

    result = await session.execute(select(Lesson).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()
    lesson_info = f"{lesson.date} {lesson.time.strftime('%H:%M')}" if lesson else "Unknown"

    end_text = f" until {end_date}" if end_date else " (no end date)"
    freq_text = {'weekly': 'Weekly', 'biweekly': 'Biweekly', 'monthly': 'Monthly'}.get(frequency, frequency)

    summary = (f"Convert to Recurring:\n\n"
               f"Lesson: {lesson_info}\n"
               f"Frequency: {freq_text}{end_text}\n\n"
               f"Confirm?")

    keyboard = [
        [InlineKeyboardButton(text="\u2705 Confirm", callback_data="CONV-CONFIRM-yes")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=CONV_BACK_END_DATE),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="CONV-CONFIRM-no")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text(summary, reply_markup=reply_markup)
    await state.set_state(CONVERT_CONFIRM)


async def convert_confirm(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle convert confirmation"""
    choice = query.data.split('-')[-1]
    if choice == 'no':
        await state.clear()
        await query.message.edit_text("❌ Conversion cancelled.")
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return

    data = await state.get_data()
    lesson_id = data.get('convert_lesson_id')
    frequency = data.get('convert_frequency')
    if not lesson_id or not frequency:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    end_date = data.get('convert_end_date')

    result = await session.execute(select(Lesson).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson or lesson.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only convert your own lessons.")
        await state.clear()
        return

    pattern_config = {
        'frequency': frequency,
        'interval': 1,
        'end_date': end_date
    }

    success, message, pattern = await RecurringLessonService.convert_to_recurring(
        session, lesson_id, pattern_config
    )

    if success:
        result = await session.execute(select(Lesson).options(selectinload(Lesson.student)).filter_by(id=lesson_id))
        lesson = result.scalar_one_or_none()
        if lesson and lesson.student:
            result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
            teacher = result.scalar_one_or_none()
            if teacher:
                await NotificationService.notify_student_recurring_created(
                    query.bot, lesson.student, teacher, pattern
                )
        await query.message.edit_text(f"\u2705 {message}")
    else:
        await query.message.edit_text(f"\u274c {message}")

    await state.clear()
