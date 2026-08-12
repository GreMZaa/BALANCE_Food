"""Subscription domain entity."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bot.domain.entities.enums import PlanType


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class Subscription(BaseModel):
    """User subscription domain model.

    Tracks premium subscription status and payment details.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal subscription ID")
    user_id: UUID = Field(..., description="Reference to User.id")
    plan_type: PlanType = Field(..., description="Subscription plan type")
    stars_paid: int = Field(..., gt=0, description="Number of Telegram Stars paid")
    telegram_payment_charge_id: str | None = Field(
        default=None, description="Telegram payment charge ID for refunds"
    )
    starts_at: datetime = Field(
        default_factory=_utc_now, description="When subscription becomes active"
    )
    expires_at: datetime = Field(..., description="When subscription expires")
    is_active: bool = Field(default=True, description="Whether subscription is active")
    created_at: datetime = Field(
        default_factory=_utc_now, description="When the subscription was created"
    )

    model_config = {"from_attributes": True}

    def is_expired(self) -> bool:
        """Check if subscription has expired.

        Returns:
            True if current time is past expires_at
        """
        return datetime.now(UTC) > self.expires_at
