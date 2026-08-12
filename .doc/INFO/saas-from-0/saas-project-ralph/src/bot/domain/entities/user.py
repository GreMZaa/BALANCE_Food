"""User domain entity."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class User(BaseModel):
    """User domain model.

    Represents a Telegram user in the system.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal user ID")
    telegram_id: int = Field(..., description="Telegram user ID")
    username: str | None = Field(default=None, description="Telegram username")
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    language_code: str = Field(default="ru", description="User's language code")
    timezone: str = Field(default="Europe/Moscow", description="User's timezone")
    created_at: datetime = Field(
        default_factory=_utc_now, description="When the user was created"
    )
    updated_at: datetime = Field(
        default_factory=_utc_now, description="When the user was last updated"
    )

    model_config = {"from_attributes": True}
