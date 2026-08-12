"""Inline keyboards for onboarding flow."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.domain.entities.enums import Category, Grade, Specialty

# =============================================================================
# Callback Data Factories
# =============================================================================


class SpecialtyCallback(CallbackData, prefix="specialty"):
    """Callback data for specialty selection."""

    value: str


class GradeCallback(CallbackData, prefix="grade"):
    """Callback data for grade selection."""

    value: str


class TechStackCallback(CallbackData, prefix="tech"):
    """Callback data for tech stack selection (multi-select)."""

    action: str  # "toggle" or "done"
    value: str  # technology name or empty for "done"


class FocusAreasCallback(CallbackData, prefix="focus"):
    """Callback data for focus areas selection (multi-select)."""

    action: str  # "toggle" or "done"
    value: str  # category name or empty for "done"


# =============================================================================
# Specialty Labels (Russian)
# =============================================================================

SPECIALTY_LABELS: dict[Specialty, str] = {
    Specialty.BACKEND: "🔧 Backend",
    # Другие специальности будут добавлены после MVP
    # Specialty.FRONTEND: "🎨 Frontend",
    # Specialty.QA: "🧪 QA",
    # Specialty.DEVOPS: "⚙️ DevOps",
    # Specialty.DATA_SCIENCE: "📊 Data Science",
}

# =============================================================================
# Grade Labels (Russian)
# =============================================================================

GRADE_LABELS: dict[Grade, str] = {
    Grade.JUNIOR: "🌱 Junior",
    Grade.MIDDLE: "🌿 Middle",
    Grade.SENIOR: "🌳 Senior",
}

# =============================================================================
# Tech Stack Options
# =============================================================================

TECH_STACK_OPTIONS: list[str] = [
    "Python",
    "Java",
    "Go",
    "Node.js",
    "C#",
    "Kotlin",
    "Rust",
    "PHP",
]

# =============================================================================
# Focus Areas Labels (Russian)
# =============================================================================

FOCUS_AREAS_LABELS: dict[Category, str] = {
    Category.LANGUAGE: "💻 Язык программирования",
    Category.ALGORITHMS: "🧮 Алгоритмы",
    Category.DATABASES: "🗄️ Базы данных",
    Category.API_DESIGN: "🔌 API Design",
    Category.SYSTEM_DESIGN: "🏗️ System Design",
    Category.ARCHITECTURE: "📐 Архитектура",
    Category.MICROSERVICES: "🔀 Микросервисы",
    Category.DEVOPS: "⚙️ DevOps",
}


# =============================================================================
# Keyboard Builders
# =============================================================================


def get_specialty_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for specialty selection.

    Note: Only Backend is available in MVP.
    """
    builder = InlineKeyboardBuilder()

    for specialty, label in SPECIALTY_LABELS.items():
        builder.button(
            text=label,
            callback_data=SpecialtyCallback(value=specialty.value),
        )

    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_grade_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for grade selection.

    Returns keyboard with 3 buttons: Junior, Middle, Senior.
    """
    builder = InlineKeyboardBuilder()

    for grade, label in GRADE_LABELS.items():
        builder.button(
            text=label,
            callback_data=GradeCallback(value=grade.value),
        )

    builder.adjust(1)  # One button per row
    return builder.as_markup()


def get_tech_stack_keyboard(
    selected: set[str] | None = None,
) -> InlineKeyboardMarkup:
    """Create inline keyboard for tech stack multi-selection.

    Args:
        selected: Set of already selected technologies.

    Returns:
        Keyboard with tech options and a "Done" button.
    """
    if selected is None:
        selected = set()

    builder = InlineKeyboardBuilder()

    for tech in TECH_STACK_OPTIONS:
        is_selected = tech in selected
        text = f"✅ {tech}" if is_selected else tech
        builder.button(
            text=text,
            callback_data=TechStackCallback(action="toggle", value=tech),
        )

    # Adjust to 2 columns for tech options
    builder.adjust(2)

    # Add "Done" button in a new row
    done_button = InlineKeyboardButton(
        text="✔️ Готово",
        callback_data=TechStackCallback(action="done", value="").pack(),
    )

    keyboard = builder.as_markup()
    keyboard.inline_keyboard.append([done_button])

    return keyboard


def get_focus_areas_keyboard(
    selected: set[Category] | None = None,
) -> InlineKeyboardMarkup:
    """Create inline keyboard for focus areas multi-selection.

    Args:
        selected: Set of already selected categories.

    Returns:
        Keyboard with focus area options and a "Done" button.
    """
    if selected is None:
        selected = set()

    builder = InlineKeyboardBuilder()

    for category, label in FOCUS_AREAS_LABELS.items():
        is_selected = category in selected
        text = f"✅ {label}" if is_selected else label
        builder.button(
            text=text,
            callback_data=FocusAreasCallback(action="toggle", value=category.value),
        )

    # Adjust to 2 columns for focus areas
    builder.adjust(2)

    # Add "Done" button in a new row
    done_button = InlineKeyboardButton(
        text="✔️ Готово",
        callback_data=FocusAreasCallback(action="done", value="").pack(),
    )

    keyboard = builder.as_markup()
    keyboard.inline_keyboard.append([done_button])

    return keyboard
