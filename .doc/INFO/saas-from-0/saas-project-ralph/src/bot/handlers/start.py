"""Start command handler."""

import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.domain.entities.user import User
from bot.repositories.profile_repository import ProfileRepository

logger = logging.getLogger(__name__)

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, user: User | None = None) -> None:
    """Handle /start command.

    For new users: shows a welcome message and starts onboarding flow.
    For existing users with profile: shows a personalized greeting.
    For existing users without profile: starts/continues onboarding.

    Args:
        message: The incoming Telegram message.
        state: FSM context for managing conversation state.
        user: User domain object injected by AuthMiddleware.
    """
    if message.from_user is None:
        logger.warning("Received /start without from_user")
        return

    if user is None:
        logger.warning(
            "User not available in handler data for telegram_id=%d",
            message.from_user.id,
        )
        await message.answer(
            "Произошла ошибка. Пожалуйста, попробуй ещё раз позже."
        )
        return

    profile_repo = ProfileRepository()

    # Check if user has completed onboarding (has a profile)
    profile = await profile_repo.get_by_user_id(user.id)
    has_profile = profile is not None

    # Determine if user was just created (created_at ~= updated_at, no profile)
    is_new = not has_profile and (user.created_at == user.updated_at)

    if is_new:
        await _send_new_user_welcome(message, user, state)
    elif has_profile:
        await _send_returning_user_welcome(message, user, has_profile=True)
    else:
        # User exists but has no profile - continue onboarding
        await _send_returning_user_welcome(message, user, has_profile=False, state=state)


async def _send_new_user_welcome(
    message: Message,
    user: User,
    state: FSMContext,
) -> None:
    """Send welcome message to a new user and start onboarding.

    Args:
        message: The incoming Telegram message.
        user: The newly created user.
        state: FSM context for managing conversation state.
    """
    from bot.handlers.onboarding import start_onboarding

    display_name = _get_display_name(user, message.from_user)

    welcome_text = (
        f"<b>Алоха, {display_name}!</b>\n\n"
        "Добро пожаловать в <b>Interview Trainer Bot</b> — твой персональный "
        "тренажёр для подготовки к техническим собеседованиям.\n\n"
        "Что я умею:\n"
        "• Генерировать вопросы под твой уровень и стек технологий\n"
        "• Оценивать ответы и давать подробный фидбэк\n"
        "• Отслеживать прогресс и поддерживать streak\n"
        "• Адаптировать сложность под твои результаты\n\n"
        "Для начала работы нужно настроить твой профиль. "
        "Это займёт пару минут и поможет подбирать вопросы, "
        "релевантные твоему опыту.\n\n"
        "<i>Давай начнём!</i>"
    )

    await message.answer(welcome_text)
    logger.info(
        "Sent new user welcome to telegram_id=%d, user_id=%s",
        user.telegram_id,
        user.id,
    )

    # Start onboarding flow
    await start_onboarding(message, state)


async def _send_returning_user_welcome(
    message: Message,
    user: User,
    has_profile: bool,
    state: FSMContext | None = None,
) -> None:
    """Send welcome message to a returning user.

    Args:
        message: The incoming Telegram message.
        user: The existing user.
        has_profile: Whether the user has completed onboarding.
        state: FSM context for managing conversation state (required if no profile).
    """
    from bot.handlers.onboarding import start_onboarding

    display_name = _get_display_name(user, message.from_user)

    if has_profile:
        welcome_text = (
            f"<b>С возвращением, {display_name}!</b>\n\n"
            "Рад видеть тебя снова. Готов продолжить тренировку?\n\n"
            "Используй /practice чтобы получить новый вопрос, "
            "или /stats чтобы посмотреть свою статистику."
        )
        await message.answer(welcome_text)
    else:
        welcome_text = (
            f"<b>С возвращением, {display_name}!</b>\n\n"
            "Похоже, ты ещё не завершил настройку профиля. "
            "Давай сделаем это сейчас, чтобы я мог подбирать "
            "вопросы специально для тебя."
        )
        await message.answer(welcome_text)

        # Start onboarding flow
        if state is not None:
            await start_onboarding(message, state)

    logger.info(
        "Sent returning user welcome to telegram_id=%d, user_id=%s, has_profile=%s",
        user.telegram_id,
        user.id,
        has_profile,
    )


def _get_display_name(user: User, telegram_user) -> str:
    """Get display name for the user.

    Priority: first_name from DB > first_name from Telegram > username > 'друг'

    Args:
        user: User domain model from database.
        telegram_user: Telegram user object from message.

    Returns:
        Display name string.
    """
    if user.first_name:
        return user.first_name
    if telegram_user and telegram_user.first_name:
        return telegram_user.first_name
    if user.username:
        return user.username
    return "друг"
