"""Teacher statistics dashboard for AI homework"""
import json
import logging
from sqlalchemy import select, func
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from models import Teacher, Student, Homework, HomeworkAttempt
from bot.utils.helpers import safe_parse_callback_int

logger = logging.getLogger(__name__)


async def ai_hw_stats(query: CallbackQuery, state: FSMContext, session) -> None:
    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    homeworks = await session.execute(
        select(Homework)
        .where(Homework.teacher_id == teacher.id, Homework.json_content.isnot(None))
        .order_by(Homework.sent_at.desc())
        .limit(20)
    )
    homeworks = homeworks.scalars().all()

    if not homeworks:
        await query.message.edit_text(
            text="\U0001f4ca No AI-generated homework sent yet.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")],
            ]),
        )
        return

    lines = ["\U0001f4ca <b>AI Homework Statistics</b>", "", "Select a homework to see details:"]
    keyboard = []

    for hw in homeworks:
        student = await session.get(Student, hw.student_id)
        name = student.name if student else f"Student {hw.student_id}"
        date = hw.sent_at.strftime("%d.%m.%Y")
        title = "(no title)"
        try:
            data = json.loads(hw.json_content) if hw.json_content else {}
            title = data.get("title", title)
        except (json.JSONDecodeError, TypeError):
            pass

        attempts = await session.execute(
            select(func.count(HomeworkAttempt.id), func.avg(HomeworkAttempt.score * 1.0 / HomeworkAttempt.total * 100))
            .where(HomeworkAttempt.homework_id == hw.id)
        )
        row = attempts.fetchone()
        count = row[0] if row else 0
        avg = round(row[1], 1) if row and row[1] else 0

        label = f"\U0001f4dd {date} - {name}: {count} attempt(s), {avg}% avg"
        keyboard.append([InlineKeyboardButton(text=label, callback_data=f"ai_hw_stats_hw_{hw.id}")])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")])

    await query.message.edit_text(
        text="\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def ai_hw_stats_hw(query: CallbackQuery, state: FSMContext, session) -> None:
    hw_id = safe_parse_callback_int(query.data, delimiter="_", position=-1)
    if hw_id is None:
        await query.answer("Invalid data", show_alert=True)
        return

    homework = await session.get(Homework, hw_id)
    if not homework:
        await query.answer("Homework not found", show_alert=True)
        return

    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher or homework.teacher_id != teacher.id:
        await query.answer("Access denied", show_alert=True)
        return

    attempts = await session.execute(
        select(HomeworkAttempt)
        .where(HomeworkAttempt.homework_id == hw_id)
        .order_by(HomeworkAttempt.completed_at.desc())
        .limit(10)
    )
    attempts = attempts.scalars().all()

    student = await session.get(Student, homework.student_id)
    name = student.name if student else "Unknown"

    title = "(no title)"
    try:
        data = json.loads(homework.json_content) if homework.json_content else {}
        title = data.get("title", title)
    except (json.JSONDecodeError, TypeError):
        pass

    lines = [
        f"\U0001f4dd <b>{title}</b>",
        f"Student: {name}",
        f"Date: {homework.sent_at.strftime('%d.%m.%Y %H:%M')}",
        "",
    ]

    if not attempts:
        lines.append("No attempts yet.")
    else:
        lines.append(f"<b>{len(attempts)} attempt(s):</b>")
        for i, a in enumerate(attempts, 1):
            pct = round(a.score / a.total * 100) if a.total > 0 else 0
            completed = a.completed_at.strftime("%d.%m.%Y %H:%M") if a.completed_at else "in progress"
            lines.append(f"  {i}. Score: {a.score}/{a.total} ({pct}%) - {completed}")

    keyboard = [
        [InlineKeyboardButton(text="\U0001f504 Try Again Stats", callback_data="ai_hw_stats")],
    ]

    if attempts:
        for a in attempts[:5]:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"Attempt {a.id}: {a.score}/{a.total}",
                    callback_data=f"ai_hw_stats_attempt_{a.id}",
                ),
            ])

    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")])

    await query.message.edit_text(
        text="\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )


async def ai_hw_stats_attempt(query: CallbackQuery, state: FSMContext, session) -> None:
    attempt_id = safe_parse_callback_int(query.data, delimiter="_", position=-1)
    if attempt_id is None:
        await query.answer("Invalid data", show_alert=True)
        return

    attempt = await session.get(HomeworkAttempt, attempt_id)
    if not attempt:
        await query.answer("Attempt not found", show_alert=True)
        return

    homework = await session.get(Homework, attempt.homework_id)
    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher or not homework or homework.teacher_id != teacher.id:
        await query.answer("Access denied", show_alert=True)
        return

    results = json.loads(attempt.results) if attempt.results else []

    lines = [
        f"\U0001f4ca <b>Attempt #{attempt.id}</b>",
        f"Score: {attempt.score}/{attempt.total}",
        f"Completed: {attempt.completed_at.strftime('%d.%m.%Y %H:%M') if attempt.completed_at else 'N/A'}",
        "",
        "<b>Exercise breakdown:</b>",
    ]

    for r in results:
        idx = r.get("idx", 0) + 1
        correct = r.get("correct")
        answer = r.get("answer", "")
        icon = "\u2705" if correct is True else "\u274c" if correct is False else "\U0001f4ac"
        lines.append(f"  {icon} Ex {idx}: {answer[:60]}")

    keyboard = [
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")],
    ]

    await query.message.edit_text(
        text="\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
