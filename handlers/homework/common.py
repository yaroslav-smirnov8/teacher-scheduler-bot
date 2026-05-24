"""Common homework handlers - cancel, back"""
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from handlers.homework.teacher import teacher_homework_menu, TeacherHomeworkStates


async def cancel_handler(update, state: FSMContext, **kwargs) -> None:
    """Cancel homework operation"""
    await state.clear()
    if hasattr(update, 'message') and update.message:
        await update.message.reply_text("Homework operation cancelled.")
    elif hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.message.edit_text("Homework operation cancelled.")


async def back_handler(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle back button - go back in homework flow"""
    current_state = await state.get_state()
    if current_state == TeacherHomeworkStates.SELECT_LESSON:
        await teacher_homework_menu(query, state, session)
    else:
        from bot.keyboards.main_menu import build_main_menu
        keyboard = await build_main_menu(query.from_user.id, session)
        await query.message.edit_text(
            "Welcome! I'm your educational bot.",
            reply_markup=keyboard
        )
        await state.clear()
