"""Telegram inline keyboards."""

from bot.keyboards.onboarding import (
    FOCUS_AREAS_LABELS,
    GRADE_LABELS,
    SPECIALTY_LABELS,
    TECH_STACK_OPTIONS,
    FocusAreasCallback,
    GradeCallback,
    SpecialtyCallback,
    TechStackCallback,
    get_focus_areas_keyboard,
    get_grade_keyboard,
    get_specialty_keyboard,
    get_tech_stack_keyboard,
)
from bot.keyboards.practice import (
    NextQuestionCallback,
    get_next_question_keyboard,
)

__all__ = [
    # Callback Data Factories
    "SpecialtyCallback",
    "GradeCallback",
    "TechStackCallback",
    "FocusAreasCallback",
    "NextQuestionCallback",
    # Keyboards
    "get_specialty_keyboard",
    "get_grade_keyboard",
    "get_tech_stack_keyboard",
    "get_focus_areas_keyboard",
    "get_next_question_keyboard",
    # Labels/Options
    "SPECIALTY_LABELS",
    "GRADE_LABELS",
    "TECH_STACK_OPTIONS",
    "FOCUS_AREAS_LABELS",
]
