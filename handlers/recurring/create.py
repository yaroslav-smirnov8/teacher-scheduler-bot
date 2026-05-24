"""Create recurring lesson flow handlers"""
import logging
from datetime import datetime, date, time, timezone
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from database import SessionLocal
from models import Teacher, Student, RecurringPattern
from services.recurring_service import RecurringLessonService
from services.notification_service import NotificationService
from handlers.recurring.constants import (
    RECURRING_SELECT_STUDENT, RECURRING_SELECT_FREQUENCY, RECURRING_SELECT_WEEKDAY,
    RECURRING_SELECT_DAY_OF_MONTH, RECURRING_SELECT_TIME, RECURRING_SELECT_END_DATE,
    RECURRING_CONFIRM,
    REC_BACK_STUDENT, REC_BACK_FREQUENCY, REC_BACK_WEEKDAY, REC_BACK_DAY,
    REC_BACK_TIME, REC_BACK_END_DATE,
    _append_back_button,
)
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)


async def create_recurring_start(update: Message | CallbackQuery, state: FSMContext, session) -> None:
    """Start creating a recurring lesson"""
    if isinstance(update, CallbackQuery):
        user_id = update.from_user.id
        query = update
    else:
        user_id = update.from_user.id
        query = None

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        text = "You are not registered as a teacher."
        if query:
            await query.message.edit_text(text)
        else:
            await update.answer(text)
        return

    result = await session.execute(select(Student).filter_by(teacher_id=teacher.id))
    students = result.scalars().all()

    if not students:
        text = "You have no students."
        if query:
            await query.message.edit_text(text)
        else:
            await update.answer(text)
        return

    keyboard = [
        [InlineKeyboardButton(text=student.name, callback_data=f"REC-STUDENT-{student.id}")]
        for student in students
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ])

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    text = "Select student for recurring lesson:"

    if query:
        await query.message.edit_text(text, reply_markup=reply_markup)
    else:
        await update.answer(text, reply_markup=reply_markup)

    await state.set_state(RECURRING_SELECT_STUDENT)


async def recurring_select_student(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle student selection for recurring lesson"""
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    await state.update_data(recurring_student_id=student_id)

    keyboard = [
        [InlineKeyboardButton(text="Weekly", callback_data="REC-FREQ-weekly")],
        [InlineKeyboardButton(text="Biweekly", callback_data="REC-FREQ-biweekly")],
        [InlineKeyboardButton(text="Monthly", callback_data="REC-FREQ-monthly")],
    ]
    await _append_back_button(keyboard, REC_BACK_STUDENT)

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text("Select frequency:", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_FREQUENCY)


async def _show_frequency_menu(query: CallbackQuery, state: FSMContext) -> None:
    """Show frequency selection menu (used for Back navigation)"""
    keyboard = [
        [InlineKeyboardButton(text="Weekly", callback_data="REC-FREQ-weekly")],
        [InlineKeyboardButton(text="Biweekly", callback_data="REC-FREQ-biweekly")],
        [InlineKeyboardButton(text="Monthly", callback_data="REC-FREQ-monthly")],
    ]
    await _append_back_button(keyboard, REC_BACK_STUDENT)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text("Select frequency:", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_FREQUENCY)


async def recurring_select_frequency(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle frequency selection"""
    frequency = query.data.split('-')[-1]
    await state.update_data(recurring_frequency=frequency)

    if frequency in ('weekly', 'biweekly'):
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        keyboard = [
            [InlineKeyboardButton(text=name, callback_data=f"REC-WEEKDAY-{i}")]
            for i, name in enumerate(weekday_names)
        ]
        await _append_back_button(keyboard, REC_BACK_FREQUENCY)
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text("Select day of week:", reply_markup=reply_markup)
        await state.set_state(RECURRING_SELECT_WEEKDAY)
    else:  # monthly
        keyboard = [
            [InlineKeyboardButton(text=str(day), callback_data=f"REC-DAY-{day}")]
            for day in range(1, 32)
        ]
        rows = []
        for i in range(0, len(keyboard), 7):
            row = [keyboard[i + j][0] for j in range(min(7, len(keyboard) - i))]
            rows.append(row)
        await _append_back_button(rows, REC_BACK_FREQUENCY)
        reply_markup = InlineKeyboardMarkup(inline_keyboard=rows)
        await query.message.edit_text("Select day of month:", reply_markup=reply_markup)
        await state.set_state(RECURRING_SELECT_DAY_OF_MONTH)


async def recurring_select_weekday(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle weekday selection"""
    weekday = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if weekday is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    await state.update_data(recurring_weekday=weekday)
    await _show_time_selection(query, state)


async def recurring_select_day_of_month(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle day of month selection"""
    day = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if day is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    await state.update_data(recurring_day_of_month=day)
    await _show_time_selection(query, state)


async def _show_time_selection(query: CallbackQuery, state: FSMContext) -> None:
    """Show time selection keyboard"""
    keyboard = []
    for hour in range(6, 24):
        keyboard.append([InlineKeyboardButton(text=f"{hour}:00", callback_data=f"REC-TIME-{hour}")])
    rows = []
    for i in range(0, len(keyboard), 3):
        row = [keyboard[i][0]]
        if i + 1 < len(keyboard):
            row.append(keyboard[i + 1][0])
        if i + 2 < len(keyboard):
            row.append(keyboard[i + 2][0])
        rows.append(row)
    data = await state.get_data()
    freq = data.get('recurring_frequency')
    back_cb = REC_BACK_WEEKDAY if freq in ('weekly', 'biweekly') else REC_BACK_DAY
    await _append_back_button(rows, back_cb)
    reply_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await query.message.edit_text("Select time:", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_TIME)


async def recurring_select_time(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle time selection"""
    hour = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if hour is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    await state.update_data(recurring_hour=hour)

    from bot.keyboards.calendar_kb import create_calendar
    now = datetime.now(timezone.utc)
    calendar_markup = create_calendar(now.year, now.month)
    extra_row = [
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=REC_BACK_TIME),
        InlineKeyboardButton(text="\u23ed\ufe0f No end date", callback_data="REC-END-NONE"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ]
    calendar_markup.inline_keyboard.append(extra_row)
    await query.message.edit_text(
        "Select end date (or 'No end date'):",
        reply_markup=calendar_markup
    )
    await state.set_state(RECURRING_SELECT_END_DATE)


async def recurring_select_end_date(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle end date selection"""
    from bot.keyboards.calendar_kb import create_calendar

    if query.data.startswith('CALENDAR-DAY-'):
        _, date_info = query.data.split("CALENDAR-DAY-", 1)
        year, month, day = map(int, date_info.split('-'))
        await state.update_data(recurring_end_date=date(year, month, day))
    elif query.data.startswith('PREV-MONTH-') or query.data.startswith('NEXT-MONTH-'):
        parts = query.data.split('-', 2)
        year, month = map(int, parts[2].split('-'))
        calendar_markup = create_calendar(year, month)
        extra_row = [
            InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=REC_BACK_TIME),
            InlineKeyboardButton(text="\u23ed\ufe0f No end date", callback_data="REC-END-NONE"),
            InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
        ]
        calendar_markup.inline_keyboard.append(extra_row)
        await query.message.edit_text("Select end date:", reply_markup=calendar_markup)
        return
    else:
        await state.update_data(recurring_end_date=None)

    data = await state.get_data()
    student_id = data.get('recurring_student_id')
    frequency = data.get('recurring_frequency')
    hour = data.get('recurring_hour')
    if not student_id or not frequency or hour is None:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    end_date = data.get('recurring_end_date')

    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    student_name = student.name if student else "Unknown"

    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    freq_text = {'weekly': 'Weekly', 'biweekly': 'Biweekly', 'monthly': 'Monthly'}.get(frequency, frequency)
    day_text = ""
    if frequency in ('weekly', 'biweekly'):
        weekday = data.get('recurring_weekday')
        day_text = f" on {weekday_names[weekday]}" if weekday is not None else ""
    elif frequency == 'monthly':
        dom = data.get('recurring_day_of_month')
        day_text = f" on day {dom}" if dom is not None else ""

    end_text = f" until {end_date}" if end_date else " (no end date)"

    summary = (f"Recurring Lesson Summary:\n\n"
               f"Student: {student_name}\n"
               f"Frequency: {freq_text}{day_text}\n"
               f"Time: {hour}:00\n"
               f"End: {end_text}\n\n"
               f"Confirm?")

    keyboard = [
        [InlineKeyboardButton(text="\u2705 Confirm", callback_data="REC-CONFIRM-yes")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=REC_BACK_END_DATE),
         InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text(summary, reply_markup=reply_markup)
    await state.set_state(RECURRING_CONFIRM)


async def recurring_confirm(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle recurring lesson confirmation"""
    choice = query.data.split('-')[-1]

    if choice == 'no':
        await state.clear()
        await query.message.edit_text("❌ Recurring lesson creation cancelled.")
        return

    data = await state.get_data()
    student_id = data.get('recurring_student_id')
    frequency = data.get('recurring_frequency')
    hour = data.get('recurring_hour')
    if not student_id or not frequency or hour is None:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    end_date = data.get('recurring_end_date')

    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        await state.clear()
        return

    pattern = RecurringPattern(
        teacher_id=teacher.id,
        student_id=student_id,
        start_date=datetime.now(timezone.utc).date(),
        end_date=end_date,
        time=time(hour, 0),
        frequency=frequency,
        interval=1,
        weekday=data.get('recurring_weekday'),
        day_of_month=data.get('recurring_day_of_month')
    )

    try:
        success, message, created_pattern = await RecurringLessonService.create_recurring_lesson(
            session, teacher.id, student_id, pattern
        )

        if success:
            result = await session.execute(select(Student).filter_by(id=student_id))
            student = result.scalar_one_or_none()
            if student:
                await NotificationService.notify_student_recurring_created(
                    query.bot, student, teacher, created_pattern
                )
            await query.message.edit_text(f"\u2705 {message}")
        else:
            await query.message.edit_text(f"\u274c {message}")

    except Exception as e:
        logger.error(f"Error creating recurring lesson: {e}")
        await query.message.edit_text("\u274c Failed to create recurring lesson. Please try again.")

    await state.clear()


async def cancel_recurring_conversation(update, state: FSMContext) -> None:
    """Cancel recurring lesson creation"""
    await state.clear()
    if hasattr(update, 'edit_message_text'):
        await update.edit_message_text("Recurring lesson creation cancelled.")
    elif hasattr(update, 'answer'):
        await update.answer("Recurring lesson creation cancelled.")
