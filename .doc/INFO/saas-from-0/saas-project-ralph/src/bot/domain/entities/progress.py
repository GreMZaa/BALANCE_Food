"""Progress domain entity."""

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class Progress(BaseModel):
    """User progress domain model.

    Tracks streak and daily progress for gamification.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal progress ID")
    user_id: UUID = Field(..., description="Reference to User.id")
    current_streak: int = Field(default=0, ge=0, description="Current streak in days")
    longest_streak: int = Field(default=0, ge=0, description="Longest streak ever achieved")
    total_questions_answered: int = Field(
        default=0, ge=0, description="Total questions answered all time"
    )
    questions_today: int = Field(
        default=0, ge=0, description="Questions answered today"
    )
    last_activity_date: date | None = Field(
        default=None, description="Date of last activity (for streak tracking)"
    )
    streak_updated_at: datetime | None = Field(
        default=None, description="When the streak was last updated"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When the progress record was created"
    )

    model_config = {"from_attributes": True}

    def has_reached_daily_goal(self, daily_goal: int = 5) -> bool:
        """Check if user has reached their daily goal.

        Args:
            daily_goal: Number of questions to reach (default: 5)

        Returns:
            True if daily goal is met
        """
        return self.questions_today >= daily_goal

    def update_longest_streak(self) -> None:
        """Update longest_streak if current_streak exceeds it."""
        if self.current_streak > self.longest_streak:
            self.longest_streak = self.current_streak

    def is_milestone_streak(self) -> int | None:
        """Check if current streak is a milestone.

        Returns:
            The milestone value (7, 30, or 100) if it's a milestone, None otherwise
        """
        milestones = [7, 30, 100]
        if self.current_streak in milestones:
            return self.current_streak
        return None
