"""Prompt templates for AI homework generation — language-first pedagogy"""
from ai_homework.prompt_templates import SYSTEM_PROMPT, EVALUATION_PROMPT


def build_user_prompt(
    topic: str,
    level: str,
    focus: str,
    count: int,
    context: str | None = None,
) -> str:
    focus_desc = {
        "vocabulary": "vocabulary: word choice, collocations, professional IT vocabulary",
        "grammar": "grammar: tenses, conditionals, prepositions, articles, word order",
        "speaking": "speaking: professional communication, register, clarifying questions",
        "reading": "reading: comprehension, extracting key information from technical texts",
        "mixed": "mixed language skills with IT context",
    }
    parts = [
        f"Create a homework pack using the IT topic '{topic}' as context.",
        f"Level: {level}",
        f"Focus: {focus_desc.get(focus, focus)}",
        f"Number of exercises: {count}",
        "\nIMPORTANT: Every exercise must test ENGLISH language proficiency. The IT context is just the setting.",
    ]
    if context:
        context_trimmed = context[:2000]
        parts.append(f"\nUse this lesson context to identify relevant language points:\n{context_trimmed}")
    parts.append("\nReturn ONLY valid JSON matching the schema.")
    return "\n".join(parts)


REPAIR_PROMPT = """The following JSON is invalid. Fix it to match this schema exactly:
{{
  "title": "string",
  "level": "A2" | "B1" | "B2",
  "topic": "string",
  "instructions": "string",
  "exercises": [
    {{ "type": "multiple_choice", "language_goal": "string", "question": "string", "options": ["a","b","c","d"], "correct_answer": "string", "explanation": "string" }},
    {{ "type": "true_false", "language_goal": "string", "question": "string", "correct_answer": true, "explanation": "string" }},
    {{ "type": "select_all", "language_goal": "string", "question": "string", "options": ["a","b","c"], "correct_answers": [0, 2], "explanation": "string" }},
    {{ "type": "fill_in_the_gap", "language_goal": "string", "sentence": "string with ___", "correct_answer": "string", "hint": "string" }},
    {{ "type": "short_answer", "language_goal": "string", "question": "string", "sample_answer": "string", "useful_phrases": ["string", "string"] }},
    {{ "type": "order_items", "language_goal": "string", "instruction": "string", "items": ["a","b","c"], "correct_order": [0, 1, 2], "explanation": "string" }},
    {{ "type": "synonyms_match", "language_goal": "string", "instruction": "string", "pairs": [{{"word": "a", "synonym": "b"}}], "distractors": ["c", "d", "e"], "explanation": "string" }},
    {{ "type": "error_correction", "language_goal": "string", "incorrect_sentence": "string", "correction": "string", "hint": "string", "explanation": "string" }},
    {{ "type": "word_formation", "language_goal": "string", "sentence_with_blank": "string", "base_word": "string", "correct_form": "string", "hint": "string", "explanation": "string" }},
    {{ "type": "cloze_text", "language_goal": "string", "instruction": "string", "text_with_gaps": "string", "gaps": [{{"correct_answer": "string", "hint": "string"}}], "explanation": "string" }},
    {{ "type": "reorder_words", "language_goal": "string", "instruction": "string", "scrambled_words": ["a","b","c"], "correct_sentence": "string", "explanation": "string" }}
  ]
}}

Rules:
- ONLY output the fixed JSON. No markdown. No code fences. No text before or after.
- Use double quotes. No trailing commas.
- Keep the same content, just fix the structure.

Invalid JSON to fix:
{raw_json}"""
