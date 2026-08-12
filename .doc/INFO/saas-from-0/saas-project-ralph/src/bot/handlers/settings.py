"""Settings handler for user profile management."""

import contextlib
import logging
from uuid import UUID

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.domain.entities.enums import Category, Grade
from bot.domain.entities.profile import UserProfile
from bot.domain.entities.user import User
from bot.keyboards.onboarding import (
    FOCUS_AREAS_LABELS,
    GRADE_LABELS,
    TECH_STACK_OPTIONS,
)
from bot.keyboards.settings import (
    SettingsFocusCallback,
    SettingsGradeCallback,
    SettingsMenuCallback,
    SettingsTechCallback,
    get_settings_focus_keyboard,
    get_settings_grade_keyboard,
    get_settings_menu_keyboard,
    get_settings_tech_keyboard,
)
from bot.repositories.profile_repository import (
    ProfileRepository,
    ProfileRepositoryError,
)
from bot.repositories.reminder_repository import ReminderRepository
from bot.states.settings import SettingsStates

logger = logging.getLogger(__name__)

router = Router(name="settings")


# =============================================================================
# Helpers
# =============================================================================


async def _get_reminders_enabled(user_id: UUID) -> bool:
    """Check if reminders are enabled for the user.

    Args:
        user_id: Internal user UUID.

    Returns:
        True if reminders are enabled, True by default if no record exists.
    """
    try:
        repo = ReminderRepository()
        settings = await repo.get_by_user_id(user_id)
        if settings is not None:
            return settings.reminders_enabled
        return True
    except Exception:
        logger.exception("Failed to fetch reminder settings for user_id=%s", user_id)
        return True


async def _toggle_reminders(user_id: UUID) -> bool:
    """Toggle reminders for the user and return the new state.

    Creates a reminder_settings record if none exists.

    Args:
        user_id: Internal user UUID.

    Returns:
        The new reminders_enabled value.
    """
    repo = ReminderRepository()
    settings = await repo.get_or_create(user_id)
    settings.reminders_enabled = not settings.reminders_enabled
    await repo.update(settings)
    return settings.reminders_enabled


def _format_current_profile(profile: UserProfile, reminders_enabled: bool) -> str:
    """Format the current profile summary for the settings menu.

    Args:
        profile: User profile.
        reminders_enabled: Whether reminders are on.

    Returns:
        Formatted HTML string.
    """
    grade_label = GRADE_LABELS.get(profile.grade, profile.grade.value)
    tech_str = ", ".join(profile.tech_stack) if profile.tech_stack else "—"
    focus_str = (
        ", ".join(
            FOCUS_AREAS_LABELS.get(area, area.value) for area in profile.focus_areas
        )
        if profile.focus_areas
        else "—"
    )
    reminder_status = "ВКЛ" if reminders_enabled else "ВЫКЛ"

    return (
        "<b>Настройки профиля</b>\n\n"
        f"• <b>Уровень:</b> {grade_label}\n"
        f"• <b>Технологии:</b> {tech_str}\n"
        f"• <b>Области фокуса:</b> {focus_str}\n"
        f"• <b>Напоминания:</b> {reminder_status}\n\n"
        "Выбери, что хочешь изменить:"
    )


# =============================================================================
# /settings command
# =============================================================================


@router.message(Command("settings"))
async def cmd_settings(
    message: Message,
    state: FSMContext,
    user: User | None = None,
) -> None:
    """Handle /settings command — show settings menu.

    Args:
        message: The incoming Telegram message.
        state: FSM context.
        user: Injected user from auth middleware.
    """
    if message.from_user is None:
        return

    if user is None:
        await message.answer("Пожалуйста, начни с /start для регистрации.")
        return

    # Clear any previous FSM state
    await state.clear()

    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        await message.answer(
            "У тебя ещё нет профиля. Пройди онбординг через /start."
        )
        return

    reminders_enabled = await _get_reminders_enabled(user.id)

    text = _format_current_profile(profile, reminders_enabled)
    await message.answer(
        text,
        reply_markup=get_settings_menu_keyboard(reminders_enabled=reminders_enabled),
    )

    logger.info(
        "User telegram_id=%d opened settings",
        message.from_user.id,
    )


# =============================================================================
# Settings menu callbacks
# =============================================================================


@router.callback_query(SettingsMenuCallback.filter())
async def process_settings_menu(
    callback: CallbackQuery,
    callback_data: SettingsMenuCallback,
    state: FSMContext,
    user: User | None = None,
) -> None:
    """Handle settings menu button presses.

    Args:
        callback: The callback query.
        callback_data: Parsed callback data with action.
        state: FSM context.
        user: Injected user from auth middleware.
    """
    if user is None:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    action = callback_data.action

    if action == "back":
        await _show_settings_menu(callback, state, user)
        return

    if action == "edit_grade":
        await _start_edit_grade(callback, state, user)
    elif action == "edit_tech":
        await _start_edit_tech(callback, state, user)
    elif action == "edit_focus":
        await _start_edit_focus(callback, state, user)
    elif action == "toggle_reminders":
        await _handle_toggle_reminders(callback, state, user)
    else:
        await callback.answer("Неизвестное действие.")


async def _show_settings_menu(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Show the settings menu (used for back navigation)."""
    await state.clear()

    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        await callback.message.edit_text(
            "Профиль не найден. Пройди онбординг через /start."
        )
        await callback.answer()
        return

    reminders_enabled = await _get_reminders_enabled(user.id)
    text = _format_current_profile(profile, reminders_enabled)

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard(reminders_enabled=reminders_enabled),
    )
    await callback.answer()


# =============================================================================
# Grade editing
# =============================================================================


async def _start_edit_grade(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Start the grade editing flow."""
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    await state.set_state(SettingsStates.editing_grade)

    text = (
        "<b>Изменение уровня</b>\n\n"
        "Выбери новый уровень. От этого зависит сложность вопросов:\n"
        "• <b>Junior</b> — базовые вопросы (сложность 1-4)\n"
        "• <b>Middle</b> — практические задачи (сложность 3-7)\n"
        "• <b>Senior</b> — архитектура, system design (сложность 5-10)"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_grade_keyboard(profile.grade),
    )
    await callback.answer()


@router.callback_query(
    SettingsStates.editing_grade,
    SettingsGradeCallback.filter(),
)
async def process_settings_grade(
    callback: CallbackQuery,
    callback_data: SettingsGradeCallback,
    state: FSMContext,
    user: User | None = None,
) -> None:
    """Process grade change in settings.

    Args:
        callback: The callback query.
        callback_data: Parsed callback data with grade value.
        state: FSM context.
        user: Injected user from auth middleware.
    """
    if user is None:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    try:
        new_grade = Grade(callback_data.value)
    except ValueError:
        await callback.answer("Неизвестный уровень.")
        return

    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    old_grade = profile.grade

    if new_grade == old_grade:
        await callback.answer("Этот уровень уже установлен.")
        return

    # Update grade and adjust difficulty to fit the new range
    profile.grade = new_grade
    min_diff, max_diff = profile.get_difficulty_range()
    profile.current_difficulty = max(min_diff, min(max_diff, profile.current_difficulty))

    try:
        await profile_repo.update(profile)
    except ProfileRepositoryError:
        logger.exception(
            "Failed to update grade for telegram_id=%d", callback.from_user.id
        )
        await callback.answer("Ошибка при сохранении. Попробуй позже.", show_alert=True)
        return

    logger.info(
        "User telegram_id=%d changed grade from %s to %s",
        callback.from_user.id,
        old_grade.value,
        new_grade.value,
    )

    await state.clear()
    await callback.answer(f"Уровень изменён на {GRADE_LABELS[new_grade]}")

    # Return to settings menu
    reminders_enabled = await _get_reminders_enabled(user.id)
    # Re-fetch profile after update
    profile = await profile_repo.get_by_user_id(user.id)
    text = _format_current_profile(profile, reminders_enabled)

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard(reminders_enabled=reminders_enabled),
    )


# =============================================================================
# Tech stack editing
# =============================================================================


async def _start_edit_tech(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Start the tech stack editing flow."""
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    selected = set(profile.tech_stack)
    await state.set_state(SettingsStates.editing_tech_stack)
    await state.update_data(tech_stack=list(selected))

    text = (
        "<b>Изменение технологий</b>\n\n"
        "Выбери технологии, с которыми ты работаешь.\n"
        "Можно выбрать несколько.\n\n"
        f"<i>Выбрано: {len(selected)}</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_tech_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(
    SettingsStates.editing_tech_stack,
    SettingsTechCallback.filter(),
)
async def process_settings_tech(
    callback: CallbackQuery,
    callback_data: SettingsTechCallback,
    state: FSMContext,
    user: User | None = None,
) -> None:
    """Process tech stack toggle/done in settings.

    Args:
        callback: The callback query.
        callback_data: Parsed callback data with action and value.
        state: FSM context.
        user: Injected user from auth middleware.
    """
    if user is None:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    action = callback_data.action
    value = callback_data.value

    data = await state.get_data()
    selected_tech: set[str] = set(data.get("tech_stack", []))

    if action == "toggle":
        if value not in TECH_STACK_OPTIONS:
            await callback.answer("Неизвестная технология.")
            return

        if value in selected_tech:
            selected_tech.remove(value)
        else:
            selected_tech.add(value)

        await state.update_data(tech_stack=list(selected_tech))

        text = (
            "<b>Изменение технологий</b>\n\n"
            "Выбери технологии, с которыми ты работаешь.\n"
            "Можно выбрать несколько.\n\n"
            f"<i>Выбрано: {len(selected_tech)}</i>"
        )

        await callback.message.edit_text(
            text, reply_markup=get_settings_tech_keyboard(selected_tech)
        )
        await callback.answer()

    elif action == "done":
        if len(selected_tech) < 1:
            await callback.answer(
                "Выбери хотя бы одну технологию!", show_alert=True
            )
            return

        profile_repo = ProfileRepository()
        profile = await profile_repo.get_by_user_id(user.id)

        if profile is None:
            await callback.answer("Профиль не найден.", show_alert=True)
            return

        profile.tech_stack = sorted(selected_tech)

        try:
            await profile_repo.update(profile)
        except ProfileRepositoryError:
            logger.exception(
                "Failed to update tech stack for telegram_id=%d",
                callback.from_user.id,
            )
            await callback.answer(
                "Ошибка при сохранении. Попробуй позже.", show_alert=True
            )
            return

        logger.info(
            "User telegram_id=%d updated tech_stack to %s",
            callback.from_user.id,
            list(selected_tech),
        )

        await state.clear()
        await callback.answer("Технологии обновлены!")

        # Return to settings menu
        reminders_enabled = await _get_reminders_enabled(user.id)
        profile = await profile_repo.get_by_user_id(user.id)
        text = _format_current_profile(profile, reminders_enabled)

        await callback.message.edit_text(
            text,
            reply_markup=get_settings_menu_keyboard(
                reminders_enabled=reminders_enabled
            ),
        )


# =============================================================================
# Focus areas editing
# =============================================================================


async def _start_edit_focus(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Start the focus areas editing flow."""
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        await callback.answer("Профиль не найден.", show_alert=True)
        return

    selected = set(profile.focus_areas)
    await state.set_state(SettingsStates.editing_focus_areas)
    await state.update_data(focus_areas=[area.value for area in selected])

    text = (
        "<b>Изменение областей фокуса</b>\n\n"
        "Выбери области, на которых хочешь сфокусироваться.\n"
        "Можно выбрать несколько.\n\n"
        f"<i>Выбрано: {len(selected)}</i>"
    )

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_focus_keyboard(selected),
    )
    await callback.answer()


@router.callback_query(
    SettingsStates.editing_focus_areas,
    SettingsFocusCallback.filter(),
)
async def process_settings_focus(
    callback: CallbackQuery,
    callback_data: SettingsFocusCallback,
    state: FSMContext,
    user: User | None = None,
) -> None:
    """Process focus areas toggle/done in settings.

    Args:
        callback: The callback query.
        callback_data: Parsed callback data with action and value.
        state: FSM context.
        user: Injected user from auth middleware.
    """
    if user is None:
        await callback.answer("Ошибка: пользователь не найден.", show_alert=True)
        return

    action = callback_data.action
    value = callback_data.value

    data = await state.get_data()
    selected_areas: set[str] = set(data.get("focus_areas", []))

    if action == "toggle":
        try:
            Category(value)
        except ValueError:
            await callback.answer("Неизвестная область.")
            return

        if value in selected_areas:
            selected_areas.remove(value)
        else:
            selected_areas.add(value)

        await state.update_data(focus_areas=list(selected_areas))

        selected_categories = set()
        for area in selected_areas:
            with contextlib.suppress(ValueError):
                selected_categories.add(Category(area))

        text = (
            "<b>Изменение областей фокуса</b>\n\n"
            "Выбери области, на которых хочешь сфокусироваться.\n"
            "Можно выбрать несколько.\n\n"
            f"<i>Выбрано: {len(selected_areas)}</i>"
        )

        await callback.message.edit_text(
            text, reply_markup=get_settings_focus_keyboard(selected_categories)
        )
        await callback.answer()

    elif action == "done":
        if len(selected_areas) < 1:
            await callback.answer(
                "Выбери хотя бы одну область!", show_alert=True
            )
            return

        focus_areas = []
        for area in selected_areas:
            try:
                focus_areas.append(Category(area))
            except ValueError:
                logger.warning("Unknown focus area: %s", area)

        profile_repo = ProfileRepository()
        profile = await profile_repo.get_by_user_id(user.id)

        if profile is None:
            await callback.answer("Профиль не найден.", show_alert=True)
            return

        profile.focus_areas = focus_areas

        try:
            await profile_repo.update(profile)
        except ProfileRepositoryError:
            logger.exception(
                "Failed to update focus areas for telegram_id=%d",
                callback.from_user.id,
            )
            await callback.answer(
                "Ошибка при сохранении. Попробуй позже.", show_alert=True
            )
            return

        logger.info(
            "User telegram_id=%d updated focus_areas to %s",
            callback.from_user.id,
            [a.value for a in focus_areas],
        )

        await state.clear()
        await callback.answer("Области фокуса обновлены!")

        # Return to settings menu
        reminders_enabled = await _get_reminders_enabled(user.id)
        profile = await profile_repo.get_by_user_id(user.id)
        text = _format_current_profile(profile, reminders_enabled)

        await callback.message.edit_text(
            text,
            reply_markup=get_settings_menu_keyboard(
                reminders_enabled=reminders_enabled
            ),
        )


# =============================================================================
# Reminder toggle
# =============================================================================


async def _handle_toggle_reminders(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    """Toggle reminders and refresh the settings menu."""
    try:
        new_state = await _toggle_reminders(user.id)
    except Exception:
        logger.exception(
            "Failed to toggle reminders for telegram_id=%d",
            callback.from_user.id,
        )
        await callback.answer("Ошибка при изменении настроек.", show_alert=True)
        return

    status = "включены" if new_state else "выключены"
    await callback.answer(f"Напоминания {status}")

    logger.info(
        "User telegram_id=%d toggled reminders to %s",
        callback.from_user.id,
        new_state,
    )

    # Refresh settings menu
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user.id)

    if profile is None:
        return

    text = _format_current_profile(profile, new_state)

    await callback.message.edit_text(
        text,
        reply_markup=get_settings_menu_keyboard(reminders_enabled=new_state),
    )
