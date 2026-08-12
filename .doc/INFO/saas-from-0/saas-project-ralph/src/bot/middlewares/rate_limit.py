"""Rate limiting middleware — protects against excessive requests."""

import logging
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

logger = logging.getLogger(__name__)

# Default: 60 requests per 60 seconds per user
_MAX_REQUESTS = 60
_WINDOW_SECONDS = 60.0

_RATE_LIMIT_TEXT = (
    "Слишком много запросов. Пожалуйста, подожди немного и попробуй снова."
)


class RateLimitMiddleware(BaseMiddleware):
    """Per-user rate limiter using a sliding window counter.

    Tracks timestamps of recent requests for each Telegram user.  When the
    number of requests within the window exceeds the limit, the handler is
    *not* called and a short message is sent instead.
    """

    def __init__(
        self,
        max_requests: int = _MAX_REQUESTS,
        window_seconds: float = _WINDOW_SECONDS,
    ) -> None:
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        # telegram_user_id → list of monotonic timestamps
        self._requests: dict[int, list[float]] = defaultdict(list)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """Check rate limit and either proceed or reject."""
        user_id = _extract_telegram_user_id(event)
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        cutoff = now - self._window_seconds

        # Prune expired timestamps
        timestamps = self._requests[user_id]
        self._requests[user_id] = [t for t in timestamps if t > cutoff]

        if len(self._requests[user_id]) >= self._max_requests:
            logger.warning(
                "Rate limit exceeded for telegram_user_id=%d (%d requests in %.0fs)",
                user_id,
                len(self._requests[user_id]),
                self._window_seconds,
            )
            if isinstance(event, Message):
                await event.answer(_RATE_LIMIT_TEXT)
            elif isinstance(event, CallbackQuery):
                await event.answer(_RATE_LIMIT_TEXT, show_alert=True)
            return None

        self._requests[user_id].append(now)
        return await handler(event, data)


def _extract_telegram_user_id(event: TelegramObject) -> int | None:
    """Extract the Telegram user ID from a supported event type."""
    if isinstance(event, (Message, CallbackQuery)) and event.from_user is not None:
        return event.from_user.id
    return None
