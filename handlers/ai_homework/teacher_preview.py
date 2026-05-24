"""Teacher AI homework preview flow — approve, confirm send, edit"""
import json
import logging
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from models import Student
from homework_service import HomeworkService
from handlers.ai_homework.teacher_states import AIHomeworkStates
from handlers.ai_homework.teacher import _generator

logger = logging.getLogger(__name__)


async def ai_hw_approve(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    student_id = data.get("student_id")
    teacher_id = data.get("teacher_id")
    raw_json = data.get("raw_json") or data.get("pack_json", "{}")

    if not student_id or not teacher_id:
        await query.answer("Missing student or teacher data", show_alert=True)
        return

    try:
        pack = _generator.validate_json(raw_json)
        if pack[0]:
            display_text = _generator.format_for_student(pack[0])
        else:
            display_text = raw_json
    except Exception:
        display_text = raw_json

    student = await session.get(Student, student_id)
    student_name = student.name if student else "Student"

    keyboard = [
        [InlineKeyboardButton(text="\u2705 Confirm Send", callback_data="ai_hw_confirm_send")],
        [InlineKeyboardButton(text="\u274c Cancel", callback_data="ai_hw_cancel")],
    ]

    await query.message.edit_text(
        text=f"\U0001f4dd <b>Send to {student_name}?</b>\n\nThe homework will be saved and sent to the student.\n\n{display_text[:500]}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.update_data(display_text=display_text)


async def ai_hw_confirm_send(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    student_id = data.get("student_id")
    teacher_id = data.get("teacher_id")
    raw_json = data.get("raw_json") or data.get("pack_json", "{}")
    display_text = data.get("display_text", raw_json)
    mode = data.get("mode", "generate")

    if not student_id or not teacher_id:
        await query.answer("Missing data", show_alert=True)
        return

    try:
        homework = await HomeworkService.create_homework(
            session=session,
            student_id=student_id,
            teacher_id=teacher_id,
            text=display_text,
            lesson_id=None,
            json_content=raw_json,
        )

        title = data.get("title", "AI Homework")
        level = data.get("level", "")
        topic = data.get("topic", "")

        student = await session.get(Student, student_id)
        if student and student.telegram_id:
            try:
                notify = (
                    f"\U0001f9e0 <b>New AI Homework!</b>\n\n"
                    f"<i>{title}</i>\n"
                    f"Level: {level}  |  Topic: {topic}\n\n"
                    f"Interactive exercises await \U0001f3ae"
                )
                await query.bot.send_message(
                    chat_id=student.telegram_id,
                    text=notify,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="\U0001f4da View Homework", callback_data="student_homework_start")],
                    ]),
                )
            except Exception as e:
                logger.error("Failed to notify student %d: %s", student_id, e)

        await session.commit()
        await query.message.edit_text(
            text="\u2705 Homework approved and sent to student!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back to Menu", callback_data="back_to_main")],
            ]),
        )
        logger.info(
            "AI homework %d created by teacher %d using mode=%s",
            homework.id, teacher_id, mode,
        )

    except ValueError as e:
        logger.warning("ValueError in AI homework creation: %s", e)
        await query.message.edit_text(text="\u274c Operation failed. Please check your input and try again.")
    except Exception as e:
        logger.error("Error creating AI homework: %s", e)
        await query.message.edit_text(text="\u274c Failed to create homework. Please try again.")

    await state.clear()


async def ai_hw_edit(query: CallbackQuery, state: FSMContext, session) -> None:
    from handlers.ai_homework.teacher_generate import _show_preview_from_query

    data = await state.get_data()
    raw_json = data.get("raw_json") or data.get("pack_json", "{}")

    try:
        pretty = json.dumps(json.loads(raw_json), indent=2, ensure_ascii=False)
    except Exception:
        pretty = raw_json

    await query.message.edit_text(
        text="\u270f\ufe0f Edit the homework JSON below.\n\n"
        "Send the corrected JSON, or use /cancel to abandon.\n\n"
        f"```json\n{pretty[:3000]}\n```",
    )
    await state.set_state(AIHomeworkStates.EDIT_TEXT)


async def ai_hw_edit_text(message: Message, state: FSMContext, session) -> None:
    from handlers.ai_homework.teacher_generate import _show_preview

    edited = message.text.strip()

    result = await _generator.generate_from_json(edited)
    if not result.success:
        await message.answer(
            text=f"\u274c {result.error}\n\nPlease fix and resend, or /cancel.",
        )
        return

    await state.update_data(
        raw_json=result.raw_json,
        pack_json=result.pack.model_dump_json(indent=2),
        title=result.pack.title,
    )

    await _show_preview(message, state, result)
