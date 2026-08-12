"""Input validation middleware — validates and sanitizes user input."""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)

# Maximum allowed length for text messages (answers)
MAX_TEXT_LENGTH = 10_000

_TEXT_TOO_LONG_MSG = (
    "Твой ответ слишком длинный (максимум {limit} символов, "
    "у тебя {length}). Пожалуйста, сократи ответ и отправь снова."
)


def sanitize_text(text: str) -> str:
    """Remove null bytes and strip surrounding whitespace.

    Args:
        text: Raw user text input.

    Returns:
        Cleaned text safe for storage and processing.
    """
    return text.replace("\x00", "").strip()


class InputValidationMiddleware(BaseMiddleware):
    """Validates incoming text messages and callback queries.

    - Rejects text messages exceeding *max_text_length* characters.
    - Strips null bytes from text before forwarding to handlers.
    - Validates callback data is non-empty for CallbackQuery events.
    """

    def __init__(self, max_text_length: int = MAX_TEXT_LENGTH) -> None:
        self._max_text_length = max_text_length

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Validate input and either proceed or reject."""

        if isinstance(event, Message) and event.text is not None:
            text_length = len(event.text)

            if text_length > self._max_text_length:
                logger.warning(
                    "Text too long from telegram_id=%s: %d chars (limit %d)",
                    event.from_user.id if event.from_user else "unknown",
                    text_length,
                    self._max_text_length,
                )
                await event.answer(
                    _TEXT_TOO_LONG_MSG.format(
                        limit=self._max_text_length, length=text_length
                    )
                )
                return None

        if isinstance(event, CallbackQuery) and not event.data:
            logger.warning(
                "Empty callback data from telegram_id=%s",
                event.from_user.id if event.from_user else "unknown",
            )
            await event.answer("Некорректный запрос.")
            return None

        return await handler(event, data)
