"""Tests for progress service module."""

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.progress import Progress
from bot.services.progress_service import (
    ProgressServiceError,
    _get_streak_last_date,
    _update_streak_on_goal_reached,
    check_daily_goal,
    check_milestone,
    record_answer,
)


@pytest.fixture
def sample_progress():
    """Create a sample Progress for testing."""
    return Progress(
        user_id=uuid4(),
        current_streak=3,
        longest_streak=10,
        total_questions_answered=42,
        questions_today=4,
        last_activity_date=date(2026, 1, 30),
        streak_updated_at=datetime(2026, 1, 30, 12, 0, 0, tzinfo=UTC),
    )


@pytest.fixture
def fresh_progress():
    """Create a fresh Progress with zero values."""
    return Progress(
        user_id=uuid4(),
        current_streak=0,
        longest_streak=0,
        total_questions_answered=0,
        questions_today=0,
        last_activity_date=None,
        streak_updated_at=None,
    )


class TestRecordAnswer:
    """Tests for record_answer function."""

    async def test_record_answer_existing_progress(self, sample_progress: Progress):
        """Test recording answer for user with existing progress."""
        user_id = sample_progress.user_id
        incremented = Progress(
            user_id=user_id,
            current_streak=3,
            longest_streak=10,
            total_questions_answered=43,
            questions_today=5,
            last_activity_date=date(2026, 1, 30),
            streak_updated_at=datetime(2026, 1, 30, 12, 0, 0, tzinfo=UTC),
        )

        # After streak update
        streaked = Progress(
            user_id=user_id,
            current_streak=4,
            longest_streak=10,
            total_questions_answered=43,
            questions_today=5,
            last_activity_date=date(2026, 1, 30),
            streak_updated_at=datetime(2026, 1, 30, 14, 0, 0, tzinfo=UTC),
        )

        mock_repo = AsyncMock()
        mock_repo.get_or_create = AsyncMock(return_value=(sample_progress, False))
        mock_repo.increment_questions_today = AsyncMock(return_value=incremented)
        mock_repo.update_streak = AsyncMock(return_value=streaked)

        with patch(
            "bot.services.progress_service.ProgressRepository",
            return_value=mock_repo,
        ):
            result = await record_answer(user_id)

        assert result.questions_today == 5
        mock_repo.get_or_create.assert_awaited_once_with(user_id)
        mock_repo.increment_questions_today.assert_awaited_once()

    async def test_record_answer_creates_progress_for_new_user(self):
        """Test that record_answer creates progress for a new user."""
        user_id = uuid4()
        new_progress = Progress(user_id=user_id)
        incremented = Progress(
            user_id=user_id,
            total_questions_answered=1,
            questions_today=1,
            last_activity_date=date.today(),
        )

        mock_repo = AsyncMock()
        mock_repo.get_or_create = AsyncMock(return_value=(new_progress, True))
        mock_repo.increment_questions_today = AsyncMock(return_value=incremented)

        with patch(
            "bot.services.progress_service.ProgressRepository",
            return_value=mock_repo,
        ):
            result = await record_answer(user_id)

        assert result.questions_today == 1
        mock_repo.get_or_create.assert_awaited_once_with(user_id)

    async def test_record_answer_triggers_streak_at_daily_goal(self):
        """Test that reaching daily goal triggers streak update."""
        user_id = uuid4()
        fixed_now = datetime(2026, 1, 30, 14, 0, 0, tzinfo=UTC)
        fixed_today = fixed_now.date()
        existing = Progress(
            user_id=user_id,
            current_streak=2,
            longest_streak=5,
            total_questions_answered=10,
            questions_today=4,
            last_activity_date=fixed_today,
            streak_updated_at=datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC),
        )
        # After increment: questions_today becomes 5 (== daily_goal)
        incremented = Progress(
            user_id=user_id,
            current_streak=2,
            longest_streak=5,
            total_questions_answered=11,
            questions_today=5,
            last_activity_date=fixed_today,
            streak_updated_at=datetime(2026, 1, 29, 12, 0, 0, tzinfo=UTC),
        )
        streaked = Progress(
            user_id=user_id,
            current_streak=3,
            longest_streak=5,
            total_questions_answered=11,
            questions_today=5,
            last_activity_date=fixed_today,
            streak_updated_at=fixed_now,
        )

        mock_repo = AsyncMock()
        mock_repo.get_or_create = AsyncMock(return_value=(existing, False))
        mock_repo.increment_questions_today = AsyncMock(return_value=incremented)
        mock_repo.update_streak = AsyncMock(return_value=streaked)

        from unittest.mock import MagicMock

        mock_settings = MagicMock()
        mock_settings.daily_goal = 5

        # Mock datetime.now to return a fixed time on 2026-01-30
        mock_datetime = MagicMock(wraps=datetime)
        mock_datetime.now = MagicMock(return_value=fixed_now)

        with (
            patch(
                "bot.services.progress_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch(
                "bot.services.progress_service.settings",
                mock_settings,
            ),
            patch(
                "bot.services.progress_service.datetime",
                mock_datetime,
            ),
        ):
            result = await record_answer(user_id)

        assert result.current_streak == 3
        mock_repo.update_streak.assert_awaited_once()

    async def test_record_answer_no_streak_before_daily_goal(self):
        """Test that streak is NOT updated when below daily goal."""
        user_id = uuid4()
        existing = Progress(
            user_id=user_id,
            current_streak=2,
            longest_streak=5,
            total_questions_answered=10,
            questions_today=2,
        )
        incremented = Progress(
            user_id=user_id,
            current_streak=2,
            longest_streak=5,
            total_questions_answered=11,
            questions_today=3,
            last_activity_date=date(2026, 1, 30),
        )

        mock_repo = AsyncMock()
        mock_repo.get_or_create = AsyncMock(return_value=(existing, False))
        mock_repo.increment_questions_today = AsyncMock(return_value=incremented)

        with (
            patch(
                "bot.services.progress_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.progress_service.settings") as mock_settings,
        ):
            mock_settings.daily_goal = 5
            result = await record_answer(user_id)

        assert result.current_streak == 2
        mock_repo.update_streak.assert_not_awaited()

    async def test_record_answer_no_streak_after_daily_goal(self):
        """Test that streak is NOT updated when already past daily goal."""
        user_id = uuid4()
        existing = Progress(
            user_id=user_id,
            current_streak=3,
            longest_streak=5,
            total_questions_answered=15,
            questions_today=5,
        )
        # After increment: questions_today becomes 6 (> daily_goal, not ==)
        incremented = Progress(
            user_id=user_id,
            current_streak=3,
            longest_streak=5,
            total_questions_answered=16,
            questions_today=6,
            last_activity_date=date(2026, 1, 30),
        )

        mock_repo = AsyncMock()
        mock_repo.get_or_create = AsyncMock(return_value=(existing, False))
        mock_repo.increment_questions_today = AsyncMock(return_value=incremented)

        with (
            patch(
                "bot.services.progress_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.progress_service.settings") as mock_settings,
        ):
            mock_settings.daily_goal = 5
            result = await record_answer(user_id)

        assert result.questions_today == 6
        mock_repo.update_streak.assert_not_awaited()

    async def test_record_answer_error_raises_progress_service_error(self):
        """Test that errors are wrapped in ProgressServiceError."""
        mock_repo = AsyncMock()
        mock_repo.get_or_create = AsyncMock(side_effect=Exception("DB down"))

        with (
            patch(
                "bot.services.progress_service.ProgressRepository",
                return_value=mock_repo,
            ),
            pytest.raises(ProgressServiceError) as exc_info,
        ):
            await record_answer(uuid4())

        assert "Failed to record answer" in str(exc_info.value)


class TestUpdateStreakOnGoalReached:
    """Tests for _update_streak_on_goal_reached."""

    async def test_consecutive_day_increments_streak(self):
        """Test streak increments for consecutive day."""
        user_id = uuid4()
        today = date(2026, 1, 30)
        yesterday = datetime(2026, 1, 29, 15, 0, 0, tzinfo=UTC)

        progress = Progress(
            user_id=user_id,
            current_streak=5,
            longest_streak=10,
            questions_today=5,
            streak_updated_at=yesterday,
        )
        updated = Progress(
            user_id=user_id,
            current_streak=6,
            longest_streak=10,
            questions_today=5,
            streak_updated_at=datetime(2026, 1, 30, 14, 0, 0, tzinfo=UTC),
        )

        mock_repo = AsyncMock()
        mock_repo.update_streak = AsyncMock(return_value=updated)

        result = await _update_streak_on_goal_reached(
            mock_repo, user_id, progress, today
        )

        assert result.current_streak == 6
        mock_repo.update_streak.assert_awaited_once_with(user_id, 6, 10)

    async def test_missed_day_resets_streak_to_1(self):
        """Test streak resets to 1 if user missed a day."""
        user_id = uuid4()
        today = date(2026, 1, 30)
        two_days_ago = datetime(2026, 1, 28, 15, 0, 0, tzinfo=UTC)

        progress = Progress(
            user_id=user_id,
            current_streak=5,
            longest_streak=10,
            questions_today=5,
            streak_updated_at=two_days_ago,
        )
        updated = Progress(
            user_id=user_id,
            current_streak=1,
            longest_streak=10,
            questions_today=5,
            streak_updated_at=datetime(2026, 1, 30, 14, 0, 0, tzinfo=UTC),
        )

        mock_repo = AsyncMock()
        mock_repo.update_streak = AsyncMock(return_value=updated)

        result = await _update_streak_on_goal_reached(
            mock_repo, user_id, progress, today
        )

        assert result.current_streak == 1
        mock_repo.update_streak.assert_awaited_once_with(user_id, 1, 10)

    async def test_first_streak_starts_at_1(self):
        """Test first ever streak starts at 1."""
        user_id = uuid4()
        today = date(2026, 1, 30)

        progress = Progress(
            user_id=user_id,
            current_streak=0,
            longest_streak=0,
            questions_today=5,
            streak_updated_at=None,
        )
        updated = Progress(
            user_id=user_id,
            current_streak=1,
            longest_streak=1,
            questions_today=5,
            streak_updated_at=datetime(2026, 1, 30, 14, 0, 0, tzinfo=UTC),
        )

        mock_repo = AsyncMock()
        mock_repo.update_streak = AsyncMock(return_value=updated)

        result = await _update_streak_on_goal_reached(
            mock_repo, user_id, progress, today
        )

        assert result.current_streak == 1
        mock_repo.update_streak.assert_awaited_once_with(user_id, 1, 1)

    async def test_streak_already_updated_today_skips(self):
        """Test that streak is not updated twice on the same day."""
        user_id = uuid4()
        today = date(2026, 1, 30)

        progress = Progress(
            user_id=user_id,
            current_streak=5,
            longest_streak=10,
            questions_today=5,
            streak_updated_at=datetime(2026, 1, 30, 10, 0, 0, tzinfo=UTC),
        )

        mock_repo = AsyncMock()

        result = await _update_streak_on_goal_reached(
            mock_repo, user_id, progress, today
        )

        assert result is progress
        mock_repo.update_streak.assert_not_awaited()

    async def test_new_longest_streak_is_tracked(self):
        """Test that longest_streak is updated when surpassed."""
        user_id = uuid4()
        today = date(2026, 1, 30)
        yesterday = datetime(2026, 1, 29, 15, 0, 0, tzinfo=UTC)

        progress = Progress(
            user_id=user_id,
            current_streak=10,
            longest_streak=10,
            questions_today=5,
            streak_updated_at=yesterday,
        )
        updated = Progress(
            user_id=user_id,
            current_streak=11,
            longest_streak=11,
            questions_today=5,
        )

        mock_repo = AsyncMock()
        mock_repo.update_streak = AsyncMock(return_value=updated)

        result = await _update_streak_on_goal_reached(
            mock_repo, user_id, progress, today
        )

        mock_repo.update_streak.assert_awaited_once_with(user_id, 11, 11)
        assert result.current_streak == 11


class TestGetStreakLastDate:
    """Tests for _get_streak_last_date helper."""

    def test_with_aware_datetime(self):
        """Test extracting date from timezone-aware streak_updated_at."""
        progress = Progress(
            user_id=uuid4(),
            streak_updated_at=datetime(2026, 1, 30, 15, 0, 0, tzinfo=UTC),
        )
        assert _get_streak_last_date(progress) == date(2026, 1, 30)

    def test_with_string_datetime(self):
        """Test extracting date from string streak_updated_at."""
        progress = Progress(
            user_id=uuid4(),
            streak_updated_at="2026-01-30T15:00:00+00:00",
        )
        assert _get_streak_last_date(progress) == date(2026, 1, 30)

    def test_with_naive_datetime(self):
        """Test extracting date from naive datetime."""
        progress = Progress(
            user_id=uuid4(),
            streak_updated_at=datetime(2026, 1, 30, 15, 0, 0),
        )
        assert _get_streak_last_date(progress) == date(2026, 1, 30)

    def test_with_none(self):
        """Test returns None when streak_updated_at is None."""
        progress = Progress(user_id=uuid4(), streak_updated_at=None)
        assert _get_streak_last_date(progress) is None


class TestCheckDailyGoal:
    """Tests for check_daily_goal function."""

    def test_goal_not_reached(self):
        """Test returns False when below goal."""
        progress = Progress(user_id=uuid4(), questions_today=3)
        with patch("bot.services.progress_service.settings") as mock_settings:
            mock_settings.daily_goal = 5
            assert check_daily_goal(progress) is False

    def test_goal_reached_exactly(self):
        """Test returns True when exactly at goal."""
        progress = Progress(user_id=uuid4(), questions_today=5)
        with patch("bot.services.progress_service.settings") as mock_settings:
            mock_settings.daily_goal = 5
            assert check_daily_goal(progress) is True

    def test_goal_exceeded(self):
        """Test returns True when above goal."""
        progress = Progress(user_id=uuid4(), questions_today=7)
        with patch("bot.services.progress_service.settings") as mock_settings:
            mock_settings.daily_goal = 5
            assert check_daily_goal(progress) is True

    def test_custom_goal(self):
        """Test with explicitly passed daily_goal."""
        progress = Progress(user_id=uuid4(), questions_today=3)
        assert check_daily_goal(progress, daily_goal=3) is True

    def test_zero_questions(self):
        """Test with zero questions."""
        progress = Progress(user_id=uuid4(), questions_today=0)
        with patch("bot.services.progress_service.settings") as mock_settings:
            mock_settings.daily_goal = 5
            assert check_daily_goal(progress) is False


class TestCheckMilestone:
    """Tests for check_milestone function."""

    def test_milestone_7(self):
        """Test 7-day milestone detected."""
        progress = Progress(user_id=uuid4(), current_streak=7)
        assert check_milestone(progress) == 7

    def test_milestone_30(self):
        """Test 30-day milestone detected."""
        progress = Progress(user_id=uuid4(), current_streak=30)
        assert check_milestone(progress) == 30

    def test_milestone_100(self):
        """Test 100-day milestone detected."""
        progress = Progress(user_id=uuid4(), current_streak=100)
        assert check_milestone(progress) == 100

    def test_no_milestone(self):
        """Test non-milestone streak returns None."""
        progress = Progress(user_id=uuid4(), current_streak=5)
        assert check_milestone(progress) is None

    def test_zero_streak(self):
        """Test zero streak is not a milestone."""
        progress = Progress(user_id=uuid4(), current_streak=0)
        assert check_milestone(progress) is None


class TestImports:
    """Tests for module imports."""

    def test_import_from_services_init(self):
        """Test that progress service functions can be imported from services."""
        from bot.services import (
            ProgressServiceError,
            check_daily_goal,
            check_milestone,
            record_answer,
        )

        assert record_answer is not None
        assert check_daily_goal is not None
        assert check_milestone is not None
        assert ProgressServiceError is not None

    def test_progress_service_error_is_exception(self):
        """Test ProgressServiceError inherits from Exception."""
        error = ProgressServiceError("test")
        assert isinstance(error, Exception)
        assert str(error) == "test"
