"""Tests for rate limiting middleware."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.middlewares.rate_limit import RateLimitMiddleware, _extract_telegram_user_id


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user object."""
    user = MagicMock()
    user.id = 123456789
    return user


@pytest.fixture
def mock_handler():
    """Create a mock handler function."""
    return AsyncMock(return_value="handler_result")


class TestExtractTelegramUserId:
    """Tests for _extract_telegram_user_id helper."""

    def test_extract_from_message(self, mock_telegram_user):
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user

        result = _extract_telegram_user_id(event)
        assert result == 123456789

    def test_extract_from_callback_query(self, mock_telegram_user):
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user

        result = _extract_telegram_user_id(event)
        assert result == 123456789

    def test_returns_none_for_unsupported_event(self):
        from aiogram.types import TelegramObject

        event = MagicMock(spec=TelegramObject)

        result = _extract_telegram_user_id(event)
        assert result is None

    def test_returns_none_when_from_user_is_none(self):
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = None

        result = _extract_telegram_user_id(event)
        assert result is None


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    async def test_allows_request_under_limit(
        self, mock_telegram_user, mock_handler
    ):
        """Requests under the limit are forwarded to handler."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user

        middleware = RateLimitMiddleware(max_requests=5, window_seconds=60.0)

        result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_blocks_request_over_limit_message(
        self, mock_telegram_user, mock_handler
    ):
        """Request exceeding the limit on a Message gets a rejection reply."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.answer = AsyncMock()

        middleware = RateLimitMiddleware(max_requests=3, window_seconds=60.0)

        # Use up the limit
        for _ in range(3):
            await middleware(mock_handler, event, {})

        mock_handler.reset_mock()
        result = await middleware(mock_handler, event, {})

        assert result is None
        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        msg = event.answer.call_args[0][0]
        assert "Слишком много запросов" in msg

    async def test_blocks_request_over_limit_callback(
        self, mock_telegram_user, mock_handler
    ):
        """Request exceeding the limit on a CallbackQuery gets an alert."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user
        event.answer = AsyncMock()

        middleware = RateLimitMiddleware(max_requests=2, window_seconds=60.0)

        for _ in range(2):
            await middleware(mock_handler, event, {})

        mock_handler.reset_mock()
        result = await middleware(mock_handler, event, {})

        assert result is None
        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        assert event.answer.call_args[1]["show_alert"] is True

    async def test_counter_resets_after_window(
        self, mock_telegram_user, mock_handler
    ):
        """Requests are allowed again after the window expires."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.answer = AsyncMock()

        middleware = RateLimitMiddleware(max_requests=2, window_seconds=60.0)

        # Exhaust limit
        for _ in range(2):
            await middleware(mock_handler, event, {})

        # Simulate time passing beyond the window
        with patch("bot.middlewares.rate_limit.time") as mock_time:
            mock_time.monotonic.return_value = time.monotonic() + 61.0
            mock_handler.reset_mock()
            result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_different_users_have_separate_limits(self, mock_handler):
        """Each user has an independent rate limit counter."""
        from aiogram.types import Message

        user_a = MagicMock()
        user_a.id = 111

        user_b = MagicMock()
        user_b.id = 222

        event_a = MagicMock(spec=Message)
        event_a.from_user = user_a
        event_a.answer = AsyncMock()

        event_b = MagicMock(spec=Message)
        event_b.from_user = user_b

        middleware = RateLimitMiddleware(max_requests=2, window_seconds=60.0)

        # Exhaust limit for user A
        for _ in range(2):
            await middleware(mock_handler, event_a, {})

        # User A is blocked
        mock_handler.reset_mock()
        result_a = await middleware(mock_handler, event_a, {})
        assert result_a is None

        # User B is NOT blocked
        mock_handler.reset_mock()
        result_b = await middleware(mock_handler, event_b, {})
        assert result_b == "handler_result"
        mock_handler.assert_called_once()

    async def test_unsupported_event_passes_through(self, mock_handler):
        """Events without a user ID pass through without rate limiting."""
        from aiogram.types import TelegramObject

        event = MagicMock(spec=TelegramObject)

        middleware = RateLimitMiddleware(max_requests=1, window_seconds=60.0)

        result = await middleware(mock_handler, event, {})
        assert result == "handler_result"

    async def test_default_limits(self):
        """Default limits match the specification: 60 requests / 60 seconds."""
        middleware = RateLimitMiddleware()
        assert middleware._max_requests == 60
        assert middleware._window_seconds == 60.0

    async def test_exact_limit_is_allowed(
        self, mock_telegram_user, mock_handler
    ):
        """Exactly max_requests calls go through; max_requests+1 is blocked."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.answer = AsyncMock()

        middleware = RateLimitMiddleware(max_requests=3, window_seconds=60.0)

        for i in range(3):
            result = await middleware(mock_handler, event, {})
            assert result == "handler_result", f"Call {i+1} should succeed"

        mock_handler.reset_mock()
        result = await middleware(mock_handler, event, {})
        assert result is None
        mock_handler.assert_not_called()
