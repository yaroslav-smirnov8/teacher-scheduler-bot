"""Main menu keyboard builder"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Teacher, Student


async def build_main_menu(telegram_id: int, session: AsyncSession) -> InlineKeyboardMarkup:
    """Build main menu with role-specific buttons"""
    keyboard = [
        [InlineKeyboardButton(text="📅 Calendar", callback_data='calendar')],
        [InlineKeyboardButton(text="🗓 My Schedule", callback_data='my_schedule')],
    ]

    result = await session.execute(select(Teacher).filter_by(telegram_id=telegram_id))
    teacher = result.scalar_one_or_none()
    if teacher:
        keyboard.append([InlineKeyboardButton(text="👥 My Students", callback_data='list_students')])
        keyboard.append([InlineKeyboardButton(text="🔁 Recurring Lessons", callback_data='recurring_menu')])
        keyboard.append([InlineKeyboardButton(text="💳 Payments", callback_data='pay_menu')])
        keyboard.append([InlineKeyboardButton(text="📝 Send Homework", callback_data='teacher_homework_start')])
        keyboard.append([InlineKeyboardButton(text="🤖 AI Homework", callback_data='ai_hw_start')])
        keyboard.append([InlineKeyboardButton(text="📊 Homework Stats", callback_data='ai_hw_stats')])
        keyboard.append([InlineKeyboardButton(text="📩 View Feedback", callback_data='view_feedback_start')])
    else:
        result = await session.execute(select(Student).filter_by(telegram_id=telegram_id))
        student = result.scalar_one_or_none()
        if student:
            keyboard.append([InlineKeyboardButton(text="📚 My Homework", callback_data='student_homework_start')])
            keyboard.append([InlineKeyboardButton(text="💬 Feedback", callback_data='feedback_start')])
            keyboard.append([InlineKeyboardButton(text="💰 Balance", callback_data='my_balance')])
        else:
            keyboard.append([InlineKeyboardButton(text="👨‍🏫 Register as Teacher", callback_data='register_teacher')])
            keyboard.append([InlineKeyboardButton(text="🎓 Register as Student", callback_data='register_student')])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def build_back_button(callback_data: str = 'back_to_main') -> InlineKeyboardMarkup:
    """Simple back button"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Back", callback_data=callback_data)]]
    )


def build_cancel_button() -> InlineKeyboardMarkup:
    """Cancel button for flows"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="❌ Cancel", callback_data="CANCEL-CONV")]]
    )