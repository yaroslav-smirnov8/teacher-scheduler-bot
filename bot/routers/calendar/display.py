"""Calendar display handlers"""
import logging
from datetime import datetime, date, timedelta, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from models import Teacher, Lesson
from bot.keyboards.calendar_kb import create_calendar
from bot.utils.helpers import get_teacher, safe_parse_callback_int

logger = logging.getLogger(__name__)
router = Router()


async def get_month_lesson_data(session: AsyncSession, teacher_id: int, year: int, month: int) -> dict:
    """Get lesson data for a month: count per day + unpaid status"""
    lesson_data = {}
    first_day = date(year, month, 1)
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    result = await session.execute(
        select(Lesson).filter(
            Lesson.teacher_id == teacher_id,
            Lesson.date >= first_day,
            Lesson.date <= last_day
        )
    )
    lessons = result.scalars().all()

    for lesson in lessons:
        date_str = lesson.date.isoformat()
        if date_str not in lesson_data:
            lesson_data[date_str] = {'count': 0, 'has_unpaid': False, 'all_paid': True}
        lesson_data[date_str]['count'] += 1
        if not lesson.is_paid:
            lesson_data[date_str]['has_unpaid'] = True
            lesson_data[date_str]['all_paid'] = False
        elif lesson.is_paid and lesson_data[date_str]['all_paid']:
            lesson_data[date_str]['all_paid'] = True

    return lesson_data


@router.message(Command('calendar'))
async def show_calendar(message: Message, session: AsyncSession):
    """Show calendar with lesson indicators"""
    now = datetime.now(timezone.utc)
    teacher = await get_teacher(session, message.from_user.id)
    lesson_data = {}
    if teacher:
        lesson_data = await get_month_lesson_data(session, teacher.id, now.year, now.month)
    await message.answer("<b>Select date:</b>", reply_markup=create_calendar(now.year, now.month, lesson_data))


@router.callback_query(F.data == 'calendar')
async def calendar_callback(query: CallbackQuery, session: AsyncSession):
    """Show calendar from main menu"""
    await query.answer()
    now = datetime.now(timezone.utc)
    teacher = await get_teacher(session, query.from_user.id)
    lesson_data = {}
    if teacher:
        lesson_data = await get_month_lesson_data(session, teacher.id, now.year, now.month)
    await query.message.edit_text("Select date:", reply_markup=create_calendar(now.year, now.month, lesson_data))


@router.callback_query(F.data.startswith('PREV-MONTH-'))
@router.callback_query(F.data.startswith('NEXT-MONTH-'))
async def calendar_month_nav(query: CallbackQuery, session: AsyncSession):
    """Navigate months in calendar"""
    await query.answer()
    try:
        parts = query.data.split('-', 2)
        year, month = map(int, parts[2].split('-'))
    except (ValueError, IndexError):
        await query.message.edit_text("⚠️ Invalid calendar navigation.")
        return
    
    teacher = await get_teacher(session, query.from_user.id)
    lesson_data = {}
    if teacher:
        lesson_data = await get_month_lesson_data(session, teacher.id, year, month)
    
    await query.message.edit_text("<b>Select date:</b>", reply_markup=create_calendar(year, month, lesson_data))


@router.callback_query(F.data.startswith('CALENDAR-DAY-'))
async def calendar_day_select(query: CallbackQuery, session: AsyncSession, state):
    """Handle day selection in calendar"""
    await query.answer()
    try:
        _, date_info = query.data.split("CALENDAR-DAY-", 1)
        year, month, day = map(int, date_info.split('-'))
        selected_date = date(year, month, day)
    except (ValueError, IndexError):
        await query.message.edit_text("⚠️ Invalid date selection.")
        return
    
    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    result = await session.execute(
        select(Lesson).options(selectinload(Lesson.student)).filter(
            Lesson.teacher_id == teacher.id,
            Lesson.date == selected_date
        )
    )
    lessons = result.scalars().all()

    await _render_day_view(query, lessons, year, month, day)


async def _render_day_view(query: CallbackQuery, lessons: list, year: int, month: int, day: int):
    """Render the day view with lesson list, cancel, forfeit, and recurring buttons"""
    selected_date = date(year, month, day)
    if not lessons:
        keyboard = [
            [InlineKeyboardButton(text="➕ Schedule Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")]
        ]
        await query.message.edit_text(
            f"No lessons scheduled for {day}-{month}-{year}.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        return

    schedule_lines = []
    for i, lesson in enumerate(lessons):
        prefix = '\U0001f501 ' if lesson.recurring_pattern_id else ''
        status = '\u2705' if lesson.is_paid else '\U0001f534'
        student_name = lesson.student.name if lesson.student else 'Unknown'
        schedule_lines.append(f"{i+1}. {prefix}{lesson.time.strftime('%H:%M')} {status} {student_name}")
    schedule_text = "\n".join(schedule_lines)

    keyboard = [
        [InlineKeyboardButton(text="➕ Add Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")]
    ]
    for i, lesson in enumerate(lessons):
        cancel_btn = InlineKeyboardButton(text=f"\u2716\ufe0f Cancel {i+1}", callback_data=f"SMART-DEL-LESSON-{lesson.id}")
        row = [cancel_btn]
        if lesson.is_paid and lesson.paid_from_balance:
            row.append(InlineKeyboardButton(text=f"🔥 Forfeit {i+1}", callback_data=f"CAL-FORFEIT-{lesson.id}"))
        if lesson.recurring_pattern_id is None:
            row.append(InlineKeyboardButton(text=f"🔄 Recur {i+1}", callback_data=f"CONVERT-RECUR-{lesson.id}"))
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")])

    await query.message.edit_text(
        f"Schedule for {day}-{month}-{year}:\n{schedule_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@router.callback_query(F.data.startswith('CAL-FORFEIT-CONFIRM-'))
async def forfeit_lesson_execute(query: CallbackQuery, session: AsyncSession):
    """Execute forfeit (mark lesson as cancelled, no refund)"""
    await query.answer()
    lesson_id = safe_parse_callback_int(query.data, "CAL-FORFEIT-CONFIRM-")
    if not lesson_id:
        await query.message.edit_text("⚠️ Invalid lesson.")
        return

    result = await session.execute(select(Lesson).filter(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        await query.message.edit_text("⚠️ Lesson not found.")
        return

    lesson.is_paid = False
    lesson.paid_from_balance = False
    lesson.payment_note = "Forfeited (no refund)"
    lesson.paid_at = None
    lesson.paid_by_admin_id = None
    lesson.payment_note = None
    await session.commit()

    await query.message.edit_text(
        f"✅ Lesson {lesson.date.isoformat()} {lesson.time.strftime('%H:%M')} has been forfeited.\n"
        "No balance was refunded.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")]
        ])
    )


@router.callback_query(F.data.startswith('CAL-FORFEIT-BACK-'))
async def forfeit_lesson_back(query: CallbackQuery, session: AsyncSession):
    """Return to day view from forfeit confirmation"""
    await query.answer()
    lesson_id = safe_parse_callback_int(query.data, "CAL-FORFEIT-BACK-")
    if not lesson_id:
        await query.message.edit_text("⚠️ Invalid lesson.")
        return

    result = await session.execute(select(Lesson).filter(Lesson.id == lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        await query.message.edit_text("⚠️ Lesson not found.")
        return

    sel = select(Lesson).options(selectinload(Lesson.student)).filter(
        Lesson.teacher_id == lesson.teacher_id,
        Lesson.date == lesson.date
    )
    lessons = (await session.execute(sel)).scalars().all()
    await _render_day_view(query, lessons, lesson.date.year, lesson.date.month, lesson.date.day)


@router.callback_query(F.data.startswith('CAL-FORFEIT-'))
async def forfeit_lesson_confirm(query: CallbackQuery, session: AsyncSession):
    """Show forfeit confirmation for a balance-paid lesson"""
    await query.answer()
    lesson_id = safe_parse_callback_int(query.data, "CAL-FORFEIT-")
    if not lesson_id:
        await query.message.edit_text("⚠️ Invalid lesson.")
        return

    result = await session.execute(
        select(Lesson).options(selectinload(Lesson.student)).filter(Lesson.id == lesson_id)
    )
    lesson = result.scalar_one_or_none()
    if not lesson:
        await query.message.edit_text("⚠️ Lesson not found.")
        return

    student_name = lesson.student.name if lesson.student else 'Unknown'
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, forfeit", callback_data=f"CAL-FORFEIT-CONFIRM-{lesson.id}")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data=f"CAL-FORFEIT-BACK-{lesson.id}")]
    ])
    await query.message.edit_text(
        f"🔥 Forfeit lesson for {student_name} on {lesson.date.isoformat()} at {lesson.time.strftime('%H:%M')}?\n\n"
        "This lesson was paid from balance. Forfeiting will NOT refund the balance.",
        reply_markup=keyboard
    )
