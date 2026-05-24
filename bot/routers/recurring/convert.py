"""Convert to recurring router"""
import logging
from datetime import date
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from handlers.recurring import (
    convert_to_recurring_start, convert_select_frequency, convert_select_end_date,
    convert_confirm, _show_convert_end_date,
    CONVERT_SELECT_FREQUENCY, CONVERT_SELECT_END_DATE, CONVERT_CONFIRM,
    CONV_BACK_FREQ, CONV_BACK_END_DATE, CONV_BACK_LESSON,
)
from models import Teacher, Lesson

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data.startswith('CONVERT-RECUR-'))
async def handle_convert_to_recurring(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        return
    await convert_to_recurring_start(query, state, session)


@router.callback_query(F.data.startswith('CONV-FREQ-'))
async def handle_convert_select_frequency(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return
    await convert_select_frequency(query, state, session)


@router.callback_query(F.data.startswith('CONV-END-'))
async def handle_convert_select_end_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return
    await convert_select_end_date(query, state, session)


@router.callback_query(F.data.startswith('CONV-CONFIRM-'))
async def handle_convert_confirm(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return
    await convert_confirm(query, state, session)


@router.callback_query(F.data == CONV_BACK_FREQ)
async def handle_conv_back_freq(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to frequency selection in convert flow"""
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return
    await convert_to_recurring_start(query, state, session)


@router.callback_query(F.data == CONV_BACK_END_DATE)
async def handle_conv_back_end_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to end date selection in convert flow"""
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("This feature is only available for teachers.")
        await state.clear()
        return
    await _show_convert_end_date(query, state)


@router.callback_query(F.data == CONV_BACK_LESSON)
async def handle_conv_back_lesson(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to lesson day view from convert flow"""
    await query.answer()
    data = await state.get_data()
    lesson_id = data.get('convert_lesson_id')
    await state.clear()

    if not lesson_id:
        await query.message.edit_text("Session expired. Please start over.")
        return

    result = await session.execute(select(Lesson).filter_by(id=lesson_id))
    lesson = result.scalar_one_or_none()
    if not lesson:
        await query.message.edit_text("Lesson not found.")
        return

    year, month, day = lesson.date.year, lesson.date.month, lesson.date.day
    selected_date = lesson.date

    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("You are not registered as a teacher.")
        return

    result = await session.execute(
        select(Lesson).options(selectinload(Lesson.student)).filter(
            Lesson.teacher_id == teacher.id,
            Lesson.date == selected_date
        )
    )
    lessons = result.scalars().all()

    if not lessons:
        keyboard = [
            [InlineKeyboardButton(text="Schedule Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")]
        ]
        await query.message.edit_text(
            f"No lessons scheduled for {day}-{month}-{year}.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        schedule_lines = []
        for i, l in enumerate(lessons):
            prefix = '\U0001f501 ' if l.recurring_pattern_id else ''
            student_name = l.student.name if l.student else 'Unknown'
            schedule_lines.append(f"{i+1}. {prefix}{l.time.strftime('%H:%M')} - {student_name}")
        schedule_text = "\n".join(schedule_lines)

        keyboard = [
            [InlineKeyboardButton(text="Add Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")]
        ]
        for i, l in enumerate(lessons):
            keyboard.append([
                InlineKeyboardButton(text=f"\u2716\ufe0f Cancel Lesson {i+1}", callback_data=f"SMART-DEL-LESSON-{l.id}")
            ])
            if l.recurring_pattern_id is None:
                keyboard.append([
                    InlineKeyboardButton(text=f"\U0001f501 Make Recurring {i+1}", callback_data=f"CONVERT-RECUR-{l.id}")
                ])
        keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")])

        await query.message.edit_text(
            f"Schedule for {day}-{month}-{year}:\n{schedule_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
