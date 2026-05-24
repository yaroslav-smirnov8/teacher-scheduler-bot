"""Student feedback and teacher feedback view handlers"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Teacher, Student, StudentFeedback
from services.feedback_service import FeedbackService
from bot.filters import IsTeacher, IsStudent
from bot.utils.helpers import get_teacher, get_student, sanitize_input, safe_parse_callback_int

logger = logging.getLogger(__name__)

router = Router()
teacher_router = Router()
student_router = Router()
router.include_router(student_router)
router.include_router(teacher_router)

teacher_router.callback_query.filter(IsTeacher())
student_router.callback_query.filter(IsStudent())
student_router.message.filter(IsStudent())


# ============================================================
# Student Feedback Submission
# ============================================================

# We reuse FEEDBACK_TEXT from original
FEEDBACK_TEXT = "FEEDBACK_TEXT_STATE"


@student_router.callback_query(F.data == 'feedback_start')
@student_router.message(Command('feedback'))
async def feedback_start(update: Message | CallbackQuery, state: FSMContext, session: AsyncSession):
    """Start student feedback flow"""
    if isinstance(update, CallbackQuery):
        await update.answer()
        chat_id = update.from_user.id
    else:
        chat_id = update.from_user.id

    student = await get_student(session, chat_id)
    if not student:
        msg = "You are not registered as a student."
        if isinstance(update, CallbackQuery):
            await update.message.edit_text(msg)
        else:
            await update.answer(msg)
        return

    msg = "⏳ Please enter your feedback or suggestion:\n\nUse /cancel to exit this conversation."
    if isinstance(update, CallbackQuery):
        await update.message.edit_text(msg)
    else:
        await update.answer(msg)

    await state.set_state(FEEDBACK_TEXT)


@student_router.message(F.text, StateFilter(FEEDBACK_TEXT))
async def feedback_text_handler(message: Message, state: FSMContext, session: AsyncSession):
    """Handle feedback text entry"""
    text = message.text
    if not text or len(text.strip()) < 5:
        await message.answer("⏳ Invalid feedback: minimum 5 characters.\n\nPlease enter your feedback:\n\nUse /cancel to exit this conversation.")
        return
    if len(text) > 1000:
        await message.answer("⏳ Invalid feedback: maximum 1000 characters.\n\nPlease enter your feedback:\n\nUse /cancel to exit this conversation.")
        return

    feedback_text = sanitize_input(text)
    chat_id = message.from_user.id

    student = await get_student(session, chat_id)
    if not student:
        await message.answer("You are not registered as a student.")
        await state.clear()
        return

    success, msg, feedback = await FeedbackService.create_feedback(
        session, student.id, student.name, feedback_text
    )
    if not success:
        await message.answer(f"Error: {msg}")
        await state.clear()
        return

    # Notify teacher
    result = await session.execute(select(Teacher).filter_by(id=student.teacher_id))
    teacher = result.scalar_one_or_none()
    if teacher and teacher.telegram_id:
        try:
            await message.bot.send_message(
                chat_id=teacher.telegram_id,
                text=f"📬 New feedback from {student.name}:\n\n{feedback_text}"
            )
        except Exception as e:
            logger.error(f"Error sending feedback notification: {e}")

    await state.clear()
    await message.answer("✅ Thank you for your feedback! It has been sent to your teacher.")


# ============================================================
# Teacher View Feedback
# ============================================================

@teacher_router.callback_query(F.data == 'view_feedback_start')
async def view_feedback_start(query: CallbackQuery, session: AsyncSession):
    """Show list of students who have sent feedback (teacher's students only)"""
    await query.answer()
    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    grouped_feedback = await FeedbackService.get_all_feedback(session, teacher.id)
    if not grouped_feedback:
        await query.message.edit_text("📭 No feedback received yet.")
        return

    keyboard = []
    for student_id, feedback_list in grouped_feedback.items():
        student_name = feedback_list[0].student_name
        unread_count = sum(1 for f in feedback_list if not f.is_read)
        indicator = "🔴" if unread_count > 0 else "✅"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{indicator} {student_name} ({len(feedback_list)} messages)",
                callback_data=f"VIEW-FEEDBACK-STUDENT-{student_id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data='back_to_main')])
    await query.message.edit_text(
        "📩 Feedback from students:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@teacher_router.callback_query(F.data.startswith('VIEW-FEEDBACK-STUDENT-'))
async def view_feedback_student(query: CallbackQuery, session: AsyncSession):
    """Show feedback items for selected student (teacher's students only)"""
    await query.answer()
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    # Verify student belongs to this teacher
    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    if not student or student.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only view feedback from your own students.")
        return

    feedback_list = await FeedbackService.get_feedback_by_student(session, student_id)
    if not feedback_list:
        await query.message.edit_text("📭 No feedback found for this student.")
        return

    keyboard = []
    for fb in feedback_list:
        date_str = fb.created_at.strftime('%Y-%m-%d %H:%M')
        indicator = "🔴" if not fb.is_read else "✅"
        keyboard.append([
            InlineKeyboardButton(
                text=f"{indicator} {date_str}",
                callback_data=f"VIEW-FEEDBACK-ITEM-{fb.id}"
            )
        ])
    keyboard.append([InlineKeyboardButton(text="⬅️ Back", callback_data='view_feedback_start')])

    student_name = feedback_list[0].student_name
    await query.message.edit_text(
        f"📩 Feedback from {student_name}:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


@teacher_router.callback_query(F.data.startswith('VIEW-FEEDBACK-ITEM-'))
async def view_feedback_item(query: CallbackQuery, session: AsyncSession):
    """Show full feedback message"""
    await query.answer()
    feedback_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if feedback_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    feedback = await FeedbackService.get_feedback_by_id(session, feedback_id)
    if not feedback:
        await query.message.edit_text("⚠️ Feedback not found.")
        return

    # Verify feedback belongs to this teacher's student
    from sqlalchemy import select
    from models import Student as StudentModel
    fb_student = await session.get(StudentModel, feedback.student_id)
    if not fb_student or fb_student.teacher_id != teacher.id:
        await query.message.edit_text("⚠️ Feedback not found.")
        return

    # Mark as read
    await FeedbackService.mark_as_read(session, feedback_id)

    date_str = feedback.created_at.strftime('%Y-%m-%d %H:%M')
    text = f"📩 From: {feedback.student_name}\n📅 {date_str}\n\n{feedback.message_text}"

    keyboard = [
        [InlineKeyboardButton(text="⬅️ Back", callback_data=f"VIEW-FEEDBACK-STUDENT-{feedback.student_id}")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == 'feedback_cancel')
async def feedback_cancel(query: CallbackQuery, state: FSMContext):
    """Cancel feedback submission"""
    await query.answer()
    await state.clear()
    await query.message.edit_text('❌ Feedback submission cancelled.')