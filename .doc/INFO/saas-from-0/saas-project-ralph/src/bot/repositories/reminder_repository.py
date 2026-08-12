"""Reminder settings repository for database operations."""

import logging
from datetime import time
from uuid import UUID

from bot.domain.entities.reminder_settings import ReminderSettings
from bot.infrastructure.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class ReminderRepositoryError(Exception):
    """Base exception for reminder repository errors."""


class ReminderNotFoundError(ReminderRepositoryError):
    """Raised when reminder settings are not found."""


class ReminderRepository:
    """Repository for ReminderSettings entity database operations.

    Handles CRUD operations for the reminder_settings table in Supabase.
    Returns domain models instead of raw dictionaries.
    """

    TABLE_NAME = "reminder_settings"

    def _to_domain_model(self, data: dict) -> ReminderSettings:
        """Convert database row to ReminderSettings domain model.

        Args:
            data: Raw database row as dictionary.

        Returns:
            ReminderSettings domain model.
        """
        reminder_times = []
        raw_times = data.get("reminder_times") or []
        for t in raw_times:
            if isinstance(t, time):
                reminder_times.append(t)
            elif isinstance(t, str):
                reminder_times.append(time.fromisoformat(t))

        return ReminderSettings(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            user_id=(
                UUID(data["user_id"])
                if isinstance(data["user_id"], str)
                else data["user_id"]
            ),
            reminders_enabled=data.get("reminders_enabled", True),
            reminder_times=reminder_times,
            reminders_sent_today=data.get("reminders_sent_today", 0),
            last_reminder_date=data.get("last_reminder_date"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def _to_db_dict(self, settings: ReminderSettings) -> dict:
        """Convert ReminderSettings domain model to database dictionary.

        Args:
            settings: ReminderSettings domain model.

        Returns:
            Dictionary suitable for database insertion.
        """
        return {
            "user_id": str(settings.user_id),
            "reminders_enabled": settings.reminders_enabled,
            "reminder_times": [t.isoformat() for t in settings.reminder_times],
            "reminders_sent_today": settings.reminders_sent_today,
            "last_reminder_date": (
                settings.last_reminder_date.isoformat()
                if settings.last_reminder_date
                else None
            ),
        }

    async def get_by_user_id(self, user_id: UUID) -> ReminderSettings | None:
        """Get reminder settings for a user.

        Args:
            user_id: The internal user UUID.

        Returns:
            ReminderSettings domain model if found, None otherwise.

        Raises:
            ReminderRepositoryError: If database operation fails.
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
                logger.debug("No reminder settings for user_id=%s", user_id)
                return None

            return self._to_domain_model(response.data[0])

        except Exception as e:
            error_msg = (
                f"Failed to get reminder settings for user_id={user_id}: {e}"
            )
            logger.exception(error_msg)
            raise ReminderRepositoryError(error_msg) from e

    async def create(self, settings: ReminderSettings) -> ReminderSettings:
        """Create new reminder settings in the database.

        Args:
            settings: The ReminderSettings domain model to create.

        Returns:
            Created ReminderSettings with database-assigned fields.

        Raises:
            ReminderRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = self._to_db_dict(settings)

            response = await client.table(self.TABLE_NAME).insert(data).execute()

            if not response.data:
                raise ReminderRepositoryError("No data returned after insert")

            created = self._to_domain_model(response.data[0])
            logger.info(
                "Created reminder settings: user_id=%s, enabled=%s",
                created.user_id,
                created.reminders_enabled,
            )
            return created

        except ReminderRepositoryError:
            raise
        except Exception as e:
            error_msg = (
                f"Failed to create reminder settings for "
                f"user_id={settings.user_id}: {e}"
            )
            logger.exception(error_msg)
            raise ReminderRepositoryError(error_msg) from e

    async def update(self, settings: ReminderSettings) -> ReminderSettings:
        """Update existing reminder settings.

        Args:
            settings: The ReminderSettings domain model with updated fields.

        Returns:
            Updated ReminderSettings domain model.

        Raises:
            ReminderNotFoundError: If settings do not exist.
            ReminderRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = {
                "reminders_enabled": settings.reminders_enabled,
                "reminder_times": [
                    t.isoformat() for t in settings.reminder_times
                ],
                "reminders_sent_today": settings.reminders_sent_today,
                "last_reminder_date": (
                    settings.last_reminder_date.isoformat()
                    if settings.last_reminder_date
                    else None
                ),
            }

            response = (
                await client.table(self.TABLE_NAME)
                .update(data)
                .eq("user_id", str(settings.user_id))
                .execute()
            )

            if not response.data:
                raise ReminderNotFoundError(
                    f"Reminder settings for user_id={settings.user_id} not found"
                )

            updated = self._to_domain_model(response.data[0])
            logger.info(
                "Updated reminder settings: user_id=%s, enabled=%s",
                updated.user_id,
                updated.reminders_enabled,
            )
            return updated

        except (ReminderNotFoundError, ReminderRepositoryError):
            raise
        except Exception as e:
            error_msg = (
                f"Failed to update reminder settings for "
                f"user_id={settings.user_id}: {e}"
            )
            logger.exception(error_msg)
            raise ReminderRepositoryError(error_msg) from e

    async def get_or_create(self, user_id: UUID) -> ReminderSettings:
        """Get reminder settings, creating defaults if none exist.

        Args:
            user_id: The internal user UUID.

        Returns:
            Existing or newly created ReminderSettings.

        Raises:
            ReminderRepositoryError: If database operation fails.
        """
        existing = await self.get_by_user_id(user_id)
        if existing is not None:
            return existing

        new_settings = ReminderSettings(user_id=user_id)
        return await self.create(new_settings)

    async def get_users_for_reminder(self, reminder_time: time) -> list[ReminderSettings]:
        """Get all users who should receive a reminder at the given time.

        Finds users with reminders enabled whose reminder_times array
        contains the specified time, and who haven't exceeded the daily limit.

        Args:
            reminder_time: The time (HH:MM) to match against.

        Returns:
            List of ReminderSettings for users needing a reminder.

        Raises:
            ReminderRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            time_str = reminder_time.isoformat()

            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("reminders_enabled", True)
                .contains("reminder_times", [time_str])
                .execute()
            )

            if not response.data:
                return []

            results = []
            for row in response.data:
                settings = self._to_domain_model(row)
                if settings.can_send_reminder():
                    results.append(settings)

            logger.debug(
                "Found %d users for reminder at %s",
                len(results),
                time_str,
            )
            return results

        except Exception as e:
            error_msg = (
                f"Failed to get users for reminder at {reminder_time}: {e}"
            )
            logger.exception(error_msg)
            raise ReminderRepositoryError(error_msg) from e
