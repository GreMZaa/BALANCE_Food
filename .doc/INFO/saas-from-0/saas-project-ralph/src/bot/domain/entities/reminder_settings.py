"""Reminder settings domain entity."""

from datetime import UTC, date, datetime, time
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

MAX_REMINDERS_PER_DAY = 3
DEFAULT_REMINDER_TIMES = [time(10, 0), time(15, 0), time(20, 0)]


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class ReminderSettings(BaseModel):
    """Reminder settings domain model.

    Stores user preferences for daily practice reminders.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal reminder settings ID")
    user_id: UUID = Field(..., description="Reference to User.id")
    reminders_enabled: bool = Field(
        default=True, description="Whether reminders are enabled"
    )
    reminder_times: list[time] = Field(
        default_factory=lambda: list(DEFAULT_REMINDER_TIMES),
        description="Times when reminders should be sent (user local time)",
    )
    reminders_sent_today: int = Field(
        default=0, ge=0, description="Number of reminders sent today"
    )
    last_reminder_date: date | None = Field(
        default=None, description="Date when reminders counter was last reset"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When the record was created"
    )
    updated_at: datetime | None = Field(
        default=None, description="When the record was last updated"
    )

    model_config = {"from_attributes": True}

    def can_send_reminder(self) -> bool:
        """Check if another reminder can be sent today.

        Returns:
            True if reminders are enabled and daily limit not reached.
        """
        if not self.reminders_enabled:
            return False
        today = date.today()
        if self.last_reminder_date != today:
            return True
        return self.reminders_sent_today < MAX_REMINDERS_PER_DAY

    def record_reminder_sent(self) -> None:
        """Record that a reminder was sent, resetting counter if new day."""
        today = date.today()
        if self.last_reminder_date != today:
            self.reminders_sent_today = 1
            self.last_reminder_date = today
        else:
            self.reminders_sent_today += 1
