"""Tests for input validation middleware."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from bot.middlewares.input_validation import (
    MAX_TEXT_LENGTH,
    InputValidationMiddleware,
    sanitize_text,
)


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


class TestSanitizeText:
    """Tests for sanitize_text utility."""

    def test_strips_whitespace(self):
        assert sanitize_text("  hello  ") == "hello"

    def test_removes_null_bytes(self):
        assert sanitize_text("hello\x00world") == "helloworld"

    def test_removes_null_bytes_and_strips(self):
        assert sanitize_text("  \x00hello\x00  ") == "hello"

    def test_empty_string(self):
        assert sanitize_text("") == ""

    def test_only_whitespace(self):
        assert sanitize_text("   ") == ""

    def test_normal_text_unchanged(self):
        text = "This is a normal answer about Python decorators."
        assert sanitize_text(text) == text

    def test_preserves_unicode(self):
        text = "Ответ на русском языке"
        assert sanitize_text(text) == text


class TestInputValidationMiddleware:
    """Tests for InputValidationMiddleware."""

    async def test_allows_normal_text_message(
        self, mock_telegram_user, mock_handler
    ):
        """Normal text messages pass through to the handler."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.text = "My answer about Python"

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_rejects_text_exceeding_limit(
        self, mock_telegram_user, mock_handler
    ):
        """Text messages exceeding the limit are rejected."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.text = "a" * (MAX_TEXT_LENGTH + 1)
        event.answer = AsyncMock()

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result is None
        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        msg = event.answer.call_args[0][0]
        assert "слишком длинный" in msg.lower()

    async def test_allows_text_at_exact_limit(
        self, mock_telegram_user, mock_handler
    ):
        """Text messages at exactly the limit pass through."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.text = "a" * MAX_TEXT_LENGTH

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_custom_max_length(self, mock_telegram_user, mock_handler):
        """Custom max_text_length is respected."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.text = "a" * 101
        event.answer = AsyncMock()

        middleware = InputValidationMiddleware(max_text_length=100)
        result = await middleware(mock_handler, event, {})

        assert result is None
        mock_handler.assert_not_called()

    async def test_allows_valid_callback_query(
        self, mock_telegram_user, mock_handler
    ):
        """Callback queries with valid data pass through."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user
        event.data = "specialty:backend"

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_rejects_empty_callback_data(
        self, mock_telegram_user, mock_handler
    ):
        """Callback queries with empty data are rejected."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user
        event.data = ""
        event.answer = AsyncMock()

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result is None
        mock_handler.assert_not_called()
        event.answer.assert_called_once()

    async def test_rejects_none_callback_data(
        self, mock_telegram_user, mock_handler
    ):
        """Callback queries with None data are rejected."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user
        event.data = None
        event.answer = AsyncMock()

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result is None
        mock_handler.assert_not_called()

    async def test_passes_through_non_text_message(
        self, mock_telegram_user, mock_handler
    ):
        """Messages without text (e.g. photo, sticker) pass through."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        event.text = None

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_passes_through_unsupported_event(self, mock_handler):
        """Unsupported event types pass through without validation."""
        from aiogram.types import TelegramObject

        event = MagicMock(spec=TelegramObject)

        middleware = InputValidationMiddleware()
        result = await middleware(mock_handler, event, {})

        assert result == "handler_result"
        mock_handler.assert_called_once()

    async def test_default_max_length_is_10000(self):
        """Default max text length matches the specification."""
        middleware = InputValidationMiddleware()
        assert middleware._max_text_length == 10_000
