"""Teacher AI homework generation flow — topic, level, focus, count, generate, preview"""
import logging
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from models import Student
from bot.utils.helpers import sanitize_input
from handlers.ai_homework.teacher_states import AIHomeworkStates
from handlers.ai_homework.teacher import _generator, _build_back_cancel

logger = logging.getLogger(__name__)


async def ai_hw_enter_topic(message: Message, state: FSMContext, session) -> None:
    topic = sanitize_input(message.text)
    if not topic:
        await message.answer("Topic cannot be empty.")
        return

    await state.update_data(topic=topic)

    keyboard = [
        [InlineKeyboardButton(text="A2 - Elementary", callback_data="ai_hw_level_A2")],
        [InlineKeyboardButton(text="B1 - Intermediate", callback_data="ai_hw_level_B1")],
        [InlineKeyboardButton(text="B2 - Upper Intermediate", callback_data="ai_hw_level_B2")],
        [InlineKeyboardButton(text="C1 - Advanced", callback_data="ai_hw_level_C1")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="ai_hw_back")],
    ]

    await message.answer(
        text="\U0001f4da Select the difficulty level:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.SELECT_LEVEL)


async def ai_hw_select_level(query: CallbackQuery, state: FSMContext, session) -> None:
    level = query.data.replace("ai_hw_level_", "")
    if level not in ("A2", "B1", "B2", "C1"):
        await query.answer("Invalid level", show_alert=True)
        return

    await state.update_data(level=level)

    keyboard = [
        [InlineKeyboardButton(text="Vocabulary", callback_data="ai_hw_focus_vocabulary")],
        [InlineKeyboardButton(text="Grammar", callback_data="ai_hw_focus_grammar")],
        [InlineKeyboardButton(text="Speaking", callback_data="ai_hw_focus_speaking")],
        [InlineKeyboardButton(text="Reading", callback_data="ai_hw_focus_reading")],
        [InlineKeyboardButton(text="Mixed", callback_data="ai_hw_focus_mixed")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="ai_hw_back")],
    ]

    await query.message.edit_text(
        text="\U0001f3af Select the focus area:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.SELECT_FOCUS)


async def ai_hw_select_focus(query: CallbackQuery, state: FSMContext, session) -> None:
    focus = query.data.replace("ai_hw_focus_", "")
    if focus not in ("vocabulary", "grammar", "speaking", "reading", "mixed"):
        await query.answer("Invalid focus", show_alert=True)
        return

    await state.update_data(focus=focus)

    keyboard = [
        [InlineKeyboardButton(text="3", callback_data="ai_hw_count_3"),
         InlineKeyboardButton(text="4", callback_data="ai_hw_count_4"),
         InlineKeyboardButton(text="5", callback_data="ai_hw_count_5"),
         InlineKeyboardButton(text="6", callback_data="ai_hw_count_6")],
        [InlineKeyboardButton(text="7", callback_data="ai_hw_count_7"),
         InlineKeyboardButton(text="8", callback_data="ai_hw_count_8"),
         InlineKeyboardButton(text="9", callback_data="ai_hw_count_9"),
         InlineKeyboardButton(text="10", callback_data="ai_hw_count_10")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back", callback_data="ai_hw_back")],
    ]

    await query.message.edit_text(
        text="\U0001f522 Select the number of exercises:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.ENTER_COUNT)


async def ai_hw_on_count_selected(query: CallbackQuery, state: FSMContext, session) -> None:
    count_str = query.data.replace("ai_hw_count_", "")
    if not count_str.isdigit():
        await query.answer("Invalid selection", show_alert=True)
        return
    count = int(count_str)
    await state.update_data(count=count)
    await _run_generation(query, state)


async def ai_hw_provide_context(message: Message, state: FSMContext, session) -> None:
    context = sanitize_input(message.text)
    if not context:
        await message.answer("Context cannot be empty.")
        return

    await state.update_data(context=context)

    await message.answer(
        text="\U0001f4cc Enter a topic for the homework (e.g. 'Docker basics', 'FastAPI debugging'):\n\n"
        "Send /cancel to abandon.",
        reply_markup=_build_back_cancel(),
    )
    await state.set_state(AIHomeworkStates.ENTER_TOPIC)


async def ai_hw_paste_json(message: Message, state: FSMContext, session) -> None:
    raw_json = message.text.strip()

    result = await _generator.generate_from_json(raw_json)
    if not result.success:
        error_text = (result.error or "")[:3500]
        await message.answer(
            text=f"\u274c {error_text}\n\nPlease fix the JSON and send it again, or /cancel.",
        )
        return

    await state.update_data(
        raw_json=result.raw_json,
        pack_json=result.pack.model_dump_json(indent=2),
        title=result.pack.title,
        level=result.pack.level,
        topic=result.pack.topic,
        instructions=result.pack.instructions,
    )

    await _show_preview(message, state, result)


async def _run_generation(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    topic = data.get("topic", "IT English")
    level = data.get("level", "B1")
    focus = data.get("focus", "mixed")
    count = data.get("count", 5)
    context = data.get("context")

    sent = await query.message.answer("\u23f3 Generating homework... Please wait.")

    result = await _generator.generate(topic, level, focus, count, context)

    if not result.success:
        await sent.edit_text(
            text=f"\u274c {result.error}",
        )
        return

    await state.update_data(
        raw_json=result.raw_json,
        pack_json=result.pack.model_dump_json(indent=2),
        title=result.pack.title,
        level=result.pack.level,
        topic=result.pack.topic,
        instructions=result.pack.instructions,
    )

    await sent.delete()
    await _show_preview_from_query(query, state, result)


async def ai_hw_generate_callback(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    topic = data.get("topic", "IT English")
    level = data.get("level", "B1")
    focus = data.get("focus", "mixed")
    count = data.get("count", 5)
    context = data.get("context")

    sent = await query.message.edit_text("\u23f3 Generating homework... Please wait.")

    result = await _generator.generate(topic, level, focus, count, context)

    if not result.success:
        await sent.edit_text(
            text=f"\u274c {result.error}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\u2b05\ufe0f Back to Menu", callback_data="ai_hw_back")],
                [InlineKeyboardButton(text="\u274c Cancel", callback_data="ai_hw_cancel")],
            ]),
        )
        return

    await state.update_data(
        raw_json=result.raw_json,
        pack_json=result.pack.model_dump_json(indent=2),
        title=result.pack.title,
        level=result.pack.level,
        topic=result.pack.topic,
        instructions=result.pack.instructions,
    )

    await _show_preview_from_query(query, state, result)


async def _show_preview(message: Message, state: FSMContext, result) -> None:
    formatted = _generator.format_for_student(result.pack)
    preview_text = f"\U0001f9e0 <b>Homework Preview</b>\n\n{formatted}"

    keyboard = [
        [InlineKeyboardButton(text="\u2705 Approve & Send", callback_data="ai_hw_approve")],
        [InlineKeyboardButton(text="\U0001f504 Regenerate", callback_data="ai_hw_regenerate")],
        [InlineKeyboardButton(text="\u270f\ufe0f Edit Manually", callback_data="ai_hw_edit")],
        [InlineKeyboardButton(text="\u274c Cancel", callback_data="ai_hw_cancel")],
    ]

    await message.answer(
        text=preview_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.PREVIEW)


async def _show_preview_from_query(query: CallbackQuery, state: FSMContext, result) -> None:
    formatted = _generator.format_for_student(result.pack)
    preview_text = f"\U0001f9e0 <b>Homework Preview</b>\n\n{formatted}"

    keyboard = [
        [InlineKeyboardButton(text="\u2705 Approve & Send", callback_data="ai_hw_approve")],
        [InlineKeyboardButton(text="\U0001f504 Regenerate", callback_data="ai_hw_regenerate")],
        [InlineKeyboardButton(text="\u270f\ufe0f Edit Manually", callback_data="ai_hw_edit")],
        [InlineKeyboardButton(text="\u274c Cancel", callback_data="ai_hw_cancel")],
    ]

    await query.message.edit_text(
        text=preview_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
    )
    await state.set_state(AIHomeworkStates.PREVIEW)


async def ai_hw_regenerate(query: CallbackQuery, state: FSMContext, session) -> None:
    data = await state.get_data()
    if data.get("mode") == "paste":
        await query.message.edit_text(
            text="Please paste the JSON again:",
            reply_markup=_build_back_cancel(),
        )
        await state.set_state(AIHomeworkStates.WAITING_JSON)
        return

    sent = await query.message.edit_text("\u23f3 Regenerating homework...")
    await _run_generation_from_callback(query, state, sent)


async def _run_generation_from_callback(query: CallbackQuery, state: FSMContext, sent: Message) -> None:
    data = await state.get_data()
    topic = data.get("topic", "IT English")
    level = data.get("level", "B1")
    focus = data.get("focus", "mixed")
    count = data.get("count", 5)
    context = data.get("context")

    result = await _generator.generate(topic, level, focus, count, context)

    if not result.success:
        await sent.edit_text(
            text=f"\u274c {result.error}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f504 Try Again", callback_data="ai_hw_regenerate")],
                [InlineKeyboardButton(text="\u274c Cancel", callback_data="ai_hw_cancel")],
            ]),
        )
        return

    await state.update_data(
        raw_json=result.raw_json,
        pack_json=result.pack.model_dump_json(indent=2),
        title=result.pack.title,
        level=result.pack.level,
        topic=result.pack.topic,
        instructions=result.pack.instructions,
    )

    await _show_preview_from_query(query, state, result)
