"""Progress and streak tracking service."""

import logging
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from bot.core.config import settings
from bot.domain.entities.progress import Progress
from bot.repositories.progress_repository import ProgressRepository

logger = logging.getLogger(__name__)


class ProgressServiceError(Exception):
    """Base exception for progress service errors."""


async def record_answer(user_id: UUID) -> Progress:
    """Record that a user answered a question.

    Increments questions_today (with day-reset logic),
    increments total_questions_answered, and updates streak
    if the daily goal is reached.

    Args:
        user_id: The user's internal UUID.

    Returns:
        Updated Progress with current state.

    Raises:
        ProgressServiceError: If recording fails.
    """
    repo = ProgressRepository()
    today = datetime.now(UTC).date()

    try:
        progress, created = await repo.get_or_create(user_id)

        if created:
            logger.info("Created new progress record for user_id=%s", user_id)

        progress = await repo.increment_questions_today(user_id, today)

        # Check if daily goal was just reached (exactly at the goal)
        if progress.questions_today == settings.daily_goal:
            progress = await _update_streak_on_goal_reached(
                repo, user_id, progress, today
            )

        logger.info(
            "Recorded answer for user_id=%s: questions_today=%d, streak=%d",
            user_id,
            progress.questions_today,
            progress.current_streak,
        )
        return progress

    except ProgressServiceError:
        raise
    except Exception as e:
        error_msg = f"Failed to record answer for user_id={user_id}: {e}"
        logger.exception(error_msg)
        raise ProgressServiceError(error_msg) from e


async def _update_streak_on_goal_reached(
    repo: ProgressRepository,
    user_id: UUID,
    progress: Progress,
    today: date,
) -> Progress:
    """Update streak when user reaches daily goal.

    Streak increments if:
    - The goal was reached today and streak hasn't been updated today yet.

    Streak resets to 1 if:
    - The user missed a day (last streak update was >1 day ago).

    Args:
        repo: Progress repository instance.
        user_id: The user's internal UUID.
        progress: Current progress state.
        today: Current date.

    Returns:
        Updated Progress with new streak values.
    """
    streak_last_date = _get_streak_last_date(progress)

    if streak_last_date == today:
        # Streak already updated today, skip
        return progress

    if streak_last_date is not None and (today - streak_last_date) == timedelta(days=1):
        # Consecutive day — increment streak
        new_streak = progress.current_streak + 1
    else:
        # First time or missed a day — start/reset streak
        new_streak = 1

    new_longest = max(progress.longest_streak, new_streak)

    progress = await repo.update_streak(user_id, new_streak, new_longest)

    logger.info(
        "Updated streak for user_id=%s: current=%d, longest=%d",
        user_id,
        new_streak,
        new_longest,
    )
    return progress


def _get_streak_last_date(progress: Progress) -> date | None:
    """Extract the date when streak was last updated.

    Uses streak_updated_at if available, otherwise falls back
    to last_activity_date as a proxy.

    Args:
        progress: Current progress state.

    Returns:
        Date of last streak update, or None if never updated.
    """
    if progress.streak_updated_at is not None:
        dt = progress.streak_updated_at
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)
        if dt.tzinfo is None:
            return dt.date()
        return dt.astimezone(UTC).date()
    return None


def check_daily_goal(progress: Progress, daily_goal: int | None = None) -> bool:
    """Check if user has reached their daily goal.

    Args:
        progress: The user's progress record.
        daily_goal: Number of questions for the goal (defaults to settings.daily_goal).

    Returns:
        True if the daily goal has been reached.
    """
    goal = daily_goal if daily_goal is not None else settings.daily_goal
    return progress.has_reached_daily_goal(goal)


def check_milestone(progress: Progress) -> int | None:
    """Check if user has reached a streak milestone.

    Milestones: 7, 30, 100 days.

    Args:
        progress: The user's progress record.

    Returns:
        The milestone value if reached, None otherwise.
    """
    return progress.is_milestone_streak()
