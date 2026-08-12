"""Inline keyboards for user settings."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.domain.entities.enums import Category, Grade
from bot.keyboards.onboarding import (
    FOCUS_AREAS_LABELS,
    GRADE_LABELS,
    TECH_STACK_OPTIONS,
)

# =============================================================================
# Callback Data Factories
# =============================================================================


class SettingsMenuCallback(CallbackData, prefix="settings"):
    """Callback data for settings main menu actions."""

    action: str  # "edit_grade", "edit_tech", "edit_focus", "toggle_reminders", "back"


class SettingsGradeCallback(CallbackData, prefix="set_grade"):
    """Callback data for grade change in settings."""

    value: str


class SettingsTechCallback(CallbackData, prefix="set_tech"):
    """Callback data for tech stack change in settings."""

    action: str  # "toggle" or "done"
    value: str


class SettingsFocusCallback(CallbackData, prefix="set_focus"):
    """Callback data for focus areas change in settings."""

    action: str  # "toggle" or "done"
    value: str


# =============================================================================
# Keyboard Builders
# =============================================================================


def get_settings_menu_keyboard(*, reminders_enabled: bool = True) -> InlineKeyboardMarkup:
    """Create inline keyboard for the settings main menu.

    Args:
        reminders_enabled: Whether reminders are currently enabled.

    Returns:
        Keyboard with settings options.
    """
    builder = InlineKeyboardBuilder()

    builder.button(
        text="📊 Изменить уровень",
        callback_data=SettingsMenuCallback(action="edit_grade"),
    )
    builder.button(
        text="💻 Изменить технологии",
        callback_data=SettingsMenuCallback(action="edit_tech"),
    )
    builder.button(
        text="🎯 Изменить области фокуса",
        callback_data=SettingsMenuCallback(action="edit_focus"),
    )

    reminder_text = "🔔 Напоминания: ВКЛ" if reminders_enabled else "🔕 Напоминания: ВЫКЛ"
    builder.button(
        text=reminder_text,
        callback_data=SettingsMenuCallback(action="toggle_reminders"),
    )

    builder.adjust(1)
    return builder.as_markup()


def get_settings_grade_keyboard(current_grade: Grade) -> InlineKeyboardMarkup:
    """Create inline keyboard for grade selection in settings.

    Shows current grade with a check mark.

    Args:
        current_grade: The user's current grade.

    Returns:
        Keyboard with grade options and a back button.
    """
    builder = InlineKeyboardBuilder()

    for grade, label in GRADE_LABELS.items():
        text = f"✅ {label}" if grade == current_grade else label
        builder.button(
            text=text,
            callback_data=SettingsGradeCallback(value=grade.value),
        )

    builder.adjust(1)

    keyboard = builder.as_markup()
    back_button = InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=SettingsMenuCallback(action="back").pack(),
    )
    keyboard.inline_keyboard.append([back_button])

    return keyboard


def get_settings_tech_keyboard(selected: set[str] | None = None) -> InlineKeyboardMarkup:
    """Create inline keyboard for tech stack editing in settings.

    Args:
        selected: Set of currently selected technologies.

    Returns:
        Keyboard with tech options, Done and Back buttons.
    """
    if selected is None:
        selected = set()

    builder = InlineKeyboardBuilder()

    for tech in TECH_STACK_OPTIONS:
        is_selected = tech in selected
        text = f"✅ {tech}" if is_selected else tech
        builder.button(
            text=text,
            callback_data=SettingsTechCallback(action="toggle", value=tech),
        )

    builder.adjust(2)

    keyboard = builder.as_markup()

    done_button = InlineKeyboardButton(
        text="✔️ Сохранить",
        callback_data=SettingsTechCallback(action="done", value="").pack(),
    )
    back_button = InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=SettingsMenuCallback(action="back").pack(),
    )
    keyboard.inline_keyboard.append([done_button, back_button])

    return keyboard


def get_settings_focus_keyboard(
    selected: set[Category] | None = None,
) -> InlineKeyboardMarkup:
    """Create inline keyboard for focus areas editing in settings.

    Args:
        selected: Set of currently selected focus area categories.

    Returns:
        Keyboard with focus area options, Done and Back buttons.
    """
    if selected is None:
        selected = set()

    builder = InlineKeyboardBuilder()

    for category, label in FOCUS_AREAS_LABELS.items():
        is_selected = category in selected
        text = f"✅ {label}" if is_selected else label
        builder.button(
            text=text,
            callback_data=SettingsFocusCallback(action="toggle", value=category.value),
        )

    builder.adjust(2)

    keyboard = builder.as_markup()

    done_button = InlineKeyboardButton(
        text="✔️ Сохранить",
        callback_data=SettingsFocusCallback(action="done", value="").pack(),
    )
    back_button = InlineKeyboardButton(
        text="◀️ Назад",
        callback_data=SettingsMenuCallback(action="back").pack(),
    )
    keyboard.inline_keyboard.append([done_button, back_button])

    return keyboard
