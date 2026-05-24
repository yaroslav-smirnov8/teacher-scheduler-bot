"""Common recurring router - delete, schedule, cancel"""
import logging
from datetime import datetime, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from handlers.recurring import (
    smart_delete_lesson, smart_delete_once, smart_delete_series,
    view_recurring_schedule, cancel_recurring_conversation,
)
from models import Teacher, Student, Lesson

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith('SMART-DEL-LESSON-'))
async def handle_smart_delete_lesson(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        await state.clear()
        return
    await smart_delete_lesson(query, state, session)


@router.callback_query(F.data.startswith('SMART-DEL-ONCE-'))
async def handle_smart_delete_once(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        await state.clear()
        return
    await smart_delete_once(query, state, session)


@router.callback_query(F.data.startswith('SMART-DEL-SERIES-'))
async def handle_smart_delete_series(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        await state.clear()
        return
    await smart_delete_series(query, state, session)


@router.callback_query(F.data == 'view_schedule')
async def handle_view_schedule(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """View teacher schedule with recurring lessons (teacher only)"""
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        return
    await view_recurring_schedule(query, state, session)


@router.callback_query(F.data == 'my_schedule')
async def handle_my_schedule(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """View schedule for both teachers and students"""
    await query.answer()
    
    teacher_result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = teacher_result.scalar_one_or_none()
    
    if teacher:
        today = datetime.now(timezone.utc).date()
        result = await session.execute(
            select(Lesson).options(selectinload(Lesson.student)).filter(
                Lesson.teacher_id == teacher.id,
                Lesson.date >= today
            ).order_by(Lesson.date, Lesson.time)
        )
        lessons = result.scalars().all()
        if not lessons:
            await query.message.edit_text("📭 You have no scheduled lessons.")
        else:
            schedule_text = "<b>Your schedule:</b>\n" + "\n".join(
                [f"{lesson.date} {lesson.time.strftime('%H:%M')} - {lesson.student.name if lesson.student else 'Unknown'}" for lesson in lessons]
            )
            await query.message.edit_text(schedule_text)
        return

    student_result = await session.execute(select(Student).filter_by(telegram_id=query.from_user.id))
    student = student_result.scalar_one_or_none()
    
    if not student:
        await query.message.edit_text("⚠️ You are not registered as a teacher or student.")
        return
        
    today = datetime.now(timezone.utc).date()
    result = await session.execute(
        select(Lesson).options(selectinload(Lesson.teacher)).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time)
    )
    lessons = result.scalars().all()
    if not lessons:
        await query.message.edit_text("📭 You have no scheduled lessons.")
    else:
        schedule_text = "<b>Your schedule:</b>\n" + "\n".join(
            [f"{lesson.date} {lesson.time.strftime('%H:%M')} - {lesson.teacher.name}" for lesson in lessons]
        )
        await query.message.edit_text(schedule_text)


@router.callback_query(F.data.startswith('CANCEL-RECUR-'))
async def handle_cancel_recurring(query: CallbackQuery, state: FSMContext):
    await query.answer()
    await cancel_recurring_conversation(query, state)


@router.message(Command('cancel_recurring'))
async def handle_cancel_recurring_cmd(message: Message, state: FSMContext):
    await cancel_recurring_conversation(message, state)
