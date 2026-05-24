"""Smart delete handlers - single instance vs entire series"""
import logging
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from models import Teacher, Student, Lesson, RecurringPattern
from services.recurring_service import RecurringLessonService
from services.notification_service import NotificationService
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)


async def smart_delete_lesson(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show delete options for a lesson"""
    lesson_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    result = await session.execute(select(Lesson).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()

    if not lesson:
        await query.message.edit_text("⚠️ Lesson not found.")
        return

    teacher_result = await session.execute(
        select(Teacher).filter_by(telegram_id=query.from_user.id)
    )
    teacher = teacher_result.scalar_one_or_none()
    if not teacher or lesson.teacher_id != teacher.id:
        await query.message.edit_text("🔒 🔒 You can only delete your own lessons.")
        return

    if lesson.recurring_pattern_id is not None:
        keyboard = [
            [InlineKeyboardButton(text="📌 Delete this instance only", callback_data=f"SMART-DEL-ONCE-{lesson.id}")],
            [InlineKeyboardButton(text="🗑 Delete entire series", callback_data=f"SMART-DEL-SERIES-{lesson.recurring_pattern_id}")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            f"📌 This lesson is part of a recurring series.\n\n{lesson.date} {lesson.time.strftime('%H:%M')}\n\nHow would you like to delete?",
            reply_markup=reply_markup
        )
    else:
        keyboard = [
            [InlineKeyboardButton(text="✅ Yes, cancel", callback_data=f"CANCEL-LESSON-{lesson.id}")],
            [InlineKeyboardButton(text="⬅️ Back", callback_data="list_students")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            f"❓ Cancel lesson?\n\n{lesson.date} {lesson.time.strftime('%H:%M')}",
            reply_markup=reply_markup
        )


async def smart_delete_once(query: CallbackQuery, state: FSMContext, session) -> None:
    """Delete single instance of recurring lesson"""
    lesson_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    result = await session.execute(select(Lesson).options(selectinload(Lesson.student)).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()

    if not lesson:
        await query.message.edit_text("⚠️ Lesson not found.")
        return

    teacher_result = await session.execute(
        select(Teacher).filter_by(telegram_id=query.from_user.id)
    )
    teacher = teacher_result.scalar_one_or_none()
    if not teacher or lesson.teacher_id != teacher.id:
        await query.message.edit_text("🔒 🔒 You can only delete your own lessons.")
        return

    lesson_date = lesson.date
    success, message = await RecurringLessonService.delete_single_instance(
        session, lesson_id, lesson_date
    )

    if success:
        if lesson.student:
            await NotificationService.notify_student_lesson_cancelled(
                query.bot, lesson.student, teacher, lesson_date, lesson.time, is_single_instance=True
            )
        await query.message.edit_text("\u2705 Single lesson instance deleted.")
    else:
        await query.message.edit_text(f"\u274c {message}")


async def smart_delete_series(query: CallbackQuery, state: FSMContext, session) -> None:
    """Delete entire recurring series"""
    pattern_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if pattern_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    result = await session.execute(select(RecurringPattern).filter_by(id=pattern_id))
    pattern = result.scalar_one_or_none()

    if not pattern:
        await query.message.edit_text("⚠️ Pattern not found.")
        return

    teacher_result = await session.execute(
        select(Teacher).filter_by(telegram_id=query.from_user.id)
    )
    teacher = teacher_result.scalar_one_or_none()
    if not teacher or pattern.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only delete your own recurring lessons.")
        return

    success, message = await RecurringLessonService.delete_recurring_series(
        session, pattern_id
    )

    if success:
        result = await session.execute(select(Student).filter_by(id=pattern.student_id))
        student = result.scalar_one_or_none()
        if student:
            await NotificationService.notify_student_series_cancelled(
                query.bot, student, teacher, pattern
            )
        await query.message.edit_text("\u2705 Entire recurring series deleted.")
    else:
        await query.message.edit_text(f"\u274c {message}")
