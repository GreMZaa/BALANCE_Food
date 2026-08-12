"""Tests for subscription check middleware."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.progress import Progress
from bot.domain.entities.user import User
from bot.middlewares.subscription import SubscriptionMiddleware, _build_paywall_text
from bot.services.subscription_service import SubscriptionServiceError


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
def sample_progress(sample_user):
    """Create a sample Progress domain model."""
    return Progress(
        user_id=sample_user.id,
        current_streak=5,
        longest_streak=10,
        total_questions_answered=42,
        questions_today=5,
    )


@pytest.fixture
def mock_handler():
    """Create a mock handler function."""
    return AsyncMock(return_value="handler_result")


@pytest.fixture
def middleware():
    """Create a SubscriptionMiddleware instance."""
    return SubscriptionMiddleware()


class TestBuildPaywallText:
    """Tests for _build_paywall_text helper."""

    def test_without_progress(self):
        """Paywall without progress shows base text only."""
        text = _build_paywall_text(None)
        assert "Дневной лимит исчерпан" in text
        assert "Оформи подписку" in text
        assert "streak" not in text

    def test_with_progress_and_streak(self, sample_user):
        """Paywall with streak shows motivating streak info."""
        progress = Progress(
            user_id=sample_user.id,
            current_streak=5,
            total_questions_answered=42,
        )
        text = _build_paywall_text(progress)
        assert "5 дн." in text
        assert "42" in text

    def test_with_zero_streak(self, sample_user):
        """Paywall with zero streak omits streak line."""
        progress = Progress(
            user_id=sample_user.id,
            current_streak=0,
            total_questions_answered=3,
        )
        text = _build_paywall_text(progress)
        assert "streak" not in text
        assert "3" in text


class TestSubscriptionMiddleware:
    """Tests for SubscriptionMiddleware."""

    async def test_allows_when_user_has_access(
        self, middleware, mock_handler, sample_user
    ):
        """Test that middleware proceeds when user has access."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        data: dict = {"user": sample_user}

        with patch(
            "bot.middlewares.subscription.check_access", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = True

            result = await middleware(mock_handler, event, data)

        mock_check.assert_called_once_with(sample_user.id)
        mock_handler.assert_called_once_with(event, data)
        assert result == "handler_result"

    async def test_blocks_message_when_limit_exhausted(
        self, middleware, mock_handler, sample_user, sample_progress
    ):
        """Test that middleware blocks and shows paywall for messages."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.answer = AsyncMock()
        data: dict = {"user": sample_user}

        with (
            patch(
                "bot.middlewares.subscription.check_access",
                new_callable=AsyncMock,
            ) as mock_check,
            patch(
                "bot.middlewares.subscription.ProgressRepository",
            ) as mock_repo_cls,
        ):
            mock_check.return_value = False
            mock_repo_cls.return_value.get_by_user_id = AsyncMock(
                return_value=sample_progress
            )

            result = await middleware(mock_handler, event, data)

        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        call_args = event.answer.call_args
        paywall_text = call_args[0][0]
        assert "Дневной лимит исчерпан" in paywall_text
        assert "5 дн." in paywall_text
        assert call_args[1]["reply_markup"] is not None
        assert result is None

    async def test_blocks_callback_when_limit_exhausted(
        self, middleware, mock_handler, sample_user, sample_progress
    ):
        """Test that middleware blocks and shows paywall for callbacks."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.answer = AsyncMock()
        event.message = MagicMock()
        event.message.answer = AsyncMock()
        data: dict = {"user": sample_user}

        with (
            patch(
                "bot.middlewares.subscription.check_access",
                new_callable=AsyncMock,
            ) as mock_check,
            patch(
                "bot.middlewares.subscription.ProgressRepository",
            ) as mock_repo_cls,
        ):
            mock_check.return_value = False
            mock_repo_cls.return_value.get_by_user_id = AsyncMock(
                return_value=sample_progress
            )

            result = await middleware(mock_handler, event, data)

        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        event.message.answer.assert_called_once()
        call_args = event.message.answer.call_args
        paywall_text = call_args[0][0]
        assert "Дневной лимит исчерпан" in paywall_text
        assert result is None

    async def test_allows_access_on_service_error(
        self, middleware, mock_handler, sample_user
    ):
        """Test that middleware allows access when subscription check fails."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        data: dict = {"user": sample_user}

        with patch(
            "bot.middlewares.subscription.check_access", new_callable=AsyncMock
        ) as mock_check:
            mock_check.side_effect = SubscriptionServiceError("DB down")

            result = await middleware(mock_handler, event, data)

        mock_handler.assert_called_once_with(event, data)
        assert result == "handler_result"

    async def test_proceeds_without_user_in_data(
        self, middleware, mock_handler
    ):
        """Test that middleware proceeds when no user is in data."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        data: dict = {}

        with patch(
            "bot.middlewares.subscription.check_access", new_callable=AsyncMock
        ) as mock_check:
            result = await middleware(mock_handler, event, data)

        mock_check.assert_not_called()
        mock_handler.assert_called_once_with(event, data)
        assert result == "handler_result"

    async def test_proceeds_when_user_is_none(
        self, middleware, mock_handler
    ):
        """Test that middleware proceeds when user is explicitly None."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        data: dict = {"user": None}

        with patch(
            "bot.middlewares.subscription.check_access", new_callable=AsyncMock
        ) as mock_check:
            result = await middleware(mock_handler, event, data)

        mock_check.assert_not_called()
        mock_handler.assert_called_once_with(event, data)
        assert result == "handler_result"

    async def test_callback_without_message_still_blocks(
        self, middleware, mock_handler, sample_user
    ):
        """Test paywall for callback with no message attribute."""
        from aiogram.types import CallbackQuery

        event = MagicMock(spec=CallbackQuery)
        event.answer = AsyncMock()
        event.message = None
        data: dict = {"user": sample_user}

        with (
            patch(
                "bot.middlewares.subscription.check_access",
                new_callable=AsyncMock,
            ) as mock_check,
            patch(
                "bot.middlewares.subscription.ProgressRepository",
            ),
        ):
            mock_check.return_value = False

            result = await middleware(mock_handler, event, data)

        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        assert result is None

    async def test_paywall_shows_progress_fallback_on_error(
        self, middleware, mock_handler, sample_user
    ):
        """Test paywall still works when progress fetch fails."""
        from aiogram.types import Message

        event = MagicMock(spec=Message)
        event.answer = AsyncMock()
        data: dict = {"user": sample_user}

        with (
            patch(
                "bot.middlewares.subscription.check_access",
                new_callable=AsyncMock,
            ) as mock_check,
            patch(
                "bot.middlewares.subscription.ProgressRepository",
            ) as mock_repo_cls,
        ):
            mock_check.return_value = False
            mock_repo_cls.return_value.get_by_user_id = AsyncMock(
                side_effect=Exception("DB error")
            )

            result = await middleware(mock_handler, event, data)

        mock_handler.assert_not_called()
        event.answer.assert_called_once()
        call_args = event.answer.call_args
        paywall_text = call_args[0][0]
        assert "Дневной лимит исчерпан" in paywall_text
        # Should still show base paywall without streak info
        assert "streak" not in paywall_text
        assert result is None
