"""Student homework handlers - view, mark received/completed"""
import json
import logging
from sqlalchemy import select

from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from models import Student, Teacher, Lesson, Homework
from homework_service import HomeworkService
from bot.utils.helpers import safe_parse_callback_int
from handlers.homework.teacher import _student_status_text

logger = logging.getLogger(__name__)


class StudentHomeworkStates(StatesGroup):
    LIST = State()
    VIEW_DETAIL = State()


async def student_homework_menu(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show student's homework list"""
    user_id = query.from_user.id

    result = await session.execute(select(Student).filter_by(telegram_id=user_id))
    student = result.scalar_one_or_none()
    if not student:
        await query.answer("Student not found", show_alert=True)
        await state.clear()
        return

    homeworks = await HomeworkService.get_student_homeworks(session, student.id, limit=20)

    if not homeworks:
        await query.message.edit_text(
            text="\U0001f4cb No homework received yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")]
            ])
        )
        await state.clear()
        return

    keyboard = []
    teacher_ids = list(set(hw.teacher_id for hw in homeworks))
    teachers_result = await session.execute(select(Teacher).filter(Teacher.id.in_(teacher_ids)))
    teachers_map = {t.id: t for t in teachers_result.scalars().all()}

    for hw in homeworks:
        icon, status_text = _student_status_text(hw)
        date_str = hw.sent_at.strftime('%d.%m.%Y')
        teacher = teachers_map.get(hw.teacher_id)
        teacher_name = teacher.name if teacher else "Teacher"
        text_preview = hw.text[:40].replace('\n', ' ')
        keyboard.append([
            InlineKeyboardButton(
                text=f"{icon} {date_str} - {teacher_name}: {text_preview}",
                callback_data=f"view_hw_{hw.id}"
            )
        ])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")])

    await query.message.edit_text(
        text="\U0001f4da Your Homework:\n\nTap on a homework to view details.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

    await state.set_state(StudentHomeworkStates.LIST)


async def student_view_homework_detail(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show homework detail with action buttons"""
    homework_id = safe_parse_callback_int(query.data, delimiter='_', position=-1)
    if homework_id is None:
        await query.answer("⚠️ Invalid callback data.", show_alert=True)
        await state.clear()
        return
    user_id = query.from_user.id

    result = await session.execute(select(Student).filter_by(telegram_id=user_id))
    student = result.scalar_one_or_none()
    if not student:
        await query.answer("Student not found", show_alert=True)
        await state.clear()
        return

    homework = await session.get(Homework, homework_id)
    if not homework or homework.student_id != student.id:
        await query.answer("Homework not found", show_alert=True)
        await state.clear()
        return

    teacher = await session.get(Teacher, homework.teacher_id)
    teacher_name = teacher.name if teacher else "Teacher"
    sent_date = homework.sent_at.strftime('%d.%m.%Y %H:%M')
    icon, student_status = _student_status_text(homework)
    status_text = f"{icon} {student_status}"

    lesson_info = ""
    if homework.lesson_id:
        lesson = await session.get(Lesson, homework.lesson_id)
        if lesson:
            lesson_info = f"\n\U0001f4c5 Lesson: {lesson.date} at {lesson.time.strftime('%H:%M')}"

    has_interactive = homework.json_content is not None

    if has_interactive:
        try:
            meta = json.loads(homework.json_content)
            ai_title = meta.get("title", "AI Homework")
            ai_level = meta.get("level", "")
            ai_topic = meta.get("topic", "")
        except (json.JSONDecodeError, TypeError):
            ai_title, ai_level, ai_topic = "AI Homework", "", ""

        text = (
            f"\U0001f4dd Homework\n\n"
            f"From: {teacher_name}\n"
            f"Date: {sent_date}\n"
            f"Status: {status_text}\n\n"
            f"\U0001f9e0 <b>AI-Generated Homework</b>\n"
            f"\U0001f4cc <b>{ai_title}</b>\n"
            f"\U0001f539 Level: {ai_level}  |  Topic: {ai_topic}\n\n"
            f"\U0001f3ae Interactive exercises available \u2014 tap the button below!"
        )
    else:
        display_text = homework.text
        text = (f"\U0001f4dd Homework\n\n"
                f"From: {teacher_name}\n"
                f"Date: {sent_date}\n"
                f"Status: {status_text}{lesson_info}\n\n"
                f"{display_text}")

    keyboard = []

    if has_interactive:
        keyboard.append([
            InlineKeyboardButton(text="\U0001f3ae Start Interactive", callback_data=f"ex_start_{homework.id}")
        ])

    if homework.status == 'sent':
        keyboard.append([
            InlineKeyboardButton(text="\U0001f4e5 Mark as Received", callback_data=f"mark_received_{homework.id}")
        ])
    elif homework.status == 'received':
        keyboard.append([
            InlineKeyboardButton(text="\u2705 Mark as Completed", callback_data=f"mark_completed_{homework.id}")
        ])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="student_homework_start")])

    await query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        disable_web_page_preview=True
    )

    await state.set_state(StudentHomeworkStates.VIEW_DETAIL)


async def student_mark_homework_received(query: CallbackQuery, state: FSMContext, session) -> None:
    """Mark homework as received"""
    homework_id = safe_parse_callback_int(query.data, delimiter='_', position=-1)
    if homework_id is None:
        await query.answer("⚠️ Invalid callback data.", show_alert=True)
        return
    user_id = query.from_user.id

    result = await session.execute(select(Student).filter_by(telegram_id=user_id))
    student = result.scalar_one_or_none()
    if not student:
        await query.answer("Student not found", show_alert=True)
        return

    try:
        homework = await HomeworkService.mark_homework_received(session, homework_id, student.id)
        await session.commit()

        await query.answer("\u2705 Marked as received!")

        await student_view_homework_detail(query, state, session)
    except ValueError as e:
        logger.warning("ValueError in mark_received: %s", e)
        await query.answer("Operation failed. Please try again.", show_alert=True)
    except Exception as e:
        logger.error(f"Error marking homework received: {e}")
        await query.answer("Error updating status", show_alert=True)


async def student_mark_homework_completed(query: CallbackQuery, state: FSMContext, session) -> None:
    """Mark homework as completed"""
    homework_id = safe_parse_callback_int(query.data, delimiter='_', position=-1)
    if homework_id is None:
        await query.answer("⚠️ Invalid callback data.", show_alert=True)
        return
    user_id = query.from_user.id

    result = await session.execute(select(Student).filter_by(telegram_id=user_id))
    student = result.scalar_one_or_none()
    if not student:
        await query.answer("Student not found", show_alert=True)
        return

    try:
        homework = await HomeworkService.mark_homework_completed(session, homework_id, student.id)
        await session.commit()

        await query.answer("\u2705 Great job! Homework completed!")

        await student_view_homework_detail(query, state, session)
    except ValueError as e:
        logger.warning("ValueError in mark_completed: %s", e)
        await query.answer("Operation failed. Please try again.", show_alert=True)
    except Exception as e:
        logger.error(f"Error marking homework completed: {e}")
        await query.answer("Error updating status", show_alert=True)
