"""Student exercise answer processing — text answers, results, AI evaluation"""
import json
import logging
from datetime import datetime, timezone

from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from models import HomeworkAttempt
from bot.utils.helpers import sanitize_input
from ai_homework.prompts import EVALUATION_PROMPT
from ai_homework.providers import get_provider_chain
from .exercise_common import _back_to_homework_kb, _build_feedback, _show_feedback, _show_feedback_from_message

logger = logging.getLogger(__name__)


async def evaluate_short_answer(question: str, sample_answer: str, user_answer: str, language_goal: str = "") -> dict:
    providers = get_provider_chain()
    if not providers:
        return {"correct": None, "score": 0, "explanation": ""}

    prompt = EVALUATION_PROMPT.format(
        language_goal=language_goal or "general English",
        question=question,
        sample_answer=sample_answer,
        user_answer=user_answer,
    )

    for provider in providers:
        text, error = await provider.generate(prompt, temperature=0.1)
        if error:
            logger.warning("Evaluation failed for %s: %s", provider.name, error)
            continue
        try:
            result = json.loads(text.strip())
            if isinstance(result.get("correct"), bool) and isinstance(result.get("score"), (int, float)):
                return result
        except (json.JSONDecodeError, TypeError):
            continue

    return {"correct": None, "score": 0, "explanation": ""}


async def ex_text_answer(message: Message, state: FSMContext, session) -> None:
    data = await state.get_data()
    if "exercises" not in data or "current_idx" not in data:
        await state.clear()
        await message.answer("Session expired. Please start again.")
        return
    exercises: list[dict] = data["exercises"]
    idx: int = data["current_idx"]
    results: list[dict] = data.get("results", [])
    ex = exercises[idx]
    ex_type = ex.get("type", "")
    user_answer = sanitize_input(message.text.strip())
    if len(user_answer) > 2000:
        await message.answer("Answer too long (max 2000 chars). Please try again.")
        return

    if ex_type in ("fill_blank", "fill_in_the_gap"):
        expected = ex.get("correct_answer", "").strip().lower()
        is_correct = user_answer.lower() == expected
        feedback = _build_feedback(is_correct, user_answer, ex.get("correct_answer", ""), ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": user_answer})

    elif ex_type == "short_answer":
        waiting = await message.answer("\u23f3 Evaluating your answer...")
        evaluation = await evaluate_short_answer(
            question=ex.get("question", ""),
            sample_answer=ex.get("sample_answer", ""),
            user_answer=user_answer,
            language_goal=ex.get("language_goal", ""),
        )
        await waiting.delete()
        is_correct = evaluation.get("correct")
        score = evaluation.get("score", 0)
        explanation = evaluation.get("explanation", "")

        if is_correct is None:
            text = (
                f"\U0001f4ac <b>Your answer:</b> {user_answer}\n\n"
                f"\U0001f4d6 <b>Sample answer:</b> {ex.get('sample_answer', '')}\n\n"
                f"<i>Useful phrases: {', '.join(ex.get('useful_phrases', []))}</i>\n\n"
            )
            results.append({"idx": idx, "correct": None, "score": score, "answer": user_answer})
            await state.update_data(results=results)
            await message.answer(
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="\u23ed\ufe0f Next", callback_data="ex_nx")],
                    [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
                ]),
            )
            return
        else:
            icon = "\u2705" if is_correct else "\u274c"
            text = (
                f"{icon} <b>{'Correct!' if is_correct else 'Not quite'}</b>\n\n"
                f"\U0001f4ac <b>Your answer:</b> {user_answer}\n\n"
                f"\U0001f4d6 <b>Sample answer:</b> {ex.get('sample_answer', '')}\n\n"
                f"\U0001f522 <b>Score: {score}/100</b>\n"
                f"{explanation}\n\n"
            )
            if ex.get("useful_phrases"):
                text += f"<i>Useful phrases: {', '.join(ex['useful_phrases'])}</i>\n\n"
            lang_focus = ex.get("language_goal", "")
            if lang_focus:
                text += f"\U0001f3f7\ufe0f <i>Language focus: {lang_focus}</i>\n\n"
            results.append({"idx": idx, "correct": is_correct, "score": score, "answer": user_answer})
            await state.update_data(results=results)
            await message.answer(
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="\u23ed\ufe0f Next", callback_data="ex_nx")],
                    [InlineKeyboardButton(text="\u274c End Session", callback_data="ex_en")],
                ]),
            )
            return

    elif ex_type == "error_correction":
        expected = ex.get("correction", ex.get("correct_answer", "")).strip().lower()
        is_correct = user_answer.lower() == expected
        feedback = _build_feedback(is_correct, user_answer, ex.get("correction", ex.get("correct_answer", "")), ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": user_answer})

    elif ex_type == "word_formation":
        expected = ex.get("correct_form", ex.get("correct_answer", "")).strip().lower()
        is_correct = user_answer.lower() == expected
        feedback = _build_feedback(is_correct, user_answer, ex.get("correct_form", ex.get("correct_answer", "")), ex.get("explanation", ""))
        results.append({"idx": idx, "correct": is_correct, "answer": user_answer})

    elif ex_type == "cloze_text":
        gap_idx: int = data.get("cloze_gap_idx", 0)
        gaps = ex.get("gaps", [])
        cloze_results: list[dict] = data.get("cloze_gap_results", [])
        if gap_idx < len(gaps):
            gap = gaps[gap_idx]
            expected = gap.get("correct_answer", "").strip().lower()
            is_correct = user_answer.lower() == expected
            cloze_results.append({"correct": is_correct, "answer": user_answer, "expected": gap.get("correct_answer", "")})
            feedback_line = _build_feedback(is_correct, user_answer, gap.get("correct_answer", ""), "")
            await state.update_data(cloze_gap_idx=gap_idx + 1, cloze_gap_results=cloze_results)
            await message.answer(text=feedback_line)
            from .exercise_display import _show_cloze_gap
            await _show_cloze_gap(message, state)
        return

    else:
        return

    await state.update_data(results=results)
    await _show_feedback_from_message(message, state, feedback)


async def _show_results(query_or_msg, state: FSMContext, session=None) -> None:
    data = await state.get_data()
    if "results" not in data or "total" not in data or "homework_id" not in data:
        await state.clear()
        msg = "Session expired. Please start again."
        if isinstance(query_or_msg, CallbackQuery):
            await query_or_msg.message.edit_text(msg)
        else:
            await query_or_msg.answer(msg)
        return
    results: list[dict] = data["results"]
    total: int = data["total"]
    hw_id: int = data["homework_id"]
    student_id: int | None = data.get("student_id")

    correct_count = sum(1 for r in results if r.get("correct") is True)
    incorrect_count = sum(1 for r in results if r.get("correct") is False)
    ungraded = sum(1 for r in results if r.get("correct") is None)

    weighted_sum = 0
    for r in results:
        if "score" in r and isinstance(r.get("score"), (int, float)):
            weighted_sum += r["score"] / 100
        elif r.get("correct") is True:
            weighted_sum += 1

    score_pct = round(weighted_sum / total * 100) if total > 0 else 0

    await _save_attempt(hw_id, student_id, results, correct_count, total, session)

    lines = [
        "\U0001f4ca <b>Exercise Results</b>",
        "",
        f"Total exercises: {total}",
        f"\u2705 Correct: {correct_count}",
        f"\u274c Incorrect: {incorrect_count}",
    ]
    if ungraded:
        lines.append(f"\U0001f4ac Self-assessed: {ungraded}")
    lines.append("")
    lines.append(f"<b>Score: {score_pct}%</b>")

    if score_pct == 100:
        lines.append("\n\U0001f389 Perfect! Great job!")
    elif score_pct >= 70:
        lines.append("\n\U0001f44d Good work! Review the ones you missed.")
    elif score_pct >= 40:
        lines.append("\n\U0001f4aa Keep practicing! Review the explanations.")
    else:
        lines.append("\n\U0001f4da Review the material and try again!")

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="\U0001f504 Try Again", callback_data="ex_rs")],
        [InlineKeyboardButton(text="\u2b05\ufe0f Back to Homework", callback_data=f"view_hw_{hw_id}")],
    ])

    if isinstance(query_or_msg, CallbackQuery):
        await query_or_msg.message.edit_text(text="\n".join(lines), reply_markup=keyboard)
    else:
        await query_or_msg.answer(text="\n".join(lines), reply_markup=keyboard)


async def _save_attempt(
    hw_id: int, student_id: int | None,
    results: list[dict], score: int, total: int,
    session,
) -> None:
    if not student_id or not session:
        return
    try:
        attempt = HomeworkAttempt(
            homework_id=hw_id,
            student_id=student_id,
            results=json.dumps(results),
            score=score,
            total=total,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(attempt)
        await session.commit()
        logger.info("Saved HomeworkAttempt for hw=%d student=%d score=%d/%d", hw_id, student_id, score, total)
    except Exception as e:
        logger.error("Failed to save HomeworkAttempt: %s", e)
