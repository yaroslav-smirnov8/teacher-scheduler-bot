"""Teacher approve/decline reschedule request handlers"""
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Teacher, Student, Lesson, RescheduleRequest
from services.reschedule_service import RescheduleService
from services.notification_service import NotificationService
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith('APPROVE-RESCH-'))
async def approve_reschedule_request(query: CallbackQuery, session: AsyncSession):
    await query.answer()
    request_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if request_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("Only teachers can approve reschedule requests.")
        return

    result = await session.execute(select(RescheduleRequest).filter_by(id=request_id))
    req = result.scalar_one_or_none()
    if not req or req.teacher_id != teacher.id:
        await query.message.edit_text("You can only approve requests for your own lessons.")
        return

    success, message, lesson = await RescheduleService.approve_reschedule(session, request_id)
    if not success:
        await query.message.edit_text(f"Error: {message}")
        return

    if req and lesson:
        result = await session.execute(select(Student).filter_by(id=req.student_id))
        student = result.scalar_one_or_none()
        if student and teacher:
            await NotificationService.notify_student_reschedule_result(
                query.bot, student, teacher,
                lesson.date, lesson.time, accepted=True
            )
    await query.message.edit_text(f"Reschedule approved. Lesson moved to {lesson.date} {lesson.time.strftime('%H:%M')}.")


@router.callback_query(F.data.startswith('DECLINE-RESCH-'))
async def decline_reschedule_request(query: CallbackQuery, session: AsyncSession):
    await query.answer()
    request_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if request_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("Only teachers can decline reschedule requests.")
        return

    result = await session.execute(select(RescheduleRequest).filter_by(id=request_id))
    req = result.scalar_one_or_none()
    if not req or req.teacher_id != teacher.id:
        await query.message.edit_text("You can only decline requests for your own lessons.")
        return

    success, message = await RescheduleService.decline_reschedule(session, request_id)
    if not success:
        await query.message.edit_text(f"Error: {message}")
        return

    if req:
        result = await session.execute(select(Student).filter_by(id=req.student_id))
        student = result.scalar_one_or_none()
        if student and teacher:
            result = await session.execute(select(Lesson).filter_by(id=req.lesson_id))
            lesson = result.scalar_one_or_none()
            if lesson:
                await NotificationService.notify_student_reschedule_result(
                    query.bot, student, teacher,
                    lesson.date, lesson.time, accepted=False
                )
    await query.message.edit_text("Reschedule request declined. Original lesson time remains unchanged.")
