"""Display functions for interactive exercise session"""
import logging
import random
from typing import Any

from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from .exercise_common import _back_to_homework_kb, _build_feedback, _show_feedback

logger = logging.getLogger(__name__)


def _next_or_results_kb(idx: int, total: int) -> InlineKeyboardMarkup:
    is_last = idx + 1 >= total
    next_label = "\U0001f3af See Results" if is_last else "\u23ed\ufe0f Next"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=next_label, callback_data="ex_nx")],
        [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
    ])


async def _show_exercise(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data or "student_id" not in data:
        await state.clear()
        await query.message.edit_text("Session expired. Please start again.")
        return

    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]
    total: int = data.get("total", len(exercises))
    ex = exercises[idx]
    ex_type = ex.get("type", "unknown")
    progress = f"\U0001f4cd Exercise {idx + 1}/{total}"
    lang_goal = ex.get("language_goal", "")
    goal_line = f"\U0001f3f7\ufe0f <i>{lang_goal}</i>" if lang_goal else ""
    q = ex.get("question", "")

    if ex_type == "synonyms_match":
        await state.update_data(syn_pair_idx=0, syn_pair_results=[])
        await _show_synonym_pair(query, state)
        return

    if ex_type == "cloze_text":
        await state.update_data(cloze_gap_idx=0, cloze_gap_results=[])
        await _show_cloze_gap(query, state)
        return

    if ex_type == "multiple_choice":
        text = f"{progress}\n{goal_line}\n\n<b>{q}</b>\n"
        keyboard = [
            [InlineKeyboardButton(text=opt, callback_data=f"ex_op_{i}")]
            for i, opt in enumerate(ex.get("options", []))
        ]
        keyboard.append([InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")])

    elif ex_type == "true_false":
        text = f"{progress}\n{goal_line}\n\n<b>{q}</b>\n\nChoose True or False:"
        keyboard = [
            [InlineKeyboardButton(text="\u2705 True", callback_data="ex_op_0")],
            [InlineKeyboardButton(text="\u274c False", callback_data="ex_op_1")],
            [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
        ]

    elif ex_type == "select_all":
        options = ex.get("options", [])
        text = f"{progress}\n{goal_line}\n\n<b>{q}</b>\n\nSelect <b>all</b> correct options, then confirm:"
        keyboard = [
            [InlineKeyboardButton(text=f"\u2610 {opt}", callback_data=f"ex_tg_{i}")]
            for i, opt in enumerate(options)
        ]
        keyboard.append([InlineKeyboardButton(text="\u2705 Confirm", callback_data="ex_cf")])
        keyboard.append([InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")])
        await state.update_data(selected=[])

    elif ex_type in ("fill_blank", "fill_in_the_gap"):
        text = (
            f"{progress}\n{goal_line}\n\n<b>Fill in the gap:</b>\n\n"
            f"{ex.get('sentence', '?')}\n\n"
            f"<i>Hint: {ex.get('hint', '')}</i>"
            f"\n\nType your answer below."
        )
        keyboard = [
            [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
            *_back_to_homework_kb(data.get("homework_id", 0)),
        ]

    elif ex_type == "short_answer":
        text = (
            f"{progress}\n{goal_line}\n\n<b>Short Answer:</b>\n\n"
            f"{q}\n\n"
            f"Type your answer below."
        )
        keyboard = [
            [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
            *_back_to_homework_kb(data.get("homework_id", 0)),
        ]

    elif ex_type in ("order_items", "ordering"):
        items = ex.get("items", [])
        text = f"{progress}\n{goal_line}\n\n<b>{ex.get('instruction', 'Order the items')}</b>\n\nTap items <b>in the correct order</b>:"
        keyboard = [
            [InlineKeyboardButton(text=item, callback_data=f"ex_op_{i}")]
            for i, item in enumerate(items)
        ]
        keyboard.append([InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")])
        await state.update_data(order_selected=[])

    elif ex_type in ("matching",):
        text = (
            f"{progress}\n{goal_line}\n\n<b>{ex.get('instruction', 'Match the items')}</b>\n\n"
        )
        left = ex.get("left_items", [])
        right = ex.get("right_items", [])
        for l, r in zip(left, right):
            text += f"\U0001f539 {l}  \u2194  {r}\n"
        text += "\nPress <b>Next</b> to continue."
        await query.message.edit_text(text=text, reply_markup=_next_or_results_kb(idx, total))
        return

    elif ex_type in ("classification",):
        text = (
            f"{progress}\n{goal_line}\n\n<b>{ex.get('instruction', 'Classify the items')}</b>\n\n"
            f"Items: {', '.join(ex.get('items', []))}\n"
            f"Categories: {', '.join(ex.get('categories', []))}\n\n"
            f"Press <b>Next</b> to continue."
        )
        await query.message.edit_text(text=text, reply_markup=_next_or_results_kb(idx, total))
        return

    elif ex_type == "error_correction":
        text = (
            f"{progress}\n{goal_line}\n\n<b>Error Correction:</b>\n\n"
            f"{ex.get('sentence', ex.get('incorrect_sentence', '?'))}\n\n"
            f"<i>Hint: {ex.get('hint', '')}</i>"
            f"\n\nType the <b>corrected</b> sentence below."
        )
        keyboard = [
            [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
            *_back_to_homework_kb(data.get("homework_id", 0)),
        ]

    elif ex_type == "word_formation":
        text = (
            f"{progress}\n{goal_line}\n\n<b>Word Formation:</b>\n\n"
            f"{ex.get('sentence', ex.get('sentence_with_blank', '?'))}\n\n"
            f"Base word: <b>{ex.get('base_word', '')}</b>\n"
            f"<i>Hint: {ex.get('hint', '')}</i>"
            f"\n\nType the correct form of the word."
        )
        keyboard = [
            [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
            *_back_to_homework_kb(data.get("homework_id", 0)),
        ]

    elif ex_type == "reorder_words":
        items = ex.get("words", ex.get("scrambled_words", []))
        text = f"{progress}\n{goal_line}\n\n<b>{ex.get('instruction', 'Reorder the words')}</b>\n\nTap words <b>in the correct order</b>:"
        keyboard = [
            [InlineKeyboardButton(text=item, callback_data=f"ex_op_{i}")]
            for i, item in enumerate(items)
        ]
        keyboard.append([InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")])
        await state.update_data(order_selected=[])

    else:
        text = f"{progress}\n\nUnknown exercise type: {ex_type}"
        keyboard = [[InlineKeyboardButton(text="\u23ed\ufe0f Next", callback_data="ex_nx")]]

    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


async def _show_synonym_pair(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data:
        await state.clear()
        await query.message.edit_text("Session expired. Please start again.")
        return
    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]
    total: int = data["total"]
    ex = exercises[idx]
    pair_idx: int = data.get("syn_pair_idx", 0)
    pairs = ex.get("pairs", [])
    distractors = ex.get("distractors", [])

    if pair_idx >= len(pairs):
        syn_results: list[dict] = data.get("syn_pair_results", [])
        correct_count = sum(1 for r in syn_results if r.get("correct"))
        total_pairs = len(pairs)
        feedback_lines = [
            f"\U0001f4a1 Synonyms Match completed: {correct_count}/{total_pairs} correct",
        ]
        if ex.get("explanation"):
            feedback_lines.append(f"\n\U0001f4dd {ex['explanation']}")
        results: list[dict] = data.get("results", [])
        results.append({"idx": idx, "correct": correct_count == total_pairs, "answer": f"{correct_count}/{total_pairs}"})
        await state.update_data(results=results)
        await _show_feedback(query, state, "\n".join(feedback_lines))
        return

    pair = pairs[pair_idx]
    word = pair.get("word", "?")
    correct_syn = pair.get("synonym", "")
    options = [correct_syn] + [d for d in distractors if d != correct_syn][:3]
    random.shuffle(options)

    progress = f"\U0001f4cd Exercise {idx + 1}/{total}"
    lang_goal = ex.get("language_goal", "")
    goal_line = f"\U0001f3f7\ufe0f <i>{lang_goal}</i>" if lang_goal else ""

    text = f"{progress}\n{goal_line}\n\n<b>Synonyms Match ({pair_idx + 1}/{len(pairs)})</b>\n\nChoose the synonym of: <b>{word}</b>"
    keyboard = [
        [InlineKeyboardButton(text=opt, callback_data=f"ex_op_{i}")]
        for i, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")])

    await state.update_data(syn_options=options, syn_correct=correct_syn)
    await query.message.edit_text(text=text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))


async def _show_cloze_gap(query_or_msg, state: FSMContext) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data:
        await state.clear()
        msg = "Session expired. Please start again."
        if isinstance(query_or_msg, CallbackQuery):
            await query_or_msg.message.edit_text(msg)
        else:
            await query_or_msg.answer(msg)
        return
    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]
    total: int = data["total"]
    ex = exercises[idx]
    gap_idx: int = data.get("cloze_gap_idx", 0)
    gaps = ex.get("gaps", [])

    if gap_idx >= len(gaps):
        cloze_results: list[dict] = data.get("cloze_gap_results", [])
        correct_count = sum(1 for r in cloze_results if r.get("correct"))
        total_gaps = len(gaps)
        feedback_lines = [
            f"\U0001f4d6 Cloze Text completed: {correct_count}/{total_gaps} gaps correct",
        ]
        if ex.get("explanation"):
            feedback_lines.append(f"\n\U0001f4dd {ex['explanation']}")
        results: list[dict] = data.get("results", [])
        results.append({"idx": idx, "correct": correct_count == total_gaps, "answer": f"{correct_count}/{total_gaps}"})
        await state.update_data(results=results)
        await _show_feedback(query_or_msg, state, "\n".join(feedback_lines))
        return

    gap = gaps[gap_idx]
    progress = f"\U0001f4cd Exercise {idx + 1}/{total}"
    lang_goal = ex.get("language_goal", "")
    goal_line = f"\U0001f3f7\ufe0f <i>{lang_goal}</i>" if lang_goal else ""

    text = (
        f"{progress}\n{goal_line}\n\n<b>Cloze Text ({gap_idx + 1}/{len(gaps)})</b>\n\n"
        f"{ex.get('text_with_gaps', '')}\n\n"
        f"<i>Hint: {gap.get('hint', '')}</i>"
        f"\n\nType the missing word."
    )
    keyboard = [
        [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
        *_back_to_homework_kb(data.get("homework_id", 0)),
    ]

    reply = InlineKeyboardMarkup(inline_keyboard=keyboard)
    if isinstance(query_or_msg, CallbackQuery):
        await query_or_msg.message.edit_text(text=text, reply_markup=reply)
    else:
        await query_or_msg.answer(text=text, reply_markup=reply)
