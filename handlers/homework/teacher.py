"""Teacher homework handlers - create, view, send homework"""
import logging
from datetime import datetime
from sqlalchemy import select

from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import SessionLocal
from models import Student, Teacher, Lesson, Homework
from homework_service import HomeworkService
from services.notification_service import NotificationService
from access_control import AccessControlService
from bot.utils.helpers import sanitize_input, safe_parse_callback_int

logger = logging.getLogger(__name__)


class TeacherHomeworkStates(StatesGroup):
    SELECT_TYPE = State()
    SELECT_LESSON = State()
    EDIT_TEXT = State()
    CONFIRM = State()


PAGE_SIZE = 7


async def teacher_view_homework_history(query: CallbackQuery, state: FSMContext, session, page: int = 0) -> None:
    """Show teacher's homework history with pagination"""
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        await state.clear()
        return

    homeworks = await HomeworkService.get_teacher_homeworks(session, teacher.id, limit=100)
    total = len(homeworks)

    if total == 0:
        await query.message.edit_text(
            text="\U0001f4cb No homework sent yet.\n\nUse the menu to send homework to students.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back")]
            ])
        )
        return

    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_homeworks = homeworks[start:end]

    student_ids = list(set(hw.student_id for hw in homeworks))
    students_result = await session.execute(select(Student).filter(Student.id.in_(student_ids)))
    students_map = {s.id: s for s in students_result.scalars().all()}

    keyboard = []
    for hw in page_homeworks:
        student = students_map.get(hw.student_id)
        student_name = student.name if student else f"Student {hw.student_id}"
        date_str = hw.sent_at.strftime('%d.%m.%Y')
        icon = _homework_teacher_icon(hw)
        preview = hw.text[:40].replace('\n', ' ')
        label = f"{icon} {date_str} {student_name}: {preview}"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"hw_detail_{hw.id}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="\u2b05\ufe0f Prev", callback_data=f"hw_history_p{page}"))
    nav_row.append(InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Next \u27a1\ufe0f", callback_data=f"hw_history_p{page + 2}"))
    keyboard.append(nav_row)

    await query.message.edit_text(
        text=f"\U0001f4cb Homework History (page {page + 1}/{total_pages}, {total} total)\n\nTap a homework to view details:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def teacher_homework_menu(query: CallbackQuery, state: FSMContext, session) -> None:
    """Main handler for teacher to send homework"""
    user_id = query.from_user.id

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        await state.clear()
        return

    keyboard = [
        [InlineKeyboardButton(text="\U0001f4da Send Post-Lesson Homework", callback_data="hw_post_lesson")],
        [InlineKeyboardButton(text="\u2795 Send Independent Homework", callback_data="hw_independent")],
        [InlineKeyboardButton(text="\U0001f4cb View Homework History", callback_data="hw_history")],
        [InlineKeyboardButton(text="\U0001f4ca Homework Stats", callback_data="hw_stats")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back")]
    ]

    reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    await query.message.edit_text(
        text="\U0001f4dd Homework Management\n\nSelect an option:",
        reply_markup=reply_markup
    )

    await state.set_state(TeacherHomeworkStates.SELECT_TYPE)


async def teacher_select_lesson(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show teacher's recent lessons to select from"""
    user_id = query.from_user.id
    data = (await state.get_data()).get('hw_type') or query.data.split("_", 1)[1]
    hw_type = data

    await state.update_data(hw_type=hw_type)

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        await state.clear()
        return

    if hw_type == "post_lesson":
        today = datetime.now().date()
        result = await session.execute(
            select(Lesson)
            .where(Lesson.teacher_id == teacher.id)
            .where(Lesson.date <= today)
            .order_by(Lesson.date.desc(), Lesson.time.desc())
            .limit(10)
        )
        lessons = result.scalars().all()

        if not lessons:
            await query.answer("No lessons found", show_alert=True)
            await state.clear()
            return

        keyboard = []
        for lesson in lessons:
            student_result = await session.get(Student, lesson.student_id)
            student_name = student_result.name if student_result else "Unknown"

            hw = await HomeworkService.get_lesson_homework(session, lesson.id)
            hw_status = " \u2713" if hw else ""

            label = f"{student_name} - {lesson.date} {lesson.time.strftime('%H:%M')}{hw_status}"
            callback = f"hw_lesson_{lesson.id}"
            keyboard.append([InlineKeyboardButton(text=label, callback_data=callback)])

        keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            text="Select a lesson for homework:",
            reply_markup=reply_markup
        )

    else:  # independent homework
        result = await session.execute(
            select(Student)
            .where(Student.teacher_id == teacher.id)
            .order_by(Student.name)
        )
        students = result.scalars().all()

        if not students:
            await query.answer("No students found", show_alert=True)
            await state.clear()
            return

        keyboard = []
        for student in students:
            label = f"{student.name}"
            callback = f"hw_student_{student.id}"
            keyboard.append([InlineKeyboardButton(text=label, callback_data=callback)])

        keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back")])

        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await query.message.edit_text(
            text="Select a student for homework:",
            reply_markup=reply_markup
        )

    await state.set_state(TeacherHomeworkStates.SELECT_LESSON)


async def teacher_edit_homework_text(query: CallbackQuery, state: FSMContext, session) -> None:
    """Get homework text from teacher"""
    callback_data = query.data

    if callback_data.startswith("hw_lesson_"):
        lesson_id = safe_parse_callback_int(callback_data, delimiter='_', position=-1)
        if lesson_id is None:
            await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
            await state.clear()
            return
        await state.update_data(lesson_id=lesson_id)
        lesson = await session.get(Lesson, lesson_id)
        if lesson:
            await state.update_data(student_id=lesson.student_id)
    elif callback_data.startswith("hw_student_"):
        student_id = safe_parse_callback_int(callback_data, delimiter='_', position=-1)
        if student_id is None:
            await query.message.edit_text("⚠️ Invalid callback data. Please try again.")
            await state.clear()
            return
        await state.update_data(student_id=student_id, lesson_id=None)

    await query.message.edit_text(
        text="\U0001f4dd Enter homework text:\n\n"
        "(You can include URLs, emojis, and line breaks. "
        "URLs will be automatically clickable.)\n\n"
        "Send /cancel to abandon."
    )

    await state.set_state(TeacherHomeworkStates.EDIT_TEXT)


async def teacher_confirm_homework(message: Message, state: FSMContext, session) -> None:
    """Confirm and save homework"""
    user_id = message.from_user.id
    homework_text = message.text

    if not homework_text or not homework_text.strip():
        await message.answer("Homework text cannot be empty")
        return
    if len(homework_text) > 5000:
        await message.answer("Homework text is too long (max 5000 characters)")
        return

    homework_text = sanitize_input(homework_text)

    data = await state.get_data()
    lesson_id = data.get('lesson_id')
    student_id = data.get('student_id')

    if not student_id:
        await message.answer("Error: No student selected. Please start over.")
        await state.clear()
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await message.answer("Teacher not found. Please register first.")
        await state.clear()
        return

    if lesson_id:
        lesson = await session.get(Lesson, lesson_id)
        if not lesson or lesson.teacher_id != teacher.id:
            await message.answer("You can only send homework for your own lessons.")
            await state.clear()
            return

    try:
        homework = await HomeworkService.create_homework(
            session=session,
            student_id=student_id,
            teacher_id=teacher.id,
            text=homework_text,
            lesson_id=lesson_id
        )

        student = await session.get(Student, student_id)
        if student and student.telegram_id:
            try:
                lesson_info = ""
                if lesson_id:
                    lesson = await session.get(Lesson, lesson_id)
                    if lesson:
                        lesson_info = f" (for {lesson.date} {lesson.time.strftime('%H:%M')})"
                
                homework_type = "\U0001f4da New homework" if lesson_id else "\U0001f4dd New independent homework"
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                hw_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="\U0001f4dd View Homework", callback_data=f"view_hw_{homework.id}")]
                ])
                await message.bot.send_message(
                    chat_id=student.telegram_id,
                    text=f"{homework_type}{lesson_info}:\n\n{homework_text}",
                    reply_markup=hw_keyboard
                )
            except Exception as e:
                logger.error(f"Failed to notify student {student_id}: {e}")

        await session.commit()
        await message.answer("\u2705 Homework sent successfully!")
        logger.info(f"Homework {homework.id} created by teacher {teacher.id}")

    except ValueError as e:
        logger.warning("ValueError creating homework: %s", e)
        await message.answer("\u274c Operation failed. Please check your input and try again.")
    except Exception as e:
        logger.error(f"Error creating homework: {e}")
        await message.answer("\u274c Failed to create homework. Please try again.")
    await state.clear()


# ═══════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════


def _homework_teacher_icon(hw: Homework) -> str:
    """Teacher-facing icon based on homework status and teacher_mark"""
    if hw.teacher_mark == 'fully_completed':
        return '\u2705'  # green check
    if hw.teacher_mark == 'main_completed':
        return '\u2705' if hw.optional_done else '\U0001f7e8'  # check or yellow square
    if hw.teacher_mark == 'partially_completed':
        return '\U0001f535'  # blue circle
    if hw.teacher_mark == 'not_completed':
        return '\u274c'  # red X
    if hw.status == 'completed':
        return '\u2705'
    if hw.status == 'received':
        return '\U0001f4e5'
    return '\U0001f4e4'  # sent


def _student_status_text(hw: Homework) -> (str, str):
    """Return (icon, text) for student-facing display.
    Full status text (e.g. 'Homework received') is returned as second element."""
    if hw.teacher_mark in ('main_completed', 'fully_completed'):
        return '\u2705', 'Homework completed'
    if hw.status == 'completed' and hw.teacher_mark is None:
        return '\u2705', 'Homework completed'
    if hw.status == 'received' and hw.teacher_mark is None:
        return '\U0001f4e5', 'Homework received'
    if hw.teacher_mark == 'partially_completed':
        return '\U0001f535', 'Homework received'  # student sees "received"
    if hw.teacher_mark == 'not_completed':
        return '\U0001f4e5', 'Homework received'
    return '\U0001f4e4', 'Homework sent'


# ═══════════════════════════════════════════════════════════════════
# TEACHER HOMEWORK DETAIL
# ═══════════════════════════════════════════════════════════════════


async def teacher_view_homework_detail(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show homework detail with teacher mark buttons"""
    user_id = query.from_user.id
    parts = query.data.split('_')
    try:
        hw_id = int(parts[-1])
    except (ValueError, IndexError):
        await query.answer("Invalid homework", show_alert=True)
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    homework = await session.get(Homework, hw_id)
    if not homework or homework.teacher_id != teacher.id:
        await query.answer("Homework not found", show_alert=True)
        return

    student = await session.get(Student, homework.student_id)
    student_name = student.name if student else "Unknown"
    date_str = homework.sent_at.strftime('%d.%m.%Y %H:%M')

    icon, student_status = _student_status_text(homework)
    lesson_info = ""
    if homework.lesson_id:
        lesson = await session.get(Lesson, homework.lesson_id)
        if lesson:
            lesson_info = f"\n\U0001f4c5 Lesson: {lesson.date} {lesson.time.strftime('%H:%M')}"

    status_line = f"{icon} {student_status}"
    if homework.teacher_mark:
        mark_labels = {
            'not_completed': 'Teacher: Not completed',
            'partially_completed': 'Teacher: Partially completed',
            'main_completed': 'Teacher: Main completed',
            'fully_completed': 'Teacher: Fully completed',
        }
        status_line += f"\n\U0001f468\u200d\U0001f3eb {mark_labels.get(homework.teacher_mark, homework.teacher_mark)}"
        if homework.optional_done:
            status_line += " + Optional done"

    lines = [
        f"\U0001f4dd <b>Homework Detail</b>",
        f"Student: {student_name}",
        f"Sent: {date_str}{lesson_info}",
        f"Status: {status_line}",
        "",
        homework.text[:500] if homework.text else "",
    ]

    keyboard = _build_teacher_marks_keyboard(homework)

    await query.message.edit_text(
        text="\n".join(lines),
        reply_markup=keyboard,
        disable_web_page_preview=True,
    )


def _build_teacher_marks_keyboard(homework: Homework) -> InlineKeyboardMarkup:
    """Build keyboard with teacher mark buttons for homework detail view"""
    hw_id = homework.id
    tm = homework.teacher_mark
    btn = lambda text, data: InlineKeyboardButton(text=text, callback_data=data)

    row1 = []
    row2 = []
    row3 = []

    if homework.status in ('received', 'completed') or tm is not None:
        row1 = [
            btn("\u274c Not completed", f"hw_mark_{hw_id}_not_completed"),
            btn("\U0001f535 Partially", f"hw_mark_{hw_id}_partially_completed"),
        ]
        row2 = [
            btn("\u2705 Main completed", f"hw_mark_{hw_id}_main_completed"),
        ]
        if tm == 'main_completed':
            opt_label = "\u2b50 Optional done" if not homework.optional_done else "\u2705 Optional done"
            row2.append(btn(opt_label, f"hw_toggle_opt_{hw_id}"))
        row3 = [
            btn("\u2705\u2705 Fully completed", f"hw_mark_{hw_id}_fully_completed"),
        ]
        if tm is not None:
            row3.append(btn("\U0001f504 Reset", f"hw_mark_{hw_id}_reset"))

    back_row = [btn("\u2b05\ufe0f Back", "hw_history")]

    kb = [row for row in [row1, row2, row3, back_row] if row]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# ═══════════════════════════════════════════════════════════════════
# TEACHER MARK HOMEWORK
# ═══════════════════════════════════════════════════════════════════


async def teacher_mark_homework(query: CallbackQuery, state: FSMContext, session) -> None:
    """Handle teacher mark action on a homework"""
    user_id = query.from_user.id
    parts = query.data.split('_')
    try:
        hw_id = int(parts[3])
        mark = parts[4]
    except (ValueError, IndexError):
        await query.answer("Invalid data", show_alert=True)
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    if mark == 'reset':
        mark_value = None
    else:
        mark_value = mark

    try:
        hw = await HomeworkService.set_teacher_mark(session, hw_id, teacher.id, mark_value)
        await session.commit()
    except ValueError as e:
        await query.answer(str(e), show_alert=True)
        return

    await query.answer("\u2705 Mark saved")
    query.data = f"hw_detail_{hw_id}"
    await teacher_view_homework_detail(query, state, session)


async def teacher_toggle_optional(query: CallbackQuery, state: FSMContext, session) -> None:
    """Toggle the optional_done flag on a homework"""
    user_id = query.from_user.id
    parts = query.data.split('_')
    try:
        hw_id = int(parts[-1])
    except (ValueError, IndexError):
        await query.answer("Invalid data", show_alert=True)
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    homework = await session.get(Homework, hw_id)
    if not homework or homework.teacher_id != teacher.id:
        await query.answer("Homework not found", show_alert=True)
        return

    homework.optional_done = not homework.optional_done
    homework.updated_at = datetime.now(timezone.utc)
    await session.commit()

    await query.answer("\u2705 Optional toggled")
    query.data = f"hw_detail_{hw_id}"
    await teacher_view_homework_detail(query, state, session)


# ═══════════════════════════════════════════════════════════════════
# TEACHER HOMEWORK STATISTICS
# ═══════════════════════════════════════════════════════════════════


async def teacher_homework_stats(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show homework statistics for the teacher"""
    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    stats = await HomeworkService.get_homework_stats(session, teacher.id)

    if stats['total'] == 0:
        await query.message.edit_text(
            text="\U0001f4ca <b>Homework Statistics</b>\n\nNo homework sent yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back")],
            ]),
        )
        return

    lines = [
        f"\U0001f4ca <b>Homework Statistics</b>",
        "",
        f"Total sent: <b>{stats['total']}</b>",
        "",
        f"\U0001f4e4 Sent (not received): {stats['sent_count']}",
        f"\U0001f4e5 Received (not evaluated): {stats['received_count']}",
        f"\u2705 Completed: <b>{stats['completed']}</b> ({stats['completion_pct']}%)",
        f"   \U0001f4d1 Main completed: {stats['main_completed']}",
        f"   \u2b50 Optional completed: {stats['optional_completed']}",
        f"\U0001f535 Partially completed: {stats['partially_completed']}",
        f"\u274c Not completed: {stats['not_completed']}",
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f504 Refresh", callback_data="hw_stats")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="hw_back")],
    ])

    await query.message.edit_text(
        text="\n".join(lines),
        reply_markup=keyboard,
    )


async def teacher_student_homework_stats(query: CallbackQuery, state: FSMContext, session) -> None:
    """Show per-student homework statistics"""
    user_id = query.from_user.id
    parts = query.data.split('_')
    try:
        student_id = int(parts[-1])
    except (ValueError, IndexError):
        await query.answer("Invalid data", show_alert=True)
        return

    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    student = await session.get(Student, student_id)
    if not student or student.teacher_id != teacher.id:
        await query.answer("Student not found", show_alert=True)
        return

    stats = await HomeworkService.get_homework_stats(session, teacher.id, student_id=student_id)

    if stats['total'] == 0:
        await query.message.edit_text(
            text=f"\U0001f4ca <b>Homework Stats: {student.name}</b>\n\nNo homework sent.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data=f"student_info-{student_id}")],
            ]),
        )
        return

    lines = [
        f"\U0001f4ca <b>Homework Stats: {student.name}</b>",
        "",
        f"Total sent: <b>{stats['total']}</b>",
        "",
        f"\U0001f4e4 Sent (not received): {stats['sent_count']}",
        f"\U0001f4e5 Received (not evaluated): {stats['received_count']}",
        f"\u2705 Completed: <b>{stats['completed']}</b> ({stats['completion_pct']}%)",
        f"   \U0001f4d1 Main completed: {stats['main_completed']}",
        f"   \u2b50 Optional completed: {stats['optional_completed']}",
        f"\U0001f535 Partially completed: {stats['partially_completed']}",
        f"\u274c Not completed: {stats['not_completed']}",
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f504 Refresh", callback_data=f"hw_student_stats_{student_id}")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to student", callback_data=f"student_info-{student_id}")],
    ])

    await query.message.edit_text(
        text="\n".join(lines),
        reply_markup=keyboard,
    )
