"""Payment note editing and cancel handlers"""
import logging
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select

from models import Teacher
from payment_service import PaymentService
from access_control import AccessControlService
from bot.utils.helpers import sanitize_input, safe_parse_callback_int

logger = logging.getLogger(__name__)


class PaymentNoteStates(StatesGroup):
    waiting_for_note = State()


async def payment_edit_note_start(query: CallbackQuery, state: FSMContext, session) -> None:
    """Start editing payment note"""
    lesson_id = safe_parse_callback_int(query.data, delimiter=':', position=-1)
    if lesson_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        return
    await state.update_data(payment_note_lesson_id=lesson_id)

    await query.message.edit_text(
        text="\u270f\ufe0f Enter payment note:\n\n"
        "(Send /cancel to abandon)"
    )

    await state.set_state(PaymentNoteStates.waiting_for_note)


async def payment_edit_note_save(message: Message, state: FSMContext, session) -> None:
    """Save payment note"""
    user_id = message.from_user.id
    note_text = message.text

    data = await state.get_data()
    lesson_id = data.get('payment_note_lesson_id')
    if not lesson_id:
        await message.answer("Error: Lesson ID not found")
        await state.clear()
        return

    if len(note_text) > 500:
        await message.answer("Note too long (max 500 characters)")
        return

    note_text = sanitize_input(note_text)

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()

    if not teacher:
        await message.answer("You are not registered as a teacher.")
        await state.clear()
        return

    is_authorized, error_msg = await AccessControlService.verify_teacher_owns_lesson(
        session, teacher.id, lesson_id
    )
    if not is_authorized:
        await message.answer(error_msg)
        await state.clear()
        return

    success, msg = await PaymentService.update_payment_note(session, lesson_id, note_text)

    if success:
        await message.answer("\u2705 Payment note updated")
    else:
        await message.answer(f"Error: {msg}")

    await state.clear()


async def payment_cancel(query: CallbackQuery, state: FSMContext, session) -> None:
    """Cancel payment note editing"""
    await state.clear()
    await query.message.edit_text("❌ Cancelled")
