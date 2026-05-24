"""Recurring lesson creation router"""
import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from handlers.recurring import (
    create_recurring_start, recurring_select_student, recurring_select_frequency,
    recurring_select_weekday, recurring_select_day_of_month, recurring_select_time,
    recurring_select_end_date, recurring_confirm,
    REC_BACK_STUDENT, REC_BACK_FREQUENCY, REC_BACK_WEEKDAY, REC_BACK_DAY,
    REC_BACK_TIME, REC_BACK_END_DATE,
    RECURRING_SELECT_STUDENT, RECURRING_SELECT_FREQUENCY, RECURRING_SELECT_WEEKDAY,
    RECURRING_SELECT_DAY_OF_MONTH, RECURRING_SELECT_TIME, RECURRING_SELECT_END_DATE,
    RECURRING_CONFIRM,
)
from models import Teacher, Student

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == 'recurring_menu')
async def show_recurring_menu(query: CallbackQuery, session: AsyncSession):
    """Show recurring lessons menu (teacher only)"""
    await query.answer()
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        return
    keyboard = [
        [InlineKeyboardButton(text="➕ Create Recurring Lesson", callback_data='create_recurring')],
        [InlineKeyboardButton(text="📋 View Schedule", callback_data='view_schedule')],
        [InlineKeyboardButton(text="⬅️ Back", callback_data='back_to_main')]
    ]
    await query.message.edit_text("🔁 Recurring Lessons:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


@router.callback_query(F.data == 'create_recurring')
@router.message(Command('create_recurring'))
async def create_recurring_entry(update: Message | CallbackQuery, state: FSMContext, session: AsyncSession):
    """Entry point for creating recurring lesson"""
    if isinstance(update, Message):
        await create_recurring_start(update, state, session)
    else:
        await update.answer()
        teacher = await session.execute(select(Teacher).filter_by(telegram_id=update.from_user.id))
        teacher = teacher.scalar_one_or_none()
        if not teacher:
            await update.message.edit_text("⚠️ You are not registered as a teacher.")
            return

        result = await session.execute(select(Student).filter_by(teacher_id=teacher.id))
        students = result.scalars().all()
        if not students:
            await update.message.edit_text("👥 You have no students.")
            return

        keyboard = [
            [InlineKeyboardButton(text=s.name, callback_data=f"REC-STUDENT-{s.id}")]
            for s in students
        ]
        keyboard.append([
            InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main"),
            InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
        ])
        await update.message.edit_text("<b>Select student:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        await state.set_state(RECURRING_SELECT_STUDENT)


async def _check_teacher(query: CallbackQuery, state: FSMContext, session: AsyncSession) -> bool:
    """Return True if user is a teacher, False otherwise."""
    result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.message.edit_text("🔒 This feature is only available for teachers.")
        await state.clear()
        return False
    return True


@router.callback_query(F.data.startswith('REC-STUDENT-'))
async def handle_recurring_select_student(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_student(query, state, session)


@router.callback_query(F.data.startswith('REC-FREQ-'))
async def handle_recurring_select_frequency(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_frequency(query, state, session)


@router.callback_query(F.data.startswith('REC-WEEKDAY-'))
async def handle_recurring_select_weekday(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_weekday(query, state, session)


@router.callback_query(F.data.startswith('REC-DAY-'))
async def handle_recurring_select_day_of_month(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_day_of_month(query, state, session)


@router.callback_query(F.data.startswith('REC-TIME-'))
async def handle_recurring_select_time(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_time(query, state, session)


@router.callback_query(F.data.startswith('REC-END-'))
async def handle_recurring_select_end_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_end_date(query, state, session)


@router.callback_query(F.data.startswith('REC-CONFIRM-'))
async def handle_recurring_confirm(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_confirm(query, state, session)


@router.callback_query(F.data == REC_BACK_STUDENT)
async def handle_rec_back_student(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to student selection"""
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await create_recurring_start(query, state, session)


@router.callback_query(F.data == REC_BACK_FREQUENCY)
async def handle_rec_back_frequency(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to frequency selection"""
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    keyboard = [
        [InlineKeyboardButton(text="Weekly", callback_data="REC-FREQ-weekly")],
        [InlineKeyboardButton(text="Biweekly", callback_data="REC-FREQ-biweekly")],
        [InlineKeyboardButton(text="Monthly", callback_data="REC-FREQ-monthly")],
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=REC_BACK_STUDENT),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text("<b>Select frequency:</b>", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_FREQUENCY)


@router.callback_query(F.data == REC_BACK_WEEKDAY)
async def handle_rec_back_weekday(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to weekday selection"""
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    keyboard = [
        [InlineKeyboardButton(text=name, callback_data=f"REC-WEEKDAY-{i}")]
        for i, name in enumerate(weekday_names)
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=REC_BACK_FREQUENCY),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await query.message.edit_text("<b>Select day of week:</b>", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_WEEKDAY)


@router.callback_query(F.data == REC_BACK_DAY)
async def handle_rec_back_day(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to day of month selection"""
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    keyboard = []
    for day in range(1, 32):
        keyboard.append([InlineKeyboardButton(text=str(day), callback_data=f"REC-DAY-{day}")])
    rows = []
    for i in range(0, len(keyboard), 7):
        row = [keyboard[i + j][0] for j in range(min(7, len(keyboard) - i))]
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=REC_BACK_FREQUENCY),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await query.message.edit_text("<b>Select day of month:</b>", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_DAY_OF_MONTH)


@router.callback_query(F.data == REC_BACK_TIME)
async def handle_rec_back_time(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to time selection"""
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    data = await state.get_data()
    freq = data.get('recurring_frequency')
    back_cb = REC_BACK_WEEKDAY if freq in ('weekly', 'biweekly') else REC_BACK_DAY
    
    keyboard = []
    for hour in range(6, 24):
        keyboard.append([InlineKeyboardButton(text=f"{hour}:00", callback_data=f"REC-TIME-{hour}")])
    rows = []
    for i in range(0, len(keyboard), 3):
        row = [keyboard[i][0]]
        if i + 1 < len(keyboard):
            row.append(keyboard[i + 1][0])
        if i + 2 < len(keyboard):
            row.append(keyboard[i + 2][0])
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=back_cb),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="REC-CONFIRM-no")
    ])
    reply_markup = InlineKeyboardMarkup(inline_keyboard=rows)
    await query.message.edit_text("<b>Select time:</b>", reply_markup=reply_markup)
    await state.set_state(RECURRING_SELECT_TIME)


@router.callback_query(F.data == REC_BACK_END_DATE)
async def handle_rec_back_end_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to end date selection"""
    await query.answer()
    if not await _check_teacher(query, state, session):
        return
    await recurring_select_time(query, state, session)
