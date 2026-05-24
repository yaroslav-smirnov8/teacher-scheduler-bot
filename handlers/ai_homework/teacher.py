"""Teacher AI Homework handlers — core: mode selection, student selection, navigation"""
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from sqlalchemy import select
from models import Teacher, Student
from ai_homework.generator import AIHomeworkGenerator
from handlers.ai_homework.teacher_states import AIHomeworkStates


logger = logging.getLogger(__name__)

_generator = AIHomeworkGenerator()


def _build_back_cancel(cancel_only: bool = False) -> InlineKeyboardMarkup:
    rows = []
    if not cancel_only:
        rows.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="ai_hw_back")])
    rows.append([InlineKeyboardButton(text="\u274c Cancel", callback_data="ai_hw_cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


async def ai_hw_start(query: CallbackQuery, state: FSMContext, session) -> None:
    user_id = query.from_user.id
    result = await session.execute(select(Teacher).filter_by(telegram_id=user_id))
    teacher = result.scalar_one_or_none()
    if not teacher:
        await query.answer("Teacher not found", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton(text="\U0001f916 Generate with AI", callback_data="ai_hw_mode_generate")],
        [InlineKeyboardButton(text="\U0001f4cb Paste JSON", callback_data="ai_hw_mode_paste")],
        [InlineKeyboardButton(text="\U0001f4d6 Generate from Context", callback_data="ai_hw_mode_context")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="back_to_main")],
    ]

    await query.message.edit_text(
        text="\U0001f9e0 AI Homework Generator\n\nSelect a mode:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.SELECT_MODE)
    await state.update_data(teacher_id=teacher.id)


async def ai_hw_select_mode(query: CallbackQuery, state: FSMContext, session) -> None:
    mode = query.data.replace("ai_hw_mode_", "")
    if mode not in ("generate", "paste", "context"):
        await query.answer("Invalid mode", show_alert=True)
        return

    data = await state.get_data()
    teacher_id = data.get("teacher_id")

    if not teacher_id:
        result = await session.execute(select(Teacher).filter_by(telegram_id=query.from_user.id))
        teacher = result.scalar_one_or_none()
        if not teacher:
            await query.answer("Teacher not found", show_alert=True)
            await state.clear()
            return
        teacher_id = teacher.id

    await state.update_data(mode=mode)

    result = await session.execute(
        select(Student).where(Student.teacher_id == teacher_id).order_by(Student.name)
    )
    students = result.scalars().all()

    if not students:
        await query.message.edit_text(
            text="\u26a0\ufe0f No students found. Add a student first.",
            reply_markup=_build_back_cancel(),
        )
        return

    keyboard = [
        [InlineKeyboardButton(text=s.name, callback_data=f"ai_hw_student_{s.id}")]
        for s in students
    ]
    keyboard.append([InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="ai_hw_back")])

    await query.message.edit_text(
        text="\U0001f465 Select a student:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.SELECT_STUDENT)


async def ai_hw_select_student(query: CallbackQuery, state: FSMContext, session) -> None:
    student_id_str = query.data.replace("ai_hw_student_", "")
    if not student_id_str.isdigit():
        await query.answer("Invalid student", show_alert=True)
        return

    student_id = int(student_id_str)
    student = await session.get(Student, student_id)
    if not student:
        await query.answer("Student not found", show_alert=True)
        return

    await state.update_data(student_id=student_id, student_name=student.name)

    data = await state.get_data()
    mode = data.get("mode")

    if mode == "paste":
        prompt = (
            "You are an IT English teacher. Generate homework exercises that test "
            "language skills through IT contexts. Return ONLY valid JSON — no markdown, no explanations.\n\n"
            "TOPIC: [enter topic like \"Docker basics\"]\n"
            "LEVEL: A2 / B1 / B2\n\n"
            "JSON SCHEMA:\n"
            "{\n"
            '  "title": "Short homework title",\n'
            '  "level": "A2|B1|B2",\n'
            '  "topic": "IT topic",\n'
            '  "instructions": "Student-facing instructions",\n'
            '  "exercises": [\n'
            "    {\n"
            '      "type": "multiple_choice",\n'
            '      "language_goal": "e.g. Prepositions in IT",\n'
            '      "question": "...",\n'
            '      "options": ["A", "B", "C", "D"],\n'
            '      "correct_answer": "...",\n'
            '      "explanation": "..."\n'
            "    }\n"
            "  ]\n"
            "}\n\n"
            "SUPPORTED EXERCISE TYPES (use any mix, 3-10 total):\n"
            "1. multiple_choice — question + options + correct_answer + explanation\n"
            "2. true_false — question + correct_answer (boolean) + explanation\n"
            "3. select_all — question + options + correct_answers (indices) + explanation\n"
            "4. fill_in_the_gap — sentence + correct_answer + hint\n"
            "5. short_answer — question + sample_answer + useful_phrases[]\n"
            "6. order_items — instruction + items[] + correct_order[] (indices) + explanation\n"
            "7. synonyms_match — instruction + pairs[{word, synonym}] + distractors[] + explanation\n"
            "8. error_correction — incorrect_sentence + correction + hint + explanation\n"
            "9. word_formation — sentence_with_blank + base_word + correct_form + hint + explanation\n"
            "10. cloze_text — instruction + text_with_gaps + gaps[{correct_answer, hint}] + explanation\n"
            "11. reorder_words — instruction + scrambled_words[] + correct_order[] + correct_sentence + explanation\n\n"
            "Rules:\n"
            "- Test ENGLISH, not tech knowledge\n"
            "- Each exercise must have language_goal (what language point it tests)\n"
            "- Use clear, concise language suitable for B1 level\n"
            "- IT context throughout\n"
            "- JSON ONLY. No surrounding text."
        )

        text = (
            "\U0001f4cb <b>Paste JSON \u2014 External AI</b>\n\n"
            "<b>Steps:</b>\n"
            "1. Copy the prompt below \U0001f447\n"
            "2. Paste into ChatGPT, DeepSeek, Mistral, etc.\n"
            "3. Replace <code>[enter topic]</code> with your topic\n"
            "4. Paste the returned JSON below\n\n"
            "<pre>" + prompt.replace("<", "&lt;").replace(">", "&gt;") + "</pre>\n\n"
            "Send the JSON below, or /cancel to abandon."
        )

        await query.message.edit_text(
            text=text,
            reply_markup=_build_back_cancel(),
        )
        await state.set_state(AIHomeworkStates.WAITING_JSON)

    elif mode == "context":
        await query.message.edit_text(
            text="\U0001f4d6 Paste the lesson context or information below.\n"
            "The AI will use this to generate relevant exercises.\n\n"
            "Send /cancel to abandon.",
            reply_markup=_build_back_cancel(),
        )
        await state.set_state(AIHomeworkStates.PROVIDE_CONTEXT)

    else:
        await query.message.edit_text(
            text="\U0001f4cc Enter a topic for the homework (e.g. 'Docker basics', 'FastAPI debugging'):\n\n"
            "Send /cancel to abandon.",
            reply_markup=_build_back_cancel(),
        )
        await state.set_state(AIHomeworkStates.ENTER_TOPIC)


async def ai_hw_cancel(query: CallbackQuery, state: FSMContext, session) -> None:
    await state.clear()
    await query.message.edit_text(
        text="AI homework generation cancelled.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\u2b05\ufe0f Back to Menu", callback_data="back_to_main")],
        ]),
    )


async def ai_hw_back(query: CallbackQuery, state: FSMContext, session) -> None:
    current = await state.get_state()
    if current == AIHomeworkStates.SELECT_MODE:
        from bot.keyboards.main_menu import build_main_menu
        kb = await build_main_menu(query.from_user.id, session)
        await query.message.edit_text("Welcome! I'm your educational bot.", reply_markup=kb)
        await state.clear()
    elif current == AIHomeworkStates.SELECT_STUDENT:
        await ai_hw_start(query, state, session)
    elif current in (AIHomeworkStates.ENTER_TOPIC, AIHomeworkStates.PROVIDE_CONTEXT, AIHomeworkStates.WAITING_JSON):
        await ai_hw_select_mode(query, state, session)
    elif current in (AIHomeworkStates.SELECT_LEVEL, AIHomeworkStates.SELECT_FOCUS, AIHomeworkStates.ENTER_COUNT):
        data = await state.get_data()
        mode = data.get("mode", "generate")
        if mode == "context" and current == AIHomeworkStates.ENTER_COUNT:
            level_data = await state.get_data()
            if level_data.get("context"):
                await ai_hw_select_student(query, state, session)
            else:
                await ai_hw_select_student(query, state, session)
        else:
            await ai_hw_select_student(query, state, session)
    else:
        await ai_hw_start(query, state, session)
