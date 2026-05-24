"""Teacher registration FSM"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Teacher
from bot.utils.helpers import sanitize_input
from bot.routers.reg_helpers import validate_text

logger = logging.getLogger(__name__)
router = Router()


class RegisterTeacher(StatesGroup):
    name = State()
    contact = State()
    login = State()


@router.message(Command('register_teacher'))
async def reg_teacher_start(message: Message, state: FSMContext, session: AsyncSession):
    """Start teacher registration"""
    result = await session.execute(select(Teacher))
    teachers = result.scalars().all()
    if len(teachers) >= 1:
        await message.answer("Maximum 1 teacher allowed in this system.")
        return

    await message.answer(
        '⏳ Please enter your name:\n\n'
        'Use /cancel to exit this conversation.'
    )
    await state.set_state(RegisterTeacher.name)


@router.message(RegisterTeacher.name, F.text)
async def reg_teacher_name(message: Message, state: FSMContext, session: AsyncSession):
    """Handle teacher name input"""
    text = message.text
    is_valid, error_msg = validate_text(text, min_length=2, max_length=100)
    if not is_valid:
        await message.answer(f"⏳ Invalid name: {error_msg}\n\nPlease enter your name (2-100 characters):\n\nUse /cancel to exit this conversation.")
        return

    await state.update_data(name=sanitize_input(text))
    await message.answer(
        '⏳ Enter your contact information:\n\n'
        'Use /cancel to exit this conversation.'
    )
    await state.set_state(RegisterTeacher.contact)


@router.message(RegisterTeacher.contact, F.text)
async def reg_teacher_contact(message: Message, state: FSMContext, session: AsyncSession):
    """Handle teacher contact input"""
    text = message.text
    is_valid, error_msg = validate_text(text, min_length=1, max_length=200)
    if not is_valid:
        await message.answer(f"⏳ Invalid contact: {error_msg}\n\nEnter your contact information:\n\nUse /cancel to exit this conversation.")
        return

    await state.update_data(contact=sanitize_input(text))
    await message.answer(
        '⏳ Create a login:\n\n'
        'Use /cancel to exit this conversation.'
    )
    await state.set_state(RegisterTeacher.login)


@router.message(RegisterTeacher.login, F.text)
async def reg_teacher_login(message: Message, state: FSMContext, session: AsyncSession):
    """Handle teacher login input and save"""
    text = message.text
    is_valid, error_msg = validate_text(text, min_length=3, max_length=50)
    if not is_valid:
        await message.answer(f"⏳ Invalid login: {error_msg}\n\nCreate a login (3-50 characters):\n\nUse /cancel to exit this conversation.")
        return

    login = sanitize_input(text)
    data = await state.get_data()

    result = await session.execute(select(Teacher).filter_by(login=login))
    if result.scalar_one_or_none():
        await message.answer("⏳ This login is already in use. Please choose another one.\n\nUse /cancel to exit this conversation.")
        return

    result = await session.execute(select(Teacher))
    teachers = result.scalars().all()
    if len(teachers) >= 1:
        await message.answer("Maximum 1 teacher allowed in this system.")
        await state.clear()
        return

    new_teacher = Teacher(
        name=data.get('name', ''),
        contact_info=data.get('contact', ''),
        login=login,
        telegram_id=message.from_user.id
    )
    session.add(new_teacher)
    await session.commit()

    await state.clear()
    await message.answer(f"You have successfully registered as a teacher. Your login: {login}")
