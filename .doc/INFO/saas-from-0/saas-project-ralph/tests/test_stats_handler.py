"""Tests for /stats command handler."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.domain.entities.progress import Progress
from bot.domain.entities.user import User
from bot.handlers.stats import (
    _format_stats_message,
    _progress_bar,
    cmd_stats,
    router,
)

# --- Fixtures ---

def _make_user(**overrides):
    defaults = {
        "id": uuid4(),
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "language_code": "ru",
    }
    defaults.update(overrides)
    return User(**defaults)


def _make_profile(user_id=None, **overrides):
    defaults = {
        "id": uuid4(),
        "user_id": user_id or uuid4(),
        "specialty": Specialty.BACKEND,
        "grade": Grade.MIDDLE,
        "tech_stack": ["Python", "Go"],
        "focus_areas": [Category.DATABASES, Category.SYSTEM_DESIGN],
        "current_difficulty": 5,
    }
    defaults.update(overrides)
    return UserProfile(**defaults)


def _make_progress(user_id=None, **overrides):
    defaults = {
        "id": uuid4(),
        "user_id": user_id or uuid4(),
        "current_streak": 3,
        "longest_streak": 10,
        "total_questions_answered": 42,
        "questions_today": 2,
    }
    defaults.update(overrides)
    return Progress(**defaults)


def _make_message(telegram_id=123456789, first_name="Test"):
    message = AsyncMock()
    from_user = MagicMock()
    from_user.id = telegram_id
    from_user.first_name = first_name
    message.from_user = from_user
    message.answer = AsyncMock()
    return message


# --- Router tests ---

class TestStatsRouter:
    """Tests for stats router configuration."""

    def test_router_has_correct_name(self):
        assert router.name == "stats"

    def test_router_has_message_handler(self):
        assert len(router.message.handlers) > 0


# --- Progress bar tests ---

class TestProgressBar:
    """Tests for _progress_bar helper."""

    def test_empty_bar(self):
        result = _progress_bar(0, 5, length=5)
        assert "0/5" in result

    def test_full_bar(self):
        result = _progress_bar(5, 5, length=5)
        assert "5/5" in result

    def test_partial_bar(self):
        result = _progress_bar(3, 10, length=10)
        assert "3/10" in result

    def test_over_limit_clamped(self):
        result = _progress_bar(8, 5, length=5)
        assert "5/5" in result

    def test_zero_total(self):
        result = _progress_bar(0, 0, length=5)
        assert "0/0" in result


# --- Format message tests ---

class TestFormatStatsMessage:
    """Tests for _format_stats_message."""

    def test_contains_name(self):
        text = _format_stats_message(
            first_name="Alice",
            grade=Grade.JUNIOR,
            current_difficulty=2,
            difficulty_range=(1, 4),
            current_streak=0,
            longest_streak=0,
            total_questions=0,
            questions_today=0,
            average_score=None,
        )
        assert "Alice" in text

    def test_grade_displayed(self):
        text = _format_stats_message(
            first_name="Bob",
            grade=Grade.SENIOR,
            current_difficulty=7,
            difficulty_range=(5, 10),
            current_streak=5,
            longest_streak=20,
            total_questions=100,
            questions_today=3,
            average_score=8.5,
        )
        assert "Senior" in text

    def test_streak_info(self):
        text = _format_stats_message(
            first_name="Test",
            grade=Grade.MIDDLE,
            current_difficulty=5,
            difficulty_range=(3, 7),
            current_streak=7,
            longest_streak=14,
            total_questions=50,
            questions_today=1,
            average_score=6.0,
        )
        assert "7" in text
        assert "14" in text

    def test_average_score_high(self):
        text = _format_stats_message(
            first_name="Test",
            grade=Grade.MIDDLE,
            current_difficulty=5,
            difficulty_range=(3, 7),
            current_streak=0,
            longest_streak=0,
            total_questions=10,
            questions_today=0,
            average_score=9.0,
        )
        # Green indicator for high score
        assert "\U0001f7e2" in text
        assert "9.0" in text

    def test_average_score_medium(self):
        text = _format_stats_message(
            first_name="Test",
            grade=Grade.MIDDLE,
            current_difficulty=5,
            difficulty_range=(3, 7),
            current_streak=0,
            longest_streak=0,
            total_questions=10,
            questions_today=0,
            average_score=6.0,
        )
        # Yellow indicator for medium score
        assert "\U0001f7e1" in text

    def test_average_score_low(self):
        text = _format_stats_message(
            first_name="Test",
            grade=Grade.MIDDLE,
            current_difficulty=5,
            difficulty_range=(3, 7),
            current_streak=0,
            longest_streak=0,
            total_questions=10,
            questions_today=0,
            average_score=3.5,
        )
        # Red indicator for low score
        assert "\U0001f534" in text

    def test_no_average_score(self):
        text = _format_stats_message(
            first_name="Test",
            grade=Grade.JUNIOR,
            current_difficulty=2,
            difficulty_range=(1, 4),
            current_streak=0,
            longest_streak=0,
            total_questions=0,
            questions_today=0,
            average_score=None,
        )
        assert "\u043e\u0442\u0432\u0435\u0442\u044c" in text.lower() or "\u0431\u0430\u043b\u043b" in text.lower()

    def test_fallback_name_when_none(self):
        text = _format_stats_message(
            first_name=None,
            grade=Grade.JUNIOR,
            current_difficulty=2,
            difficulty_range=(1, 4),
            current_streak=0,
            longest_streak=0,
            total_questions=0,
            questions_today=0,
            average_score=None,
        )
        assert "User" in text

    def test_difficulty_range_displayed(self):
        text = _format_stats_message(
            first_name="Test",
            grade=Grade.SENIOR,
            current_difficulty=8,
            difficulty_range=(5, 10),
            current_streak=0,
            longest_streak=0,
            total_questions=0,
            questions_today=0,
            average_score=None,
        )
        assert "5" in text
        assert "10" in text


# --- Handler tests ---

class TestCmdStats:
    """Tests for cmd_stats handler."""

    async def test_returns_early_without_from_user(self):
        message = AsyncMock()
        message.from_user = None
        message.answer = AsyncMock()

        await cmd_stats(message)

        message.answer.assert_not_called()

    async def test_prompts_start_when_no_user(self):
        message = _make_message()

        await cmd_stats(message, user=None)

        message.answer.assert_called_once()
        text = message.answer.call_args[0][0]
        assert "/start" in text

    async def test_prompts_onboarding_when_no_profile(self):
        user = _make_user()
        message = _make_message()

        with patch("bot.handlers.stats.ProfileRepository") as p_cls:
            p_repo = MagicMock()
            p_repo.get_by_user_id = AsyncMock(return_value=None)
            p_cls.return_value = p_repo

            await cmd_stats(message, user=user)

        message.answer.assert_called_once()
        text = message.answer.call_args[0][0]
        assert "/start" in text

    async def test_shows_stats_with_progress(self):
        user = _make_user()
        profile = _make_profile(user_id=user.id, grade=Grade.MIDDLE)
        progress = _make_progress(user_id=user.id, current_streak=5, total_questions_answered=20)

        message = _make_message()

        with (
            patch("bot.handlers.stats.ProfileRepository") as p_cls,
            patch("bot.handlers.stats.ProgressRepository") as pr_cls,
            patch("bot.handlers.stats.SessionRepository") as s_cls,
        ):
            p_repo = MagicMock()
            p_repo.get_by_user_id = AsyncMock(return_value=profile)
            p_cls.return_value = p_repo

            pr_repo = MagicMock()
            pr_repo.get_by_user_id = AsyncMock(return_value=progress)
            pr_cls.return_value = pr_repo

            s_repo = MagicMock()
            s_repo.get_average_score = AsyncMock(return_value=7.5)
            s_cls.return_value = s_repo

            await cmd_stats(message, user=user)

        message.answer.assert_called_once()
        text = message.answer.call_args[0][0]
        assert "Middle" in text
        assert "7.5" in text

    async def test_shows_stats_without_progress(self):
        user = _make_user()
        profile = _make_profile(user_id=user.id)

        message = _make_message()

        with (
            patch("bot.handlers.stats.ProfileRepository") as p_cls,
            patch("bot.handlers.stats.ProgressRepository") as pr_cls,
            patch("bot.handlers.stats.SessionRepository") as s_cls,
        ):
            p_repo = MagicMock()
            p_repo.get_by_user_id = AsyncMock(return_value=profile)
            p_cls.return_value = p_repo

            pr_repo = MagicMock()
            pr_repo.get_by_user_id = AsyncMock(return_value=None)
            pr_cls.return_value = pr_repo

            s_repo = MagicMock()
            s_repo.get_average_score = AsyncMock(return_value=None)
            s_cls.return_value = s_repo

            await cmd_stats(message, user=user)

        message.answer.assert_called_once()
        text = message.answer.call_args[0][0]
        # Should still display with zero values
        assert "0" in text

    async def test_average_score_uses_last_10(self):
        user = _make_user()
        profile = _make_profile(user_id=user.id)
        progress = _make_progress(user_id=user.id)

        message = _make_message()

        with (
            patch("bot.handlers.stats.ProfileRepository") as p_cls,
            patch("bot.handlers.stats.ProgressRepository") as pr_cls,
            patch("bot.handlers.stats.SessionRepository") as s_cls,
        ):
            p_repo = MagicMock()
            p_repo.get_by_user_id = AsyncMock(return_value=profile)
            p_cls.return_value = p_repo

            pr_repo = MagicMock()
            pr_repo.get_by_user_id = AsyncMock(return_value=progress)
            pr_cls.return_value = pr_repo

            s_repo = MagicMock()
            s_repo.get_average_score = AsyncMock(return_value=6.0)
            s_cls.return_value = s_repo

            await cmd_stats(message, user=user)

            s_repo.get_average_score.assert_called_once_with(user.id, last_n=10)
