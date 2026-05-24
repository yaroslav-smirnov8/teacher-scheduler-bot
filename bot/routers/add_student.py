"""Add student (by teacher) FSM"""
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


class AddStudent(StatesGroup):
    name = State()
    contact = State()


@router.message(Command('add_student'))
async def add_student_start(message: Message, state: FSMContext, session: AsyncSession):
    """Start add student flow by teacher"""
    result = await session.execute(select(Teacher).filter_by(telegram_id=message.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await message.answer("You are not registered as a teacher.")
        return

    await message.answer(
        '⏳ Enter student name:\n\n'
        'Use /cancel to exit this conversation.'
    )
    await state.set_state(AddStudent.name)


@router.message(AddStudent.name, F.text)
async def add_student_name(message: Message, state: FSMContext, session: AsyncSession):
    """Handle student name input"""
    text = message.text
    is_valid, error_msg = validate_text(text, min_length=2, max_length=100)
    if not is_valid:
        await message.answer(f"⏳ Invalid name: {error_msg}\n\nEnter student name:\n\nUse /cancel to exit this conversation.")
        return

    await state.update_data(student_name=sanitize_input(text))
    await message.answer(
        '⏳ Enter student contact information:\n\n'
        'Use /cancel to exit this conversation.'
    )
    await state.set_state(AddStudent.contact)


@router.message(AddStudent.contact, F.text)
async def add_student_contact(message: Message, state: FSMContext, session: AsyncSession):
    """Handle student contact and save"""
    text = message.text
    is_valid, error_msg = validate_text(text, min_length=1, max_length=200)
    if not is_valid:
        await message.answer(f"⏳ Invalid contact: {error_msg}\n\nEnter student contact information:\n\nUse /cancel to exit this conversation.")
        return

    contact = sanitize_input(text)
    data = await state.get_data()

    result = await session.execute(select(Teacher).filter_by(telegram_id=message.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await message.answer("You are not registered as a teacher.")
        await state.clear()
        return

    student_name = data.get('student_name', 'Unknown')
    new_student = Student(
        name=student_name,
        contact_info=contact,
        teacher=teacher
    )
    session.add(new_student)
    await session.commit()

    await state.clear()
    await message.answer(f"Student {student_name} successfully added.")
