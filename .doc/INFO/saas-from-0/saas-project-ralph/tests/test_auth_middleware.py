"""Tests for authentication middleware."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.user import User
from bot.middlewares.auth import AuthMiddleware, _extract_telegram_user
from bot.repositories.user_repository import UserRepositoryError


@pytest.fixture
def sample_user():
    """Create a sample User domain model."""
    return User(
        id=uuid4(),
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
    )


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user object."""
    user = MagicMock()
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.language_code = "en"
    return user


@pytest.fixture
def mock_handler():
    """Create a mock handler function."""
    return AsyncMock(return_value="handler_result")


class TestExtractTelegramUser:
    """Tests for _extract_telegram_user helper."""

    def test_extract_from_message(self, mock_telegram_user):
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user

        result = _extract_telegram_user(event)
        assert result is mock_telegram_user

    def test_extract_from_callback_query(self, mock_telegram_user):
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user

        result = _extract_telegram_user(event)
        assert result is mock_telegram_user

    def test_returns_none_for_unsupported_event(self):
        from aiogram.types import TelegramObject

        event = MagicMock(spec=TelegramObject)

        result = _extract_telegram_user(event)
        assert result is None


class TestAuthMiddleware:
    """Tests for AuthMiddleware."""

    async def test_injects_user_into_data_for_message(
        self, mock_telegram_user, sample_user, mock_handler
    ):
        """Test that middleware injects user into handler data for messages."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            mock_get_or_create.return_value = (sample_user, False)

            result = await middleware(mock_handler, event, data)

        assert data["user"] is sample_user
        assert result == "handler_result"
        mock_handler.assert_called_once_with(event, data)

    async def test_injects_user_into_data_for_callback(
        self, mock_telegram_user, sample_user, mock_handler
    ):
        """Test that middleware injects user into handler data for callbacks."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.from_user = mock_telegram_user
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            mock_get_or_create.return_value = (sample_user, True)

            result = await middleware(mock_handler, event, data)

        assert data["user"] is sample_user
        assert result == "handler_result"

    async def test_calls_get_or_create_with_correct_args(
        self, mock_telegram_user, sample_user, mock_handler
    ):
        """Test that middleware passes correct Telegram user data to repository."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            mock_get_or_create.return_value = (sample_user, False)

            await middleware(mock_handler, event, data)

            mock_get_or_create.assert_called_once_with(
                telegram_id=123456789,
                username="testuser",
                first_name="Test",
                last_name="User",
                language_code="en",
            )

    async def test_proceeds_without_user_on_db_error(
        self, mock_telegram_user, mock_handler
    ):
        """Test that middleware still calls handler when DB fails."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = mock_telegram_user
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            mock_get_or_create.side_effect = UserRepositoryError("DB down")

            result = await middleware(mock_handler, event, data)

        assert "user" not in data
        assert result == "handler_result"
        mock_handler.assert_called_once_with(event, data)

    async def test_no_from_user_skips_db_call(self, mock_handler):
        """Test that middleware skips DB call when from_user is None."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.from_user = None
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            result = await middleware(mock_handler, event, data)

        mock_get_or_create.assert_not_called()
        assert "user" not in data
        assert result == "handler_result"

    async def test_unsupported_event_type_skips_db_call(self, mock_handler):
        """Test that middleware skips DB call for unsupported event types."""
        from aiogram.types import TelegramObject

        event = MagicMock(spec=TelegramObject)
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            result = await middleware(mock_handler, event, data)

        mock_get_or_create.assert_not_called()
        assert "user" not in data
        assert result == "handler_result"

    async def test_language_code_defaults_to_ru(
        self, sample_user, mock_handler
    ):
        """Test that middleware defaults language_code to 'ru' when None."""
        from aiogram.types import Message

        tg_user = MagicMock()
        tg_user.id = 123
        tg_user.username = None
        tg_user.first_name = None
        tg_user.last_name = None
        tg_user.language_code = None

        event = MagicMock(spec=Message)
        event.from_user = tg_user
        data: dict = {}

        middleware = AuthMiddleware()
        with patch.object(
            middleware._repo, "get_or_create", new_callable=AsyncMock
        ) as mock_get_or_create:
            mock_get_or_create.return_value = (sample_user, True)

            await middleware(mock_handler, event, data)

            mock_get_or_create.assert_called_once_with(
                telegram_id=123,
                username=None,
                first_name=None,
                last_name=None,
                language_code="ru",
            )
