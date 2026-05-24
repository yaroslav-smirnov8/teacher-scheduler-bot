"""Router for AI homework flow - callbacks and message handlers"""
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.ai_homework import (
    AIHomeworkStates,
    ai_hw_start,
    ai_hw_select_mode,
    ai_hw_select_student,
    ai_hw_enter_topic,
    ai_hw_select_level,
    ai_hw_select_focus,
    ai_hw_on_count_selected,
    ai_hw_provide_context,
    ai_hw_paste_json,
    ai_hw_generate_callback,
    ai_hw_approve,
    ai_hw_regenerate,
    ai_hw_edit,
    ai_hw_edit_text,
    ai_hw_cancel,
    ai_hw_confirm_send,
    ai_hw_back,
    StudentExerciseStates,
    ex_start,
    ex_option,
    ex_toggle,
    ex_confirm,
    ex_text_answer,
    ex_next,
    ex_restart,
    ex_end,
    ai_hw_stats,
    ai_hw_stats_hw,
    ai_hw_stats_attempt,
)
from bot.filters import IsTeacher, IsStudent

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


# ── Entry ─────────────────────────────────────────────────────────


@teacher_router.callback_query(F.data == "ai_hw_start")
async def ai_hw_entry(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_start(query, state, session)


# ── Mode selection ────────────────────────────────────────────────


@teacher_router.callback_query(F.data.startswith("ai_hw_mode_"))
async def ai_hw_mode_selected(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_select_mode(query, state, session)


# ── Student selection ────────────────────────────────────────────


@teacher_router.callback_query(F.data.startswith("ai_hw_student_"))
async def ai_hw_student_selected(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_select_student(query, state, session)


# ── Level selection ──────────────────────────────────────────────


@teacher_router.callback_query(F.data.startswith("ai_hw_level_"))
async def ai_hw_level_selected(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_select_level(query, state, session)


# ── Focus selection ──────────────────────────────────────────────


@teacher_router.callback_query(F.data.startswith("ai_hw_focus_"))
async def ai_hw_focus_selected(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_select_focus(query, state, session)


# ── Preview actions ──────────────────────────────────────────────


@teacher_router.callback_query(F.data == "ai_hw_approve")
async def ai_hw_approve_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_approve(query, state, session)


@teacher_router.callback_query(F.data == "ai_hw_confirm_send")
async def ai_hw_confirm_send_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_confirm_send(query, state, session)


@teacher_router.callback_query(F.data == "ai_hw_regenerate")
async def ai_hw_regenerate_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_regenerate(query, state, session)


@teacher_router.callback_query(F.data == "ai_hw_edit")
async def ai_hw_edit_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_edit(query, state, session)


# ── Navigation ────────────────────────────────────────────────────


@teacher_router.callback_query(F.data == "ai_hw_cancel")
async def ai_hw_cancel_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_cancel(query, state, session)


@teacher_router.callback_query(F.data == "ai_hw_back")
async def ai_hw_back_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_back(query, state, session)


# ── Message handlers (text input) ────────────────────────────────


@teacher_router.message(AIHomeworkStates.ENTER_TOPIC)
async def ai_hw_topic_received(message: Message, state: FSMContext, session: AsyncSession):
    await ai_hw_enter_topic(message, state, session)


@teacher_router.message(AIHomeworkStates.PROVIDE_CONTEXT)
async def ai_hw_context_received(message: Message, state: FSMContext, session: AsyncSession):
    await ai_hw_provide_context(message, state, session)


@teacher_router.callback_query(AIHomeworkStates.ENTER_COUNT, F.data.startswith("ai_hw_count_"))
async def ai_hw_count_selected(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_on_count_selected(query, state, session)


@teacher_router.message(AIHomeworkStates.WAITING_JSON)
async def ai_hw_json_received(message: Message, state: FSMContext, session: AsyncSession):
    await ai_hw_paste_json(message, state, session)


@teacher_router.message(AIHomeworkStates.EDIT_TEXT)
async def ai_hw_edit_received(message: Message, state: FSMContext, session: AsyncSession):
    await ai_hw_edit_text(message, state, session)


# ═══════════════════════════════════════════════════════════════════
# STUDENT INTERACTIVE EXERCISE ROUTES
# ═══════════════════════════════════════════════════════════════════


@student_router.callback_query(F.data.startswith("ex_start_"))
async def ex_start_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_start(query, state, session)


@student_router.callback_query(F.data.startswith("ex_op_"))
async def ex_option_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_option(query, state, session)


@student_router.callback_query(F.data.startswith("ex_tg_"))
async def ex_toggle_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_toggle(query, state, session)


@student_router.callback_query(F.data == "ex_cf")
async def ex_confirm_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_confirm(query, state, session)


@student_router.callback_query(F.data == "ex_nx")
async def ex_next_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_next(query, state, session)


@student_router.callback_query(F.data == "ex_rs")
async def ex_restart_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_restart(query, state, session)


@student_router.callback_query(F.data == "ex_en")
async def ex_end_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ex_end(query, state, session)


@student_router.message(StudentExerciseStates.EXERCISE)
async def ex_text_received(message: Message, state: FSMContext, session: AsyncSession):
    await ex_text_answer(message, state, session)


# ═══════════════════════════════════════════════════════════════════
# TEACHER STATISTICS ROUTES
# ═══════════════════════════════════════════════════════════════════


@teacher_router.callback_query(F.data == "ai_hw_stats")
async def ai_hw_stats_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_stats(query, state, session)


@teacher_router.callback_query(F.data.startswith("ai_hw_stats_hw_"))
async def ai_hw_stats_hw_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_stats_hw(query, state, session)


@teacher_router.callback_query(F.data.startswith("ai_hw_stats_attempt_"))
async def ai_hw_stats_attempt_action(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    await ai_hw_stats_attempt(query, state, session)
