"""Authentication middleware — ensures user exists in DB for every update."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.repositories.user_repository import UserRepository, UserRepositoryError

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseMiddleware):
    """Middleware that resolves the database User for every incoming event.

    On each message or callback query the middleware:
    1. Extracts the Telegram user from the event.
    2. Calls ``get_or_create`` so the user always has a DB record.
    3. Puts the resulting ``User`` domain object into ``data["user"]``
       so downstream handlers can access it without querying the DB again.

    If the DB call fails, the event is still forwarded to the handler
    (without ``data["user"]``) so that essential commands like /start
    keep working even during transient DB issues.
    """

    def __init__(self) -> None:
        self._repo = UserRepository()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Process the event and inject the User into handler data."""
        telegram_user = _extract_telegram_user(event)

        if telegram_user is not None:
            try:
                user, created = await self._repo.get_or_create(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    language_code=telegram_user.language_code or "ru",
                )
                data["user"] = user
                if created:
                    logger.info(
                        "Auth middleware: created new user telegram_id=%d",
                        telegram_user.id,
                    )
            except UserRepositoryError:
                logger.warning(
                    "Auth middleware: failed to get/create user for telegram_id=%d, "
                    "proceeding without user in data",
                    telegram_user.id,
                )

        return await handler(event, data)


def _extract_telegram_user(event: TelegramObject):
    """Extract the Telegram user from a supported event type.

    Returns:
        The ``from_user`` object, or ``None`` if unavailable.
    """
    if isinstance(event, Message):
        return event.from_user
    if isinstance(event, CallbackQuery):
        return event.from_user
    return None
