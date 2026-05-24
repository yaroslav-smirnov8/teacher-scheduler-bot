"""Common handlers: /start, main menu, cancel, error handling"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, ErrorEvent
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from bot.keyboards.main_menu import build_main_menu, build_back_button
from bot.utils.helpers import get_teacher, get_student

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message, session: AsyncSession):
    """Handle /start command"""
    keyboard = await build_main_menu(message.from_user.id, session)
    await message.answer("<b>Welcome!</b> I'm your educational assistant bot.", reply_markup=keyboard)


@router.callback_query(F.data == 'back_to_main')
async def back_to_main(query: CallbackQuery, session: AsyncSession):
    """Return to main menu"""
    await query.answer()
    keyboard = await build_main_menu(query.from_user.id, session)
    await query.message.edit_text("<b>Welcome!</b> I'm your educational assistant bot.", reply_markup=keyboard)


@router.callback_query(F.data == 'register_teacher')
async def register_teacher_prompt(query: CallbackQuery, session: AsyncSession):
    """Prompt to use /register_teacher command"""
    await query.answer()
    teacher = await get_teacher(session, query.from_user.id)
    if teacher:
        await query.message.edit_text("✅ You are already registered as a teacher.")
    else:
        await query.message.edit_text(
            "👨‍🏫 To register as a teacher, please use the command:\n\n"
            "<code>/register_teacher</code>\n\n"
            "You will be asked for your name, contact info, and a login."
        )


@router.callback_query(F.data == 'register_student')
async def register_student_prompt(query: CallbackQuery, session: AsyncSession):
    """Prompt to use /register_student command"""
    await query.answer()
    student = await get_student(session, query.from_user.id)
    if student:
        await query.message.edit_text("✅ You are already registered as a student.")
    else:
        await query.message.edit_text(
            "🎓 To register as a student, please use the command:\n\n"
            "<code>/register_student</code>\n\n"
            "You will need your teacher's login code."
        )


@router.callback_query(F.data == 'CANCEL-CONV')
async def cancel_generic(query: CallbackQuery, state: FSMContext):
    """Generic cancel handler for inline cancel buttons"""
    await query.answer()
    await state.clear()
    await query.message.edit_text("❌ Process cancelled.")


@router.message(Command('cancel'))
async def cancel_command(message: Message, state: FSMContext):
    """Handle /cancel command"""
    await state.clear()
    await message.answer("❌ Process cancelled.")


@router.errors()
async def error_handler(event: ErrorEvent):
    """Global error handler"""
    logger.error(f"Error occurred: {event.exception}", exc_info=event.exception)
    # Try to notify user — never expose internal error details
    if event.update and event.update.callback_query:
        try:
            await event.update.callback_query.answer(
                "⚠️ An error occurred. Please try again later.",
                show_alert=True
            )
        except Exception:
            pass
    elif event.update and event.update.message:
        try:
            await event.update.message.answer("⚠️ An error occurred. Please try again later.")
        except Exception:
            pass