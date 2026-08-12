"""Onboarding handlers for user profile setup."""

import logging

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.keyboards.onboarding import (
    FOCUS_AREAS_LABELS,
    GRADE_LABELS,
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
from bot.repositories.profile_repository import ProfileRepository
from bot.repositories.user_repository import UserRepository
from bot.states.onboarding import OnboardingStates

logger = logging.getLogger(__name__)

router = Router(name="onboarding")


async def start_onboarding(message: Message, state: FSMContext) -> None:
    """Start the onboarding flow by showing specialty selection.

    This function is called from the start handler when a new user
    or a user without a profile needs to complete onboarding.

    Args:
        message: The incoming Telegram message.
        state: FSM context for managing conversation state.
    """
    await state.set_state(OnboardingStates.waiting_specialty)

    text = (
        "<b>Шаг 1 из 4: Выбор специальности</b>\n\n"
        "Выбери свою специальность. В MVP доступен только Backend, "
        "но мы добавим другие направления в будущем."
    )

    await message.answer(text, reply_markup=get_specialty_keyboard())
    logger.info("Started onboarding for user telegram_id=%d", message.from_user.id)


@router.callback_query(
    OnboardingStates.waiting_specialty,
    SpecialtyCallback.filter(),
)
async def process_specialty_selection(
    callback: CallbackQuery,
    callback_data: SpecialtyCallback,
    state: FSMContext,
) -> None:
    """Process specialty selection and move to grade selection.

    Args:
        callback: The callback query from the inline button.
        callback_data: Parsed callback data with specialty value.
        state: FSM context for managing conversation state.
    """
    specialty_value = callback_data.value

    # Validate specialty
    try:
        specialty = Specialty(specialty_value)
    except ValueError:
        logger.warning("Invalid specialty value: %s", specialty_value)
        await callback.answer("Неизвестная специальность. Попробуй ещё раз.")
        return

    # Save specialty to FSM context
    await state.update_data(specialty=specialty.value)

    # Move to next state
    await state.set_state(OnboardingStates.waiting_grade)

    # Update message with grade selection
    text = (
        "<b>Шаг 2 из 4: Выбор уровня</b>\n\n"
        "Отлично! Теперь выбери свой уровень опыта.\n\n"
        "От этого зависит сложность вопросов:\n"
        "• <b>Junior</b> — базовые вопросы, основы\n"
        "• <b>Middle</b> — практические задачи, паттерны\n"
        "• <b>Senior</b> — архитектура, system design"
    )

    await callback.message.edit_text(text, reply_markup=get_grade_keyboard())
    await callback.answer()

    logger.info(
        "User telegram_id=%d selected specialty=%s, moving to grade selection",
        callback.from_user.id,
        specialty.value,
    )


@router.callback_query(
    OnboardingStates.waiting_grade,
    GradeCallback.filter(),
)
async def process_grade_selection(
    callback: CallbackQuery,
    callback_data: GradeCallback,
    state: FSMContext,
) -> None:
    """Process grade selection and move to tech stack selection.

    Args:
        callback: The callback query from the inline button.
        callback_data: Parsed callback data with grade value.
        state: FSM context for managing conversation state.
    """
    grade_value = callback_data.value

    # Validate grade
    try:
        grade = Grade(grade_value)
    except ValueError:
        logger.warning("Invalid grade value: %s", grade_value)
        await callback.answer("Неизвестный уровень. Попробуй ещё раз.")
        return

    # Save grade to FSM context
    await state.update_data(grade=grade.value)

    # Move to next state (tech stack selection - TASK-013)
    await state.set_state(OnboardingStates.waiting_tech_stack)

    # Get current data for logging
    data = await state.get_data()

    text = (
        "<b>Шаг 3 из 4: Технологии</b>\n\n"
        "Выбери технологии, с которыми ты работаешь.\n"
        "Можно выбрать несколько. Это поможет подбирать "
        "релевантные вопросы.\n\n"
        "<i>Нажми на технологию для выбора, затем 'Готово'.</i>"
    )

    await callback.message.edit_text(text, reply_markup=get_tech_stack_keyboard())
    await callback.answer()

    logger.info(
        "User telegram_id=%d selected grade=%s, moving to tech stack selection. "
        "Current data: %s",
        callback.from_user.id,
        grade.value,
        data,
    )


@router.callback_query(
    OnboardingStates.waiting_tech_stack,
    TechStackCallback.filter(),
)
async def process_tech_stack_selection(
    callback: CallbackQuery,
    callback_data: TechStackCallback,
    state: FSMContext,
) -> None:
    """Process tech stack selection (toggle or done).

    Args:
        callback: The callback query from the inline button.
        callback_data: Parsed callback data with action and value.
        state: FSM context for managing conversation state.
    """
    action = callback_data.action
    value = callback_data.value

    # Get current selected technologies from FSM context
    data = await state.get_data()
    selected_tech: set[str] = set(data.get("tech_stack", []))

    if action == "toggle":
        # Validate tech value against known options
        if value not in TECH_STACK_OPTIONS:
            logger.warning(
                "Invalid tech stack value from telegram_id=%d: %s",
                callback.from_user.id,
                value,
            )
            await callback.answer("Неизвестная технология.")
            return

        # Toggle technology selection
        if value in selected_tech:
            selected_tech.remove(value)
            logger.debug(
                "User telegram_id=%d deselected tech: %s",
                callback.from_user.id,
                value,
            )
        else:
            selected_tech.add(value)
            logger.debug(
                "User telegram_id=%d selected tech: %s",
                callback.from_user.id,
                value,
            )

        # Update FSM context with new selection
        await state.update_data(tech_stack=list(selected_tech))

        # Update keyboard to show current selection
        text = (
            "<b>Шаг 3 из 4: Технологии</b>\n\n"
            "Выбери технологии, с которыми ты работаешь.\n"
            "Можно выбрать несколько. Это поможет подбирать "
            "релевантные вопросы.\n\n"
            f"<i>Выбрано: {len(selected_tech)}</i>"
        )

        await callback.message.edit_text(
            text, reply_markup=get_tech_stack_keyboard(selected_tech)
        )
        await callback.answer()

    elif action == "done":
        # Validate minimum selection
        if len(selected_tech) < 1:
            await callback.answer(
                "Выбери хотя бы одну технологию!", show_alert=True
            )
            return

        # Save final selection and move to next step
        await state.update_data(tech_stack=list(selected_tech))

        # Move to focus areas selection (TASK-014)
        await state.set_state(OnboardingStates.waiting_focus_areas)

        # Import here to avoid circular imports
        from bot.keyboards.onboarding import get_focus_areas_keyboard

        text = (
            "<b>Шаг 4 из 4: Области для практики</b>\n\n"
            "Последний шаг! Выбери области, на которых хочешь "
            "сфокусироваться в подготовке.\n\n"
            "<i>Нажми на область для выбора, затем 'Готово'.</i>"
        )

        await callback.message.edit_text(
            text, reply_markup=get_focus_areas_keyboard()
        )
        await callback.answer()

        logger.info(
            "User telegram_id=%d completed tech stack selection: %s, "
            "moving to focus areas",
            callback.from_user.id,
            list(selected_tech),
        )


@router.callback_query(
    OnboardingStates.waiting_focus_areas,
    FocusAreasCallback.filter(),
)
async def process_focus_areas_selection(
    callback: CallbackQuery,
    callback_data: FocusAreasCallback,
    state: FSMContext,
) -> None:
    """Process focus areas selection (toggle or done).

    Args:
        callback: The callback query from the inline button.
        callback_data: Parsed callback data with action and value.
        state: FSM context for managing conversation state.
    """
    action = callback_data.action
    value = callback_data.value

    # Get current selected focus areas from FSM context
    data = await state.get_data()
    selected_areas: set[str] = set(data.get("focus_areas", []))

    if action == "toggle":
        # Validate focus area value against Category enum
        try:
            Category(value)
        except ValueError:
            logger.warning(
                "Invalid focus area value from telegram_id=%d: %s",
                callback.from_user.id,
                value,
            )
            await callback.answer("Неизвестная область.")
            return

        # Toggle focus area selection
        if value in selected_areas:
            selected_areas.remove(value)
            logger.debug(
                "User telegram_id=%d deselected focus area: %s",
                callback.from_user.id,
                value,
            )
        else:
            selected_areas.add(value)
            logger.debug(
                "User telegram_id=%d selected focus area: %s",
                callback.from_user.id,
                value,
            )

        # Update FSM context with new selection
        await state.update_data(focus_areas=list(selected_areas))

        # Convert string values to Category enums for keyboard
        selected_categories = set()
        for area in selected_areas:
            try:
                selected_categories.add(Category(area))
            except ValueError:
                logger.warning("Unknown focus area value: %s", area)

        # Update keyboard to show current selection
        text = (
            "<b>Шаг 4 из 4: Области для практики</b>\n\n"
            "Последний шаг! Выбери области, на которых хочешь "
            "сфокусироваться в подготовке.\n\n"
            f"<i>Выбрано: {len(selected_areas)}</i>"
        )

        await callback.message.edit_text(
            text, reply_markup=get_focus_areas_keyboard(selected_categories)
        )
        await callback.answer()

    elif action == "done":
        # Validate minimum selection
        if len(selected_areas) < 1:
            await callback.answer(
                "Выбери хотя бы одну область!", show_alert=True
            )
            return

        # Save final selection
        await state.update_data(focus_areas=list(selected_areas))

        # Complete onboarding - save profile to database
        await _complete_onboarding(callback, state)


async def _complete_onboarding(callback: CallbackQuery, state: FSMContext) -> None:
    """Complete onboarding by saving profile to database.

    Args:
        callback: The callback query from the inline button.
        state: FSM context containing all profile data.
    """
    # Get all collected data from FSM
    data = await state.get_data()

    specialty_value = data.get("specialty", Specialty.BACKEND.value)
    grade_value = data.get("grade")
    tech_stack = data.get("tech_stack", [])
    focus_areas_values = data.get("focus_areas", [])

    # Convert to domain models
    try:
        specialty = Specialty(specialty_value)
        grade = Grade(grade_value)
        focus_areas = [Category(area) for area in focus_areas_values]
    except (ValueError, TypeError) as e:
        logger.error(
            "Failed to convert onboarding data for telegram_id=%d: %s",
            callback.from_user.id,
            e,
        )
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении профиля. "
            "Пожалуйста, попробуй снова с /start"
        )
        await callback.answer()
        await state.clear()
        return

    # Get user from database
    user_repo = UserRepository()
    user = await user_repo.get_by_telegram_id(callback.from_user.id)

    if user is None:
        logger.error(
            "User not found for telegram_id=%d during onboarding completion",
            callback.from_user.id,
        )
        await callback.message.edit_text(
            "❌ Пользователь не найден. Пожалуйста, начни с /start"
        )
        await callback.answer()
        await state.clear()
        return

    # Determine initial difficulty based on grade
    initial_difficulty = {
        Grade.JUNIOR: 2,
        Grade.MIDDLE: 5,
        Grade.SENIOR: 7,
    }[grade]

    # Create user profile
    profile = UserProfile(
        user_id=user.id,
        specialty=specialty,
        grade=grade,
        tech_stack=tech_stack,
        focus_areas=focus_areas,
        current_difficulty=initial_difficulty,
    )

    profile_repo = ProfileRepository()

    try:
        created_profile = await profile_repo.create(profile)
        logger.info(
            "Created profile for telegram_id=%d, user_id=%s, profile_id=%s",
            callback.from_user.id,
            user.id,
            created_profile.id,
        )
    except Exception as e:
        logger.exception(
            "Failed to create profile for telegram_id=%d: %s",
            callback.from_user.id,
            e,
        )
        await callback.message.edit_text(
            "❌ Произошла ошибка при сохранении профиля. "
            "Пожалуйста, попробуй снова с /start"
        )
        await callback.answer()
        await state.clear()
        return

    # Clear FSM state
    await state.clear()

    # Format profile summary message
    summary_text = _format_profile_summary(
        specialty=specialty,
        grade=grade,
        tech_stack=tech_stack,
        focus_areas=focus_areas,
    )

    await callback.message.edit_text(summary_text)
    await callback.answer("Профиль сохранён!")

    logger.info(
        "Onboarding completed for telegram_id=%d, profile_id=%s",
        callback.from_user.id,
        created_profile.id,
    )


def _format_profile_summary(
    specialty: Specialty,
    grade: Grade,
    tech_stack: list[str],
    focus_areas: list[Category],
) -> str:
    """Format a profile summary message.

    Args:
        specialty: User's specialty.
        grade: User's grade level.
        tech_stack: List of technologies.
        focus_areas: List of focus area categories.

    Returns:
        Formatted HTML message string.
    """
    # Get grade label
    grade_label = GRADE_LABELS.get(grade, grade.value)

    # Format tech stack
    tech_stack_str = ", ".join(tech_stack) if tech_stack else "—"

    # Format focus areas with labels
    focus_areas_str = ", ".join(
        FOCUS_AREAS_LABELS.get(area, area.value) for area in focus_areas
    ) if focus_areas else "—"

    return (
        "✅ <b>Профиль создан!</b>\n\n"
        "Твой профиль:\n"
        f"• <b>Специальность:</b> Backend\n"
        f"• <b>Уровень:</b> {grade_label}\n"
        f"• <b>Технологии:</b> {tech_stack_str}\n"
        f"• <b>Области фокуса:</b> {focus_areas_str}\n\n"
        "Теперь ты можешь начать практику!\n\n"
        "Используй /practice чтобы получить свой первый вопрос."
    )
