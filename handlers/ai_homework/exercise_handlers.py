"""Exercise callback handlers — option, toggle, confirm"""
import logging
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from .exercise_common import _build_feedback, _show_feedback
from .exercise_display import _show_synonym_pair

logger = logging.getLogger(__name__)


async def ex_option(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data:
        await state.clear()
        await query.message.edit_text("Session expired. Please start again.")
        return
    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]
    results: list[dict] = data.get("results", [])

    opt_str = query.data.replace("ex_op_", "")
    if not opt_str.isdigit():
        return
    opt_idx = int(opt_str)
    ex = exercises[idx]
    ex_type = ex.get("type", "")

    if ex_type == "multiple_choice":
        options = ex.get("options", [])
        correct = ex.get("correct_answer", "")
        answer_label = options[opt_idx] if opt_idx < len(options) else "?"
        is_correct = answer_label == correct
        feedback = _build_feedback(is_correct, answer_label, correct, ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": answer_label})

    elif ex_type == "true_false":
        selected = opt_idx == 0
        is_correct = selected == ex.get("correct_answer", False)
        answer_label = "True" if selected else "False"
        correct_label = "True" if ex.get("correct_answer") else "False"
        feedback = _build_feedback(is_correct, answer_label, correct_label, ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": answer_label})

    elif ex_type in ("order_items", "ordering"):
        order_selected: list[int] = data.get("order_selected", [])
        if opt_idx in order_selected:
            await query.answer("Already selected", show_alert=True)
            return
        order_selected.append(opt_idx)
        items = ex.get("items", [])
        remaining = len(items) - len(order_selected)

        if remaining > 0:
            await state.update_data(order_selected=order_selected)
            selected_labels = " \u2192 ".join(items[i] for i in order_selected)
            progress = f"\U0001f4cd Exercise {idx + 1}/{len(exercises)}"
            await query.message.edit_text(
                text=f"{progress}\n\n<b>{ex.get('instruction', 'Order the items')}</b>\n\n"
                f"Selected: {selected_labels}\n\n"
                f"Tap <b>{remaining} more</b> in order:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=items[i], callback_data=f"ex_op_{i}")]
                    for i in range(len(items)) if i not in order_selected
                ] + [[InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")]]),
            )
            return

        is_correct = order_selected == ex.get("correct_order", [])
        selected_labels = " \u2192 ".join(items[i] for i in order_selected)
        correct_labels = " \u2192 ".join(items[i] for i in ex.get("correct_order", []))
        feedback = _build_feedback(is_correct, selected_labels, correct_labels, ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": selected_labels})

    elif ex_type == "synonyms_match":
        syn_options: list[str] = data.get("syn_options", [])
        syn_correct: str = data.get("syn_correct", "")
        pair_idx: int = data.get("syn_pair_idx", 0)
        syn_results: list[dict] = data.get("syn_pair_results", [])
        selected = syn_options[opt_idx] if opt_idx < len(syn_options) else ""
        is_correct = selected == syn_correct
        syn_results.append({"correct": is_correct, "selected": selected, "expected": syn_correct})
        await state.update_data(syn_pair_idx=pair_idx + 1, syn_pair_results=syn_results)
        await _show_synonym_pair(query, state)
        return

    elif ex_type == "reorder_words":
        order_selected: list[int] = data.get("order_selected", [])
        if opt_idx in order_selected:
            await query.answer("Already selected", show_alert=True)
            return
        order_selected.append(opt_idx)
        items = ex.get("words", ex.get("scrambled_words", []))
        remaining = len(items) - len(order_selected)

        if remaining > 0:
            await state.update_data(order_selected=order_selected)
            selected_labels = " ".join(items[i] for i in order_selected)
            progress = f"\U0001f4cd Exercise {idx + 1}/{len(exercises)}"
            await query.message.edit_text(
                text=f"{progress}\n\n<b>{ex.get('instruction', 'Reorder the words')}</b>\n\n"
                f"Your sentence so far: {selected_labels}\n\n"
                f"Tap <b>{remaining} more</b> words:",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=items[i], callback_data=f"ex_op_{i}")]
                    for i in range(len(items)) if i not in order_selected
                ] + [[InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")]]),
            )
            return

        selected_labels = " ".join(items[i] for i in order_selected)
        is_correct = order_selected == ex.get("correct_order", [])
        correct_sentence = ex.get("correct_sentence", ex.get("correct_answer", ""))
        feedback = _build_feedback(is_correct, selected_labels, correct_sentence, ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": selected_labels})

    else:
        return

    await state.update_data(results=results)
    await _show_feedback(query, state, feedback)


async def ex_toggle(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data:
        await state.clear()
        await query.message.edit_text("Session expired. Please start again.")
        return
    selected: list[int] = data.get("selected", [])
    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]

    opt_str = query.data.replace("ex_tg_", "")
    if not opt_str.isdigit():
        return
    opt_idx = int(opt_str)

    if opt_idx in selected:
        selected.remove(opt_idx)
    else:
        selected.append(opt_idx)

    await state.update_data(selected=selected)

    ex = exercises[idx]
    options = ex.get("options", [])
    keyboard = [
        [InlineKeyboardButton(
            text=f"\u2611 {opt}" if i in selected else f"\u2610 {opt}",
            callback_data=f"ex_tg_{i}",
        )]
        for i, opt in enumerate(options)
    ]
    keyboard.append([InlineKeyboardButton(text="\u2705 Confirm", callback_data="ex_cf")])
    keyboard.append([InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")])

    await query.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    await query.answer(f"{len(selected)} selected")


async def ex_confirm(query: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data:
        await state.clear()
        await query.message.edit_text("Session expired. Please start again.")
        return
    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]
    results: list[dict] = data.get("results", [])
    selected: list[int] = sorted(data.get("selected", []))
    ex = exercises[idx]

    correct = sorted(ex.get("correct_answers", []))
    is_correct = selected == correct
    answer_labels = ", ".join(ex.get("options", [])[i] for i in selected) if selected else "(none)"
    correct_labels = ", ".join(ex.get("options", [])[i] for i in correct) if correct else "(none)"
    feedback = _build_feedback(is_correct, answer_labels, correct_labels, ex.get("explanation", ""))

    results.append({"idx": idx, "correct": is_correct, "answer": answer_labels})
    await state.update_data(results=results)
    await _show_feedback(query, state, feedback)
