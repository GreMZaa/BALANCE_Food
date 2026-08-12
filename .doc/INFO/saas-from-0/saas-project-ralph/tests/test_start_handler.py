"""Tests for start command handler."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.user import User
from bot.handlers.start import (
    _get_display_name,
    _send_new_user_welcome,
    _send_returning_user_welcome,
    cmd_start,
    router,
)


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user."""
    user = MagicMock()
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    user.language_code = "en"
    return user


@pytest.fixture
def mock_message(mock_telegram_user):
    """Create a mock Telegram message."""
    message = AsyncMock()
    message.from_user = mock_telegram_user
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Create a mock FSMContext."""
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


@pytest.fixture
def sample_user():
    """Create a sample User domain model with equal timestamps (new user)."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)
    return User(
        id=uuid4(),
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
        created_at=now,
        updated_at=now,
    )


class TestStartRouter:
    """Tests for start router configuration."""

    def test_router_has_correct_name(self):
        """Test that router has correct name."""
        assert router.name == "start"

    def test_router_has_message_handler(self):
        """Test that router has registered message handler."""
        # Check that there's at least one message handler
        assert len(router.message.handlers) > 0


class TestCmdStart:
    """Tests for cmd_start handler."""

    async def test_cmd_start_no_from_user(self, mock_state):
        """Test that handler returns early when from_user is None."""
        message = AsyncMock()
        message.from_user = None
        message.answer = AsyncMock()

        await cmd_start(message, mock_state)

        message.answer.assert_not_called()

    async def test_cmd_start_new_user(self, mock_message, mock_state, sample_user):
        """Test cmd_start sends welcome for new user (no profile, timestamps equal)."""
        with (
            patch("bot.handlers.start.ProfileRepository") as mock_profile_repo_cls,
            patch(
                "bot.handlers.onboarding.start_onboarding", new_callable=AsyncMock
            ),
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_profile_repo_cls.return_value = mock_profile_repo

            # User injected by middleware — created_at == updated_at signals new user
            await cmd_start(mock_message, mock_state, user=sample_user)

            mock_profile_repo.get_by_user_id.assert_called_once_with(sample_user.id)
            # First answer is the welcome message
            assert mock_message.answer.call_count >= 1

            # Verify welcome message contains expected content
            call_args = mock_message.answer.call_args_list[0]
            message_text = call_args[0][0]
            assert "Алоха" in message_text
            assert "Interview Trainer Bot" in message_text
            assert "Добро пожаловать" in message_text

    async def test_cmd_start_existing_user_with_profile(
        self, mock_message, mock_state, sample_user
    ):
        """Test cmd_start sends returning message for user with profile."""
        mock_profile = MagicMock()

        with patch("bot.handlers.start.ProfileRepository") as mock_profile_repo_cls:
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=mock_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await cmd_start(mock_message, mock_state, user=sample_user)

            mock_message.answer.assert_called_once()

            call_args = mock_message.answer.call_args
            message_text = call_args[0][0]
            assert "С возвращением" in message_text
            assert "/practice" in message_text
            assert "/stats" in message_text

    async def test_cmd_start_existing_user_without_profile(
        self, mock_message, mock_state, sample_user
    ):
        """Test cmd_start sends onboarding prompt for user without profile."""
        from datetime import timedelta

        # Make updated_at differ from created_at so the user is not treated as new
        sample_user.updated_at = sample_user.created_at + timedelta(seconds=1)

        with (
            patch("bot.handlers.start.ProfileRepository") as mock_profile_repo_cls,
            patch(
                "bot.handlers.onboarding.start_onboarding", new_callable=AsyncMock
            ),
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await cmd_start(mock_message, mock_state, user=sample_user)

            # First answer is the welcome message
            assert mock_message.answer.call_count >= 1

            call_args = mock_message.answer.call_args_list[0]
            message_text = call_args[0][0]
            assert "С возвращением" in message_text
            assert "не завершил" in message_text or "профил" in message_text


class TestSendNewUserWelcome:
    """Tests for _send_new_user_welcome function."""

    async def test_send_new_user_welcome_with_name(
        self, mock_message, mock_state, sample_user
    ):
        """Test new user welcome contains user's name."""
        with patch(
            "bot.handlers.onboarding.start_onboarding", new_callable=AsyncMock
        ):
            await _send_new_user_welcome(mock_message, sample_user, mock_state)

        # First call is the welcome message
        call_args = mock_message.answer.call_args_list[0]
        message_text = call_args[0][0]

        assert "Test" in message_text
        assert "Алоха" in message_text
        assert "Interview Trainer Bot" in message_text

    async def test_send_new_user_welcome_features_listed(
        self, mock_message, mock_state, sample_user
    ):
        """Test new user welcome lists bot features."""
        with patch(
            "bot.handlers.onboarding.start_onboarding", new_callable=AsyncMock
        ):
            await _send_new_user_welcome(mock_message, sample_user, mock_state)

        call_args = mock_message.answer.call_args_list[0]
        message_text = call_args[0][0]

        assert "вопрос" in message_text.lower()
        assert "фидбэк" in message_text.lower() or "оценив" in message_text.lower()
        assert "прогресс" in message_text.lower() or "streak" in message_text.lower()


class TestSendReturningUserWelcome:
    """Tests for _send_returning_user_welcome function."""

    async def test_send_returning_user_welcome_with_profile(
        self, mock_message, sample_user
    ):
        """Test returning user welcome with profile mentions commands."""
        await _send_returning_user_welcome(mock_message, sample_user, has_profile=True)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        message_text = call_args[0][0]

        assert "С возвращением" in message_text
        assert "/practice" in message_text
        assert "/stats" in message_text

    async def test_send_returning_user_welcome_without_profile(
        self, mock_message, sample_user
    ):
        """Test returning user welcome without profile prompts onboarding."""
        await _send_returning_user_welcome(mock_message, sample_user, has_profile=False)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        message_text = call_args[0][0]

        assert "С возвращением" in message_text
        assert "профил" in message_text.lower()


class TestGetDisplayName:
    """Tests for _get_display_name function."""

    def test_get_display_name_from_user_first_name(self, sample_user, mock_telegram_user):
        """Test display name uses user's first_name from database."""
        result = _get_display_name(sample_user, mock_telegram_user)
        assert result == "Test"

    def test_get_display_name_from_telegram_first_name(self, mock_telegram_user):
        """Test display name uses Telegram first_name when DB has none."""
        user = User(telegram_id=123456789)
        mock_telegram_user.first_name = "TelegramName"

        result = _get_display_name(user, mock_telegram_user)
        assert result == "TelegramName"

    def test_get_display_name_from_username(self):
        """Test display name uses username when no first_name available."""
        user = User(telegram_id=123456789, username="myusername")
        telegram_user = MagicMock()
        telegram_user.first_name = None

        result = _get_display_name(user, telegram_user)
        assert result == "myusername"

    def test_get_display_name_fallback(self):
        """Test display name falls back to 'друг' when nothing available."""
        user = User(telegram_id=123456789)
        telegram_user = MagicMock()
        telegram_user.first_name = None

        result = _get_display_name(user, telegram_user)
        assert result == "друг"

    def test_get_display_name_with_none_telegram_user(self, sample_user):
        """Test display name handles None telegram_user."""
        result = _get_display_name(sample_user, None)
        assert result == "Test"

    def test_get_display_name_empty_first_name_uses_username(self):
        """Test display name uses username when first_name is empty string."""
        user = User(telegram_id=123456789, first_name="", username="myuser")
        telegram_user = MagicMock()
        telegram_user.first_name = ""

        result = _get_display_name(user, telegram_user)
        # Empty string is falsy, so should fall through to username
        assert result == "myuser"
