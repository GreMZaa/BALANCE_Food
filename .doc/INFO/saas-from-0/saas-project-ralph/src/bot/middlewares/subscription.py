"""Subscription check middleware — blocks practice when free limit is exhausted."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.domain.entities.progress import Progress
from bot.domain.entities.user import User
from bot.keyboards.subscription import get_subscription_plans_keyboard
from bot.repositories.progress_repository import ProgressRepository
from bot.services.subscription_service import SubscriptionServiceError, check_access

logger = logging.getLogger(__name__)


def _build_paywall_text(progress: Progress | None) -> str:
    """Build paywall message with streak and progress info.

    Args:
        progress: User's progress data, or None if unavailable.

    Returns:
        HTML-formatted paywall text.
    """
    parts: list[str] = [
        "<b>Дневной лимит исчерпан</b>\n",
        "Ты использовал все бесплатные вопросы на сегодня.",
    ]

    if progress is not None:
        streak = progress.current_streak
        total = progress.total_questions_answered

        if streak > 0:
            parts.append(
                f"\n\U0001f525 Твой текущий streak: <b>{streak} дн.</b>"
                " \u2014 не теряй его!"
            )
        if total > 0:
            parts.append(
                f"\U0001f4da Всего отвечено вопросов: <b>{total}</b>"
            )

    parts.append(
        "\nОформи подписку, чтобы получить безлимитный доступ "
        "и продолжить практику прямо сейчас!"
    )

    return "\n".join(parts)


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware that verifies subscription access before practice handlers.

    Attach this middleware to the practice router so it only runs for
    practice-related messages and callbacks.  When the user has exhausted
    free daily questions and has no active subscription, the handler is
    *not* called — a paywall message is sent instead.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check subscription access and either proceed or show paywall."""
        user: User | None = data.get("user")

        if user is None:
            # No authenticated user — let the handler deal with it
            return await handler(event, data)

        try:
            has_access = await check_access(user.id)
        except SubscriptionServiceError:
            logger.warning(
                "Subscription check failed for user_id=%s, allowing access",
                user.id,
            )
            # On error, allow access rather than blocking a paying user
            return await handler(event, data)

        if has_access:
            return await handler(event, data)

        # --- paywall ---
        logger.info(
            "User user_id=%s blocked by subscription middleware (limit exhausted)",
            user.id,
        )

        # Fetch progress for streak/stats display in paywall
        progress: Progress | None = None
        try:
            progress_repo = ProgressRepository()
            progress = await progress_repo.get_by_user_id(user.id)
        except Exception:
            logger.debug("Could not fetch progress for paywall, skipping stats")

        paywall_text = _build_paywall_text(progress)

        if isinstance(event, Message):
            await event.answer(
                paywall_text,
                reply_markup=get_subscription_plans_keyboard(),
            )
        elif isinstance(event, CallbackQuery):
            await event.answer()
            if event.message is not None:
                await event.message.answer(
                    paywall_text,
                    reply_markup=get_subscription_plans_keyboard(),
                )

        # Do NOT call the handler — request is blocked
        return None
