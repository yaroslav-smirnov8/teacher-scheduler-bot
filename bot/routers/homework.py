"""Homework handlers – teacher send + student view"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.homework import (
    TeacherHomeworkStates,
    teacher_homework_menu, teacher_select_lesson, teacher_edit_homework_text,
    teacher_confirm_homework, teacher_view_homework_history,
    teacher_view_homework_detail, teacher_mark_homework, teacher_toggle_optional,
    teacher_homework_stats, teacher_student_homework_stats,
    student_homework_menu, student_view_homework_detail,
    student_mark_homework_received, student_mark_homework_completed, cancel_handler, back_handler
)
from bot.filters import IsTeacher, IsStudent
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)

router = Router()
teacher_router = Router()
student_router = Router()
router.include_router(teacher_router)
router.include_router(student_router)

teacher_router.callback_query.filter(IsTeacher())
teacher_router.message.filter(IsTeacher())
student_router.callback_query.filter(IsStudent())
student_router.message.filter(IsStudent())


@teacher_router.callback_query(F.data == 'teacher_homework_start')
async def teacher_homework_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await teacher_homework_menu(query, state, session)


@student_router.callback_query(F.data == 'student_homework_start')
async def student_homework_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await student_homework_menu(query, state, session)


@teacher_router.callback_query(F.data.startswith('hw_post_lesson_'))
async def hw_post_lesson_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    lesson_id = safe_parse_callback_int(query.data, delimiter='_', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    await state.update_data(lesson_id=lesson_id, hw_type='post_lesson')
    await teacher_homework_menu(query, state, session)


@teacher_router.callback_query(F.data == 'hw_stats')
async def hw_stats_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await teacher_homework_stats(query, state, session)


@teacher_router.callback_query(F.data.startswith('hw_detail_'))
async def hw_detail_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await teacher_view_homework_detail(query, state, session)


@teacher_router.callback_query(F.data.startswith('hw_mark_'))
async def hw_mark_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await teacher_mark_homework(query, state, session)


@teacher_router.callback_query(F.data.startswith('hw_toggle_opt_'))
async def hw_toggle_opt_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await teacher_toggle_optional(query, state, session)


@teacher_router.callback_query(F.data.startswith('hw_student_stats_'))
async def hw_student_stats_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await teacher_student_homework_stats(query, state, session)


# Handle homework text input from teacher
@teacher_router.message(TeacherHomeworkStates.EDIT_TEXT)
async def teacher_confirm_homework_handler(message: Message, state: FSMContext, session: AsyncSession):
    await teacher_confirm_homework(message, state, session)


# Relay all remaining homework-related callbacks (teacher)
@teacher_router.callback_query(F.data.startswith('hw_'))
async def homework_callback_relay(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    data = query.data

    if data == 'hw_back':
        await back_handler(query, state, session)
    elif data.startswith('hw_history'):
        page = 0
        if data != 'hw_history':
            parts = data.split('_p')
            if len(parts) == 2 and parts[1].isdigit():
                page = int(parts[1]) - 1  # callback data is 1-indexed
        await teacher_view_homework_history(query, state, session, page=page)
    elif data in ('hw_post_lesson', 'hw_independent'):
        await teacher_select_lesson(query, state, session)
    elif data.startswith('hw_lesson_') or data.startswith('hw_student_'):
        await teacher_edit_homework_text(query, state, session)


@student_router.callback_query(F.data.startswith('view_hw_'))
async def homework_view_relay(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await student_view_homework_detail(query, state, session)


@student_router.callback_query(F.data.startswith('mark_received_'))
async def homework_mark_received_relay(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await student_mark_homework_received(query, state, session)


@student_router.callback_query(F.data.startswith('mark_completed_'))
async def homework_mark_completed_relay(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await student_mark_homework_completed(query, state, session)