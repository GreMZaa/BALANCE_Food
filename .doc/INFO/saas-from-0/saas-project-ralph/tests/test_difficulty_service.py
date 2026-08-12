"""Tests for adaptive difficulty service module."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.domain.entities.question import QuestionSession
from bot.services.difficulty_service import (
    DECREASE_THRESHOLD,
    INCREASE_THRESHOLD,
    PERFORMANCE_WINDOW,
    DifficultyServiceError,
    adjust_difficulty,
)


def _make_session(user_id, ai_score):
    """Helper to create a QuestionSession with a given score."""
    return QuestionSession(
        user_id=user_id,
        question_text="Test question",
        question_category=Category.LANGUAGE,
        question_difficulty=5,
        user_answer="Test answer",
        ai_score=ai_score,
    )


def _make_profile(user_id, grade=Grade.MIDDLE, difficulty=5):
    """Helper to create a UserProfile."""
    return UserProfile(
        user_id=user_id,
        grade=grade,
        current_difficulty=difficulty,
        specialty=Specialty.BACKEND,
    )


class TestAdjustDifficulty:
    """Tests for adjust_difficulty function."""

    async def test_increases_difficulty_when_avg_score_high(self):
        """Difficulty increases by 1 when average score >= INCREASE_THRESHOLD."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 9) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.MIDDLE, difficulty=5)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=9.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)
        mock_profile_repo.update_difficulty = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result == 6
        mock_profile_repo.update_difficulty.assert_awaited_once_with(user_id, 6)

    async def test_decreases_difficulty_when_avg_score_low(self):
        """Difficulty decreases by 1 when average score <= DECREASE_THRESHOLD."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 3) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.MIDDLE, difficulty=5)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=3.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)
        mock_profile_repo.update_difficulty = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result == 4
        mock_profile_repo.update_difficulty.assert_awaited_once_with(user_id, 4)

    async def test_no_change_when_avg_score_in_neutral_range(self):
        """No adjustment when average score is between thresholds."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 6) for _ in range(PERFORMANCE_WINDOW)]

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=6.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result is None
        mock_profile_repo.get_by_user_id.assert_not_awaited()

    async def test_no_change_when_not_enough_sessions(self):
        """No adjustment when fewer than PERFORMANCE_WINDOW scored sessions."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 9) for _ in range(3)]

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=9.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result is None

    async def test_no_change_when_no_scored_sessions(self):
        """No adjustment when there are no scored sessions at all."""
        user_id = uuid4()

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=None)

        mock_profile_repo = AsyncMock()

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result is None

    async def test_junior_cannot_exceed_max_difficulty(self):
        """Junior grade difficulty is capped at 4."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 9) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.JUNIOR, difficulty=4)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=9.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        # Already at max for Junior, so no change
        assert result is None
        mock_profile_repo.update_difficulty.assert_not_awaited()

    async def test_junior_cannot_go_below_min_difficulty(self):
        """Junior grade difficulty is floored at 1."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 2) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.JUNIOR, difficulty=1)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=2.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        # Already at min for Junior, so no change
        assert result is None
        mock_profile_repo.update_difficulty.assert_not_awaited()

    async def test_senior_difficulty_range(self):
        """Senior grade difficulty stays within [5, 10] range."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 3) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.SENIOR, difficulty=5)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=3.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        # Already at min for Senior (5), cannot decrease further
        assert result is None

    async def test_senior_can_increase_to_max(self):
        """Senior grade difficulty can increase up to 10."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 9) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.SENIOR, difficulty=9)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=9.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)
        mock_profile_repo.update_difficulty = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result == 10
        mock_profile_repo.update_difficulty.assert_awaited_once_with(user_id, 10)

    async def test_no_profile_returns_none(self):
        """Returns None if the user has no profile."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 9) for _ in range(PERFORMANCE_WINDOW)]

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=9.0)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result is None

    async def test_exact_increase_threshold(self):
        """Difficulty increases when average is exactly at INCREASE_THRESHOLD."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 8) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.MIDDLE, difficulty=5)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=INCREASE_THRESHOLD)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)
        mock_profile_repo.update_difficulty = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result == 6

    async def test_exact_decrease_threshold(self):
        """Difficulty decreases when average is exactly at DECREASE_THRESHOLD."""
        user_id = uuid4()
        sessions = [_make_session(user_id, 4) for _ in range(PERFORMANCE_WINDOW)]
        profile = _make_profile(user_id, Grade.MIDDLE, difficulty=5)

        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(return_value=DECREASE_THRESHOLD)
        mock_session_repo.get_last_n_by_user = AsyncMock(return_value=sessions)

        mock_profile_repo = AsyncMock()
        mock_profile_repo.get_by_user_id = AsyncMock(return_value=profile)
        mock_profile_repo.update_difficulty = AsyncMock(return_value=profile)

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            patch(
                "bot.services.difficulty_service.ProfileRepository",
                return_value=mock_profile_repo,
            ),
        ):
            result = await adjust_difficulty(user_id)

        assert result == 4

    async def test_error_wraps_in_difficulty_service_error(self):
        """Exceptions are wrapped in DifficultyServiceError."""
        mock_session_repo = AsyncMock()
        mock_session_repo.get_average_score = AsyncMock(side_effect=Exception("DB down"))

        with (
            patch(
                "bot.services.difficulty_service.SessionRepository",
                return_value=mock_session_repo,
            ),
            pytest.raises(DifficultyServiceError) as exc_info,
        ):
            await adjust_difficulty(uuid4())

        assert "Failed to adjust difficulty" in str(exc_info.value)


class TestConstants:
    """Tests for module constants."""

    def test_performance_window_is_5(self):
        assert PERFORMANCE_WINDOW == 5

    def test_increase_threshold_is_8(self):
        assert INCREASE_THRESHOLD == 8.0

    def test_decrease_threshold_is_4(self):
        assert DECREASE_THRESHOLD == 4.0


class TestImports:
    """Tests for module imports."""

    def test_import_from_services_init(self):
        """Test that difficulty service can be imported from services."""
        from bot.services import DifficultyServiceError, adjust_difficulty

        assert adjust_difficulty is not None
        assert DifficultyServiceError is not None

    def test_difficulty_service_error_is_exception(self):
        """Test DifficultyServiceError inherits from Exception."""
        error = DifficultyServiceError("test")
        assert isinstance(error, Exception)
        assert str(error) == "test"
