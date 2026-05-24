"""Student registration FSM"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Teacher, Student
from bot.utils.helpers import sanitize_input
from bot.routers.reg_helpers import validate_text

logger = logging.getLogger(__name__)
router = Router()


class RegisterStudent(StatesGroup):
    teacher_login = State()


@router.message(Command('register_student'))
async def reg_student_start(message: Message, state: FSMContext, session: AsyncSession):
    """Start student registration"""
    result = await session.execute(select(Student).filter_by(telegram_id=message.from_user.id))
    if result.scalar_one_or_none():
        await message.answer("You are already registered as a student.")
        return

    await message.answer(
        '⏳ Please enter the teacher login:\n\n'
        'Use /cancel to exit this conversation.'
    )
    await state.set_state(RegisterStudent.teacher_login)


@router.message(RegisterStudent.teacher_login, F.text)
async def reg_student_login(message: Message, state: FSMContext, session: AsyncSession):
    """Handle teacher login and register student"""
    text = message.text
    is_valid, error_msg = validate_text(text, min_length=3, max_length=50)
    if not is_valid:
        await message.answer(f"⏳ Invalid login: {error_msg}\n\nPlease enter the teacher login:\n\nUse /cancel to exit this conversation.")
        return

    teacher_login = sanitize_input(text)
    chat_id = message.from_user.id

    result = await session.execute(select(Student).filter_by(telegram_id=chat_id))
    if result.scalar_one_or_none():
        await message.answer("You are already registered as a student.")
        await state.clear()
        return

    result = await session.execute(select(Teacher).filter_by(login=teacher_login))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await message.answer("⏳ Teacher with this login not found.\n\nPlease enter the teacher login:\n\nUse /cancel to exit this conversation.")
        return

    username = message.from_user.username or f"Student_{chat_id}"
    username = sanitize_input(username)
    new_student = Student(
        name=username,
        telegram_id=chat_id,
        teacher=teacher
    )
    session.add(new_student)
    await session.commit()

    await state.clear()
    await message.answer(f"You have successfully registered as a student. Your teacher: {teacher.name}")
