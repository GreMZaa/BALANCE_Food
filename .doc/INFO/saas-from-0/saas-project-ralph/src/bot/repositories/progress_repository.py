"""Progress repository for database operations."""

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from bot.domain.entities.progress import Progress
from bot.infrastructure.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class ProgressRepositoryError(Exception):
    """Base exception for progress repository errors."""


class ProgressNotFoundError(ProgressRepositoryError):
    """Raised when progress record is not found."""


class ProgressRepository:
    """Repository for Progress entity database operations.

    Handles CRUD operations for user_progress table in Supabase.
    Returns domain models instead of raw dictionaries.
    """

    TABLE_NAME = "user_progress"

    def _to_domain_model(self, data: dict) -> Progress:
        """Convert database row to Progress domain model.

        Args:
            data: Raw database row as dictionary.

        Returns:
            Progress domain model.
        """
        last_activity_date = data.get("last_activity_date")
        if isinstance(last_activity_date, str):
            last_activity_date = date.fromisoformat(last_activity_date)

        return Progress(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            user_id=UUID(data["user_id"])
            if isinstance(data["user_id"], str)
            else data["user_id"],
            current_streak=data.get("current_streak", 0),
            longest_streak=data.get("longest_streak", 0),
            total_questions_answered=data.get("total_questions_answered", 0),
            questions_today=data.get("questions_today", 0),
            last_activity_date=last_activity_date,
            streak_updated_at=data.get("streak_updated_at"),
            created_at=data.get("created_at"),
        )

    def _to_db_dict(self, progress: Progress) -> dict:
        """Convert Progress domain model to database dictionary.

        Args:
            progress: Progress domain model.

        Returns:
            Dictionary suitable for database operations.
        """
        return {
            "user_id": str(progress.user_id),
            "current_streak": progress.current_streak,
            "longest_streak": progress.longest_streak,
            "total_questions_answered": progress.total_questions_answered,
            "questions_today": progress.questions_today,
            "last_activity_date": progress.last_activity_date.isoformat()
            if progress.last_activity_date
            else None,
            "streak_updated_at": progress.streak_updated_at.isoformat()
            if progress.streak_updated_at
            else None,
        }

    async def get_by_user_id(self, user_id: UUID) -> Progress | None:
        """Get progress by user ID.

        Args:
            user_id: The internal user UUID.

        Returns:
            Progress domain model if found, None otherwise.

        Raises:
            ProgressRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("Progress for user_id=%s not found", user_id)
                return None

            logger.debug("Found progress for user_id=%s", user_id)
            row = response.data[0] if isinstance(response.data, list) else response.data
            return self._to_domain_model(row)

        except Exception as e:
            error_msg = f"Failed to get progress by user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise ProgressRepositoryError(error_msg) from e

    async def create(self, progress: Progress) -> Progress:
        """Create a new progress record in the database.

        Args:
            progress: The Progress domain model to create.

        Returns:
            Created Progress domain model with database-assigned fields.

        Raises:
            ProgressRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = self._to_db_dict(progress)

            response = await client.table(self.TABLE_NAME).insert(data).execute()

            if not response.data:
                raise ProgressRepositoryError("No data returned after insert")

            created_progress = self._to_domain_model(response.data[0])
            logger.info(
                "Created progress: user_id=%s, id=%s",
                created_progress.user_id,
                created_progress.id,
            )
            return created_progress

        except ProgressRepositoryError:
            raise
        except Exception as e:
            error_msg = f"Failed to create progress for user_id={progress.user_id}: {e}"
            logger.exception(error_msg)
            raise ProgressRepositoryError(error_msg) from e

    async def update(self, progress: Progress) -> Progress:
        """Update an existing progress record in the database.

        Args:
            progress: The Progress domain model with updated fields.

        Returns:
            Updated Progress domain model.

        Raises:
            ProgressNotFoundError: If progress record does not exist.
            ProgressRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = self._to_db_dict(progress)

            response = (
                await client.table(self.TABLE_NAME)
                .update(data)
                .eq("user_id", str(progress.user_id))
                .execute()
            )

            if not response.data:
                raise ProgressNotFoundError(
                    f"Progress for user_id={progress.user_id} not found"
                )

            updated_progress = self._to_domain_model(response.data[0])
            logger.info(
                "Updated progress: user_id=%s, streak=%d, questions_today=%d",
                updated_progress.user_id,
                updated_progress.current_streak,
                updated_progress.questions_today,
            )
            return updated_progress

        except (ProgressNotFoundError, ProgressRepositoryError):
            raise
        except Exception as e:
            error_msg = f"Failed to update progress for user_id={progress.user_id}: {e}"
            logger.exception(error_msg)
            raise ProgressRepositoryError(error_msg) from e

    async def update_streak(
        self, user_id: UUID, current_streak: int, longest_streak: int
    ) -> Progress:
        """Update streak values for a user's progress.

        Args:
            user_id: The user's internal UUID.
            current_streak: The new current streak value.
            longest_streak: The new longest streak value.

        Returns:
            Updated Progress domain model.

        Raises:
            ProgressNotFoundError: If progress record does not exist.
            ProgressRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            response = (
                await client.table(self.TABLE_NAME)
                .update(
                    {
                        "current_streak": current_streak,
                        "longest_streak": longest_streak,
                        "streak_updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                .eq("user_id", str(user_id))
                .execute()
            )

            if not response.data:
                raise ProgressNotFoundError(
                    f"Progress for user_id={user_id} not found"
                )

            updated_progress = self._to_domain_model(response.data[0])
            logger.info(
                "Updated streak for user_id=%s: current=%d, longest=%d",
                user_id,
                current_streak,
                longest_streak,
            )
            return updated_progress

        except (ProgressNotFoundError, ProgressRepositoryError):
            raise
        except Exception as e:
            error_msg = f"Failed to update streak for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise ProgressRepositoryError(error_msg) from e

    async def increment_questions_today(
        self, user_id: UUID, current_date: date | None = None
    ) -> Progress:
        """Increment questions_today counter, resetting if it's a new day.

        If last_activity_date differs from current_date, questions_today resets to 1.
        Otherwise, questions_today is incremented by 1.
        Also increments total_questions_answered.

        Args:
            user_id: The user's internal UUID.
            current_date: The current date (defaults to today UTC).

        Returns:
            Updated Progress domain model.

        Raises:
            ProgressNotFoundError: If progress record does not exist.
            ProgressRepositoryError: If database operation fails.
        """
        if current_date is None:
            current_date = datetime.now(UTC).date()

        try:
            progress = await self.get_by_user_id(user_id)

            if progress is None:
                raise ProgressNotFoundError(
                    f"Progress for user_id={user_id} not found"
                )

            # Reset questions_today if it's a new day
            if progress.last_activity_date != current_date:
                progress.questions_today = 1
            else:
                progress.questions_today += 1

            progress.total_questions_answered += 1
            progress.last_activity_date = current_date

            return await self.update(progress)

        except (ProgressNotFoundError, ProgressRepositoryError):
            raise
        except Exception as e:
            error_msg = (
                f"Failed to increment questions_today for user_id={user_id}: {e}"
            )
            logger.exception(error_msg)
            raise ProgressRepositoryError(error_msg) from e

    async def get_or_create(self, user_id: UUID) -> tuple[Progress, bool]:
        """Get existing progress or create a new one.

        Args:
            user_id: The user's internal UUID.

        Returns:
            Tuple of (Progress, created) where created is True if new record was created.

        Raises:
            ProgressRepositoryError: If database operation fails.
        """
        existing = await self.get_by_user_id(user_id)

        if existing is not None:
            return existing, False

        new_progress = Progress(user_id=user_id)
        created = await self.create(new_progress)
        return created, True
