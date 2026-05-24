"""AI Homework Generator - orchestrates provider chain, validation, and formatting"""
import json
import time
import logging
from typing import Optional
from pydantic import ValidationError
from ai_homework.schema import HomeworkPack
from ai_homework.prompts import SYSTEM_PROMPT, build_user_prompt, REPAIR_PROMPT
from ai_homework.providers.base import AIProvider
from ai_homework.providers import get_provider_chain
from bot.utils.helpers import sanitize_json_string

logger = logging.getLogger(__name__)


class GenerateResult:
    def __init__(
        self,
        success: bool,
        pack: Optional[HomeworkPack] = None,
        error: Optional[str] = None,
        provider_name: Optional[str] = None,
        raw_json: Optional[str] = None,
    ):
        self.success = success
        self.pack = pack
        self.error = error
        self.provider_name = provider_name
        self.raw_json = raw_json


class AIHomeworkGenerator:
    def __init__(self):
        self._providers: list[AIProvider] = get_provider_chain()

    def validate_json(self, raw: str) -> tuple[Optional[HomeworkPack], Optional[str]]:
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.splitlines()
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines).strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            return None, f"Invalid JSON: {e}"

        try:
            pack = HomeworkPack(**data)
            return pack, None
        except ValidationError as e:
            errors = e.errors()
            summary = "; ".join(
                f"{'.'.join(str(p) for p in err.get('loc', ()))}: {err.get('msg', '')}"
                for err in errors[:3]
            )
            if len(errors) > 3:
                summary += f" (+{len(errors) - 3} more)"
            return None, f"Schema validation failed: {summary}"

    def format_for_student(self, pack: HomeworkPack) -> str:
        lines = [f"\U0001f4dd {pack.title}", f"Level: {pack.level}  |  Topic: {pack.topic}", "", pack.instructions, ""]

        for i, ex in enumerate(pack.exercises, 1):
            lines.append(f"{'=' * 30}")
            goal = getattr(ex, "language_goal", None)
            goal_line = f"  \U0001f3f7 Language focus: {goal}" if goal else ""

            if ex.type == "multiple_choice":
                lines.append(f"Exercise {i} \U0001f520 Multiple Choice{goal_line}")
                lines.append(f"Q: {ex.question}")
                for j, opt in enumerate(ex.options, 1):
                    lines.append(f"   {j}. {opt}")
                lines.append(f"")
                lines.append(f"(Answer: {ex.correct_answer})")
            elif ex.type == "true_false":
                lines.append(f"Exercise {i} \U0001f4ac True or False{goal_line}")
                lines.append(f"Q: {ex.question}")
                lines.append(f"")
                text = "True" if ex.correct_answer else "False"
                lines.append(f"(Answer: {text})")
            elif ex.type == "select_all":
                lines.append(f"Exercise {i} \U0001f4dd Select All{goal_line}")
                lines.append(f"Q: {ex.question}")
                for j, opt in enumerate(ex.options, 1):
                    lines.append(f"   {j}. {opt}")
                lines.append(f"")
                correct = [ex.options[j] for j in ex.correct_answers]
                lines.append(f"(Answers: {', '.join(correct)})")
            elif ex.type == "fill_in_the_gap":
                lines.append(f"Exercise {i} \U00002753 Fill in the Gap{goal_line}")
                lines.append(f"{ex.sentence}")
                lines.append(f"")
                lines.append(f"Hint: {ex.hint}")
            elif ex.type == "short_answer":
                lines.append(f"Exercise {i} \U0001f4ac Short Answer{goal_line}")
                lines.append(f"Q: {ex.question}")
                lines.append(f"")
                lines.append(f"Useful phrases: {', '.join(ex.useful_phrases)}")
            elif ex.type == "order_items":
                lines.append(f"Exercise {i} \U0001f500 Order Items{goal_line}")
                lines.append(f"{ex.instruction}")
                for j, item in enumerate(ex.items, 1):
                    lines.append(f"   {j}. {item}")
            elif ex.type == "synonyms_match":
                lines.append(f"Exercise {i} \U0001f4a1 Synonyms Match{goal_line}")
                lines.append(f"{ex.instruction}")
                for pair in ex.pairs:
                    lines.append(f"   \U0001f517 {pair.word} \u2194 {pair.synonym}")
                lines.append(f"")
                lines.append(f"Distractors: {', '.join(ex.distractors)}")
            elif ex.type == "error_correction":
                lines.append(f"Exercise {i} \U0001f527 Error Correction{goal_line}")
                lines.append(f"Find the error: {ex.incorrect_sentence}")
                lines.append(f"")
                lines.append(f"Hint: {ex.hint}")
            elif ex.type == "word_formation":
                lines.append(f"Exercise {i} \U0001f4a1 Word Formation{goal_line}")
                lines.append(f"{ex.sentence_with_blank}")
                lines.append(f"")
                lines.append(f"Base word: {ex.base_word}")
            elif ex.type == "cloze_text":
                lines.append(f"Exercise {i} \U0001f4d6 Cloze Text{goal_line}")
                lines.append(f"{ex.instruction}")
                lines.append(f"")
                lines.append(f"{ex.text_with_gaps}")
            elif ex.type == "reorder_words":
                lines.append(f"Exercise {i} \U0001f500 Reorder Words{goal_line}")
                lines.append(f"{ex.instruction}")
                for j, w in enumerate(ex.scrambled_words, 1):
                    lines.append(f"   {j}. {w}")

        return "\n".join(lines)

    async def generate(
        self,
        topic: str,
        level: str,
        focus: str,
        count: int,
        context: Optional[str] = None,
    ) -> GenerateResult:
        if not self._providers:
            return GenerateResult(
                success=False,
                error="No AI providers configured. Add API keys in .env or paste homework manually.",
            )

        user_prompt = build_user_prompt(topic, level, focus, count, context)
        full_prompt = f"{SYSTEM_PROMPT}\n\n{user_prompt}"

        for provider in self._providers:
            result = await self._try_provider(provider, full_prompt)
            if result.success:
                return result
            logger.warning(
                "provider=%s failed, trying next provider. error=%s",
                provider.name, result.error,
            )

        return GenerateResult(
            success=False,
            error="All AI providers failed. You can paste your own JSON using the 'Paste JSON' option, or create homework manually.",
        )

    async def _try_provider(
        self,
        provider: AIProvider,
        prompt: str,
    ) -> GenerateResult:
        logger.info("Attempting generation with %s (%s)", provider.name, provider.model_name)
        text, error = await provider.generate(prompt)

        if error:
            return GenerateResult(success=False, error=f"{provider.name}: {error}")

        pack, validation_error = self.validate_json(text)
        if pack:
            sanitized_raw = sanitize_json_string(text)
            sanitized_pack, _ = self.validate_json(sanitized_raw)
            return GenerateResult(
                success=True,
                pack=sanitized_pack or pack,
                provider_name=provider.name,
                raw_json=sanitized_raw,
            )

        logger.warning(
            "%s returned invalid JSON, attempting repair. error=%s",
            provider.name, validation_error,
        )

        repair_prompt = REPAIR_PROMPT.format(raw_json=text)
        repaired_text, repair_error = await provider.generate(repair_prompt, temperature=0.1)

        if repair_error:
            return GenerateResult(success=False, error=f"{provider.name} repair failed: {repair_error}")

        pack, repair_validation_error = self.validate_json(repaired_text)
        if pack:
            sanitized_raw = sanitize_json_string(repaired_text)
            sanitized_pack, _ = self.validate_json(sanitized_raw)
            return GenerateResult(
                success=True,
                pack=sanitized_pack or pack,
                provider_name=f"{provider.name} (repaired)",
                raw_json=sanitized_raw,
            )

        return GenerateResult(
            success=False,
            error=f"{provider.name}: Invalid JSON after repair: {repair_validation_error}",
        )

    async def generate_from_json(
        self,
        raw_json: str,
    ) -> GenerateResult:
        pack, error = self.validate_json(raw_json)
        if pack:
            sanitized_raw = sanitize_json_string(raw_json)
            sanitized_pack, _ = self.validate_json(sanitized_raw)
            return GenerateResult(
                success=True,
                pack=sanitized_pack or pack,
                provider_name="manual",
                raw_json=sanitized_raw,
            )
        return GenerateResult(success=False, error=error)
