"""View recurring schedule handler"""
import logging
from datetime import datetime, date, time, timedelta, timezone
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Teacher, Student, Lesson
from services.recurring_service import RecurringLessonService

logger = logging.getLogger(__name__)


async def view_recurring_schedule(query: CallbackQuery, state: FSMContext, session) -> None:
    """View teacher's schedule with recurring lessons"""
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    today = datetime.now(timezone.utc).date()
    end_date = today + timedelta(days=30)

    lessons = await RecurringLessonService.get_recurring_lessons(
        session, teacher_id=teacher.id, start_date=today, end_date=end_date
    )

    if not lessons:
        await query.message.edit_text("No lessons scheduled for the next 30 days.")
        return

    schedule_by_date = {}
    for lesson in lessons:
        if lesson.date not in schedule_by_date:
            schedule_by_date[lesson.date] = []
        schedule_by_date[lesson.date].append(lesson)

    lines = ["\U0001f4c5 Schedule (next 30 days):\n"]
    for lesson_date in sorted(schedule_by_date.keys()):
        lines.append(f"\n\U0001f4c6 {lesson_date}:")
        for lesson in sorted(schedule_by_date[lesson_date], key=lambda l: l.time):
            student_name = lesson.student.name if lesson.student else "Unknown"
            recurring_icon = "\U0001f501 " if lesson.recurring_pattern_id else ""
            lines.append(f"  {recurring_icon}{lesson.time.strftime('%H:%M')} - {student_name}")

    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to Main", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text("\n".join(lines), reply_markup=reply_markup)
