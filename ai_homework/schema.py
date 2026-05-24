"""Pydantic schemas for AI-generated homework JSON validation"""
from typing import Union, Literal
from pydantic import BaseModel, Field


class MultipleChoiceExercise(BaseModel):
    type: Literal["multiple_choice"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    question: str
    options: list[str]
    correct_answer: str
    explanation: str


class TrueFalseExercise(BaseModel):
    type: Literal["true_false"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    question: str
    correct_answer: bool
    explanation: str


class SelectAllExercise(BaseModel):
    type: Literal["select_all"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    question: str
    options: list[str]
    correct_answers: list[int]
    explanation: str


class FillInTheGapExercise(BaseModel):
    type: Literal["fill_in_the_gap"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    sentence: str
    correct_answer: str
    hint: str


class ShortAnswerExercise(BaseModel):
    type: Literal["short_answer"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    question: str
    sample_answer: str
    useful_phrases: list[str]


class OrderItemsExercise(BaseModel):
    type: Literal["order_items"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    instruction: str
    items: list[str]
    correct_order: list[int]
    explanation: str


class SynonymPair(BaseModel):
    word: str = Field(..., min_length=1, max_length=100)
    synonym: str = Field(..., min_length=1, max_length=100)


class SynonymsMatchExercise(BaseModel):
    type: Literal["synonyms_match"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    instruction: str
    pairs: list[SynonymPair] = Field(..., min_length=3, max_length=6)
    distractors: list[str] = Field(..., min_length=3, max_length=10)
    explanation: str


class ErrorCorrectionExercise(BaseModel):
    type: Literal["error_correction"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    incorrect_sentence: str
    correction: str
    hint: str
    explanation: str


class WordFormationExercise(BaseModel):
    type: Literal["word_formation"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    sentence_with_blank: str
    base_word: str
    correct_form: str
    hint: str
    explanation: str


class ClozeGap(BaseModel):
    correct_answer: str
    hint: str


class ClozeTextExercise(BaseModel):
    type: Literal["cloze_text"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    instruction: str
    text_with_gaps: str
    gaps: list[ClozeGap] = Field(..., min_length=2, max_length=6)
    explanation: str


class ReorderWordsExercise(BaseModel):
    type: Literal["reorder_words"]
    language_goal: str = Field(..., min_length=1, max_length=200)
    instruction: str
    scrambled_words: list[str]
    correct_order: list[int]
    correct_sentence: str
    explanation: str


Exercise = Union[
    MultipleChoiceExercise,
    TrueFalseExercise,
    SelectAllExercise,
    FillInTheGapExercise,
    ShortAnswerExercise,
    OrderItemsExercise,
    SynonymsMatchExercise,
    ErrorCorrectionExercise,
    WordFormationExercise,
    ClozeTextExercise,
    ReorderWordsExercise,
]


class HomeworkPack(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    level: Literal["A2", "B1", "B2"]
    topic: str = Field(..., min_length=1, max_length=200)
    instructions: str = Field(..., min_length=1, max_length=1000)
    exercises: list[Exercise] = Field(..., min_length=1, max_length=20)
