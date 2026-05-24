"""Schedule lesson and my schedule handlers"""
import logging
from datetime import datetime, date, time, timezone
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models import Teacher, Student, Lesson
from services.lesson_service import LessonService
from services.notification_service import NotificationService
from services.payment.bulk_balance import apply_balance_to_lesson
from bot.utils.helpers import get_teacher, safe_parse_callback_int

logger = logging.getLogger(__name__)
router = Router()


class ScheduleLesson(StatesGroup):
    select_student = State()
    select_time = State()


@router.callback_query(F.data.startswith('SCHEDULE-LESSON-'))
async def schedule_lesson_start(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Start scheduling a lesson: select student"""
    await query.answer()
    try:
        _, date_info = query.data.split("SCHEDULE-LESSON-", 1)
        year, month, day = map(int, date_info.split('-'))
    except (ValueError, TypeError):
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    await state.update_data(schedule_date=(year, month, day))

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        await state.clear()
        return

    result = await session.execute(select(Student).filter_by(teacher_id=teacher.id))
    students = result.scalars().all()
    if not students:
        await query.message.edit_text("👥 You have no students to schedule a lesson with.")
        await state.clear()
        return

    keyboard = [
        [InlineKeyboardButton(text=student.name, callback_data=f"SCHEDULE-TIME-{student.id}")]
        for student in students
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="SCHEDULE-BACK-date"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ])
    await query.message.edit_text("<b>Select student:</b>", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(ScheduleLesson.select_student)


@router.callback_query(ScheduleLesson.select_student, F.data.startswith('SCHEDULE-TIME-'))
async def schedule_lesson_select_time(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Select time for lesson"""
    await query.answer()
    student_id = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if student_id is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    await state.update_data(student_id=student_id)

    from bot.keyboards.calendar_kb import build_time_keyboard
    await query.message.edit_text("<b>Select time:</b>", reply_markup=build_time_keyboard(back_callback="SCHEDULE-BACK-student"))
    await state.set_state(ScheduleLesson.select_time)


@router.callback_query(F.data == "SCHEDULE-BACK-student")
async def schedule_back_to_student(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to student selection when scheduling"""
    await query.answer()
    data = await state.get_data()
    if 'schedule_date' not in data:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    year, month, day = data['schedule_date']

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        await state.clear()
        return

    result = await session.execute(select(Student).filter_by(teacher_id=teacher.id))
    students = result.scalars().all()
    if not students:
        await query.message.edit_text("👥 You have no students to schedule a lesson with.")
        await state.clear()
        return

    keyboard = [
        [InlineKeyboardButton(text=student.name, callback_data=f"SCHEDULE-TIME-{student.id}")]
        for student in students
    ]
    keyboard.append([
        InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="SCHEDULE-BACK-date"),
        InlineKeyboardButton(text="\u274c Cancel", callback_data="CANCEL-CONV")
    ])
    await query.message.edit_text("Select student:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await state.set_state(ScheduleLesson.select_student)


@router.callback_query(F.data == "SCHEDULE-BACK-date")
async def schedule_back_to_date(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Back to calendar day view when scheduling a lesson"""
    await query.answer()
    data = await state.get_data()
    year, month, day = data.get('schedule_date', (0, 0, 0))
    await state.clear()

    if year == 0:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        return

    selected_date = date(year, month, day)
    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        return

    result = await session.execute(
        select(Lesson).options(selectinload(Lesson.student)).filter(
            Lesson.teacher_id == teacher.id,
            Lesson.date == selected_date
        )
    )
    lessons = result.scalars().all()

    if not lessons:
        keyboard = [
            [InlineKeyboardButton(text="➕ Schedule Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")]
        ]
        await query.message.edit_text(
            f"No lessons scheduled for {day}-{month}-{year}.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
    else:
        schedule_lines = []
        for i, lesson in enumerate(lessons):
            prefix = '\U0001f501 ' if lesson.recurring_pattern_id else ''
            student_name = lesson.student.name if lesson.student else 'Unknown'
            schedule_lines.append(f"{i+1}. {prefix}{lesson.time.strftime('%H:%M')} - {student_name}")
        schedule_text = "\n".join(schedule_lines)

        keyboard = [
            [InlineKeyboardButton(text="➕ Add Lesson", callback_data=f"SCHEDULE-LESSON-{year}-{month}-{day}")]
        ]
        for i, lesson in enumerate(lessons):
            keyboard.append([
                InlineKeyboardButton(text=f"\u2716\ufe0f Cancel Lesson {i+1}", callback_data=f"SMART-DEL-LESSON-{lesson.id}")
            ])
            if lesson.recurring_pattern_id is None:
                keyboard.append([
                    InlineKeyboardButton(text=f"\U0001f501 Make Recurring {i+1}", callback_data=f"CONVERT-RECUR-{lesson.id}")
                ])
        keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back to Calendar", callback_data="calendar")])

        await query.message.edit_text(
            f"Schedule for {day}-{month}-{year}:\n{schedule_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(ScheduleLesson.select_time, F.data.startswith('TIME-SLOT-'))
async def schedule_lesson_confirm(query: CallbackQuery, state: FSMContext, session: AsyncSession):
    """Confirm scheduling the lesson"""
    await query.answer()
    hour = safe_parse_callback_int(query.data, delimiter='-', position=-1)
    if hour is None:
        await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
        await state.clear()
        return
    data = await state.get_data()
    if 'student_id' not in data or 'schedule_date' not in data:
        await query.message.edit_text("⏳ Session expired. Please start over.")
        await state.clear()
        return
    student_id = data['student_id']
    year, month, day = data['schedule_date']
    lesson_date = date(year, month, day)
    lesson_time = time(hour, 0)

    teacher = await get_teacher(session, query.from_user.id)
    if not teacher:
        await query.message.edit_text("⚠️ You are not registered as a teacher.")
        await state.clear()
        return

    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    if not student or student.teacher_id != teacher.id:
        await query.message.edit_text("🔒 You can only schedule lessons for your own students.")
        await state.clear()
        return

    if lesson_date < datetime.now(timezone.utc).date():
        await query.message.edit_text("⚠️ Cannot schedule a lesson for a past date.")
        await state.clear()
        return

    result = await session.execute(
        select(Lesson).filter(
            Lesson.teacher_id == teacher.id,
            Lesson.date == lesson_date,
            Lesson.time == lesson_time
        )
    )
    if result.scalar_one_or_none():
        await query.message.edit_text(f"⚠️ On {day}-{month}-{year} at {hour}:00 the teacher already has a lesson scheduled.")
        await state.clear()
        return

    result = await session.execute(
        select(Lesson).filter(
            Lesson.student_id == student_id,
            Lesson.date == lesson_date,
            Lesson.time == lesson_time
        )
    )
    if result.scalar_one_or_none():
        await query.message.edit_text(f"⚠️ On {day}-{month}-{year} at {hour}:00 the student already has a lesson scheduled.")
        await state.clear()
        return

    success, message, lesson = await LessonService.create_lesson(
        session, teacher.id, student_id, lesson_date, lesson_time
    )
    if not success:
        await query.message.edit_text(message)
        await state.clear()
        return

    if lesson:
        await apply_balance_to_lesson(session, lesson)

    result = await session.execute(select(Student).filter_by(id=student_id))
    student = result.scalar_one_or_none()
    if student:
        await NotificationService.notify_student_lesson_created(
            query.bot, student, teacher, lesson_date, lesson_time
        )

    await state.clear()
    await query.message.edit_text(f"✅ Lesson scheduled for {day}-{month}-{year} at {hour}:00.")


@router.message(Command('my_schedule'))
async def my_schedule(message: Message, session: AsyncSession):
    """Show schedule for both teachers and students"""
    teacher_result = await session.execute(select(Teacher).filter_by(telegram_id=message.from_user.id))
    teacher = teacher_result.scalar_one_or_none()
    
    if teacher:
        today = datetime.now(timezone.utc).date()
        result = await session.execute(
            select(Lesson).options(selectinload(Lesson.student)).filter(
                Lesson.teacher_id == teacher.id,
                Lesson.date >= today
            ).order_by(Lesson.date, Lesson.time)
        )
        lessons = result.scalars().all()
        if not lessons:
            await message.answer("📭 You have no scheduled lessons.")
        else:
            schedule_text = "<b>Your schedule:</b>\n" + "\n".join(
                [f"{lesson.date} {lesson.time.strftime('%H:%M')} - {lesson.student.name if lesson.student else 'Unknown'}" for lesson in lessons]
            )
            await message.answer(schedule_text)
        return

    student_result = await session.execute(select(Student).filter_by(telegram_id=message.from_user.id))
    student = student_result.scalar_one_or_none()
    
    if not student:
        await message.answer("⚠️ You are not registered as a teacher or student.")
        return

    today = datetime.now(timezone.utc).date()
    result = await session.execute(
        select(Lesson).options(selectinload(Lesson.teacher)).filter(
            Lesson.student_id == student.id,
            Lesson.date >= today
        ).order_by(Lesson.date, Lesson.time)
    )
    lessons = result.scalars().all()
    if not lessons:
        await message.answer("📭 You have no scheduled lessons.")
    else:
        schedule_text = "<b>Your schedule:</b>\n" + "\n".join(
            [f"{lesson.date} {lesson.time.strftime('%H:%M')} - {lesson.teacher.name}" for lesson in lessons]
        )
        await message.answer(schedule_text)
