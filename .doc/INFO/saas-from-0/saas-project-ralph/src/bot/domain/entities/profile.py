"""UserProfile domain entity."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bot.domain.entities.enums import Category, Grade, Specialty


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class UserProfile(BaseModel):
    """User profile domain model.

    Stores user preferences for interview preparation.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal profile ID")
    user_id: UUID = Field(..., description="Reference to User.id")
    specialty: Specialty = Field(
        default=Specialty.BACKEND, description="User's specialty (only BACKEND in MVP)"
    )
    grade: Grade = Field(..., description="User's experience level")
    tech_stack: list[str] = Field(
        default_factory=list, description="Technologies the user works with"
    )
    focus_areas: list[Category] = Field(
        default_factory=list, description="Areas the user wants to focus on"
    )
    current_difficulty: int = Field(
        default=5, ge=1, le=10, description="Current difficulty level (1-10)"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When the profile was created"
    )
    updated_at: datetime = Field(
        default_factory=_utc_now, description="When the profile was last updated"
    )

    model_config = {"from_attributes": True}

    def get_difficulty_range(self) -> tuple[int, int]:
        """Get the allowed difficulty range based on grade.

        Returns:
            Tuple of (min_difficulty, max_difficulty)
        """
        ranges = {
            Grade.JUNIOR: (1, 4),
            Grade.MIDDLE: (3, 7),
            Grade.SENIOR: (5, 10),
        }
        return ranges[self.grade]

    def adjust_difficulty(self, delta: int) -> int:
        """Adjust difficulty within grade constraints.

        Args:
            delta: Amount to change difficulty by (+1 or -1 typically)

        Returns:
            New difficulty value, constrained to grade range
        """
        min_diff, max_diff = self.get_difficulty_range()
        new_difficulty = self.current_difficulty + delta
        return max(min_diff, min(max_diff, new_difficulty))
