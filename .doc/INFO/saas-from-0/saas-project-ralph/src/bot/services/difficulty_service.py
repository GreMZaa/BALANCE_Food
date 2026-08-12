"""Adaptive difficulty adjustment service.

Analyzes user's recent performance and adjusts question difficulty
to keep the challenge level appropriate for their skill.
"""

import logging
from uuid import UUID

from bot.repositories.profile_repository import ProfileRepository
from bot.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)

PERFORMANCE_WINDOW = 5
INCREASE_THRESHOLD = 8.0
DECREASE_THRESHOLD = 4.0


class DifficultyServiceError(Exception):
    """Base exception for difficulty service errors."""


async def adjust_difficulty(user_id: UUID) -> int | None:
    """Adjust difficulty based on the user's recent performance.

    Analyzes the last PERFORMANCE_WINDOW scored sessions.
    If the average score >= INCREASE_THRESHOLD, difficulty goes up by 1.
    If the average score <= DECREASE_THRESHOLD, difficulty goes down by 1.
    The new difficulty is clamped to the user's grade range.

    Only adjusts when the user has at least PERFORMANCE_WINDOW scored sessions.

    Args:
        user_id: The user's internal UUID.

    Returns:
        The new difficulty level if changed, None if no change was made.

    Raises:
        DifficultyServiceError: If adjustment fails.
    """
    session_repo = SessionRepository()
    profile_repo = ProfileRepository()

    try:
        avg_score = await session_repo.get_average_score(user_id, PERFORMANCE_WINDOW)

        if avg_score is None:
            logger.debug("No scored sessions for user_id=%s, skipping adjustment", user_id)
            return None

        # Only adjust if we have a full window of scores
        sessions = await session_repo.get_last_n_by_user(user_id, PERFORMANCE_WINDOW)
        scored_count = sum(1 for s in sessions if s.ai_score is not None)
        if scored_count < PERFORMANCE_WINDOW:
            logger.debug(
                "Not enough scored sessions for user_id=%s (%d/%d), skipping",
                user_id,
                scored_count,
                PERFORMANCE_WINDOW,
            )
            return None

        # Determine delta
        if avg_score >= INCREASE_THRESHOLD:
            delta = 1
        elif avg_score <= DECREASE_THRESHOLD:
            delta = -1
        else:
            logger.debug(
                "Average score %.2f for user_id=%s is in neutral range, no adjustment",
                avg_score,
                user_id,
            )
            return None

        # Get profile and calculate new difficulty
        profile = await profile_repo.get_by_user_id(user_id)
        if profile is None:
            logger.warning("Profile not found for user_id=%s during difficulty adjustment", user_id)
            return None

        new_difficulty = profile.adjust_difficulty(delta)

        if new_difficulty == profile.current_difficulty:
            logger.debug(
                "Difficulty unchanged for user_id=%s (already at grade boundary: %d)",
                user_id,
                new_difficulty,
            )
            return None

        # Persist the new difficulty
        await profile_repo.update_difficulty(user_id, new_difficulty)

        logger.info(
            "Adjusted difficulty for user_id=%s: %d -> %d (avg_score=%.2f, delta=%+d)",
            user_id,
            profile.current_difficulty,
            new_difficulty,
            avg_score,
            delta,
        )
        return new_difficulty

    except DifficultyServiceError:
        raise
    except Exception as e:
        error_msg = f"Failed to adjust difficulty for user_id={user_id}: {e}"
        logger.exception(error_msg)
        raise DifficultyServiceError(error_msg) from e
