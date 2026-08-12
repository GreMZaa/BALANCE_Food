"""Subscription access control service."""

import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from bot.core.config import settings
from bot.domain.entities.enums import PlanType
from bot.domain.entities.subscription import Subscription
from bot.repositories.progress_repository import ProgressRepository
from bot.repositories.subscription_repository import SubscriptionRepository

logger = logging.getLogger(__name__)


class SubscriptionServiceError(Exception):
    """Base exception for subscription service errors."""


# Prices in Telegram Stars per plan
PLAN_PRICES: dict[PlanType, int] = {
    PlanType.WEEK: 50,
    PlanType.MONTH: 150,
    PlanType.THREE_MONTHS: 350,
}

# Duration per plan
PLAN_DURATIONS: dict[PlanType, timedelta] = {
    PlanType.WEEK: timedelta(days=7),
    PlanType.MONTH: timedelta(days=30),
    PlanType.THREE_MONTHS: timedelta(days=90),
}


async def check_access(user_id: UUID) -> bool:
    """Check if user has access to practice.

    User has access if they have an active subscription
    or have not exhausted free daily questions.

    Args:
        user_id: The user's internal UUID.

    Returns:
        True if user can practice, False otherwise.

    Raises:
        SubscriptionServiceError: If the check fails.
    """
    try:
        sub_repo = SubscriptionRepository()
        subscription = await sub_repo.get_active_by_user_id(user_id)

        if subscription is not None:
            logger.debug("User %s has active subscription", user_id)
            return True

        return await has_free_questions_today(user_id)

    except SubscriptionServiceError:
        raise
    except Exception as e:
        error_msg = f"Failed to check access for user_id={user_id}: {e}"
        logger.exception(error_msg)
        raise SubscriptionServiceError(error_msg) from e


async def has_free_questions_today(user_id: UUID) -> bool:
    """Check if user has remaining free questions for today.

    Free users get settings.free_questions_per_day questions per day.

    Args:
        user_id: The user's internal UUID.

    Returns:
        True if free questions remain, False if limit exhausted.

    Raises:
        SubscriptionServiceError: If the check fails.
    """
    try:
        progress_repo = ProgressRepository()
        progress = await progress_repo.get_by_user_id(user_id)

        if progress is None:
            logger.debug("No progress for user_id=%s, free questions available", user_id)
            return True

        today = datetime.now(UTC).date()
        questions_today = progress.questions_today

        # If last activity was a different day, counter is effectively 0
        if progress.last_activity_date != today:
            questions_today = 0

        has_free = questions_today < settings.free_questions_per_day

        logger.debug(
            "Free questions check for user_id=%s: today=%d, limit=%d, has_free=%s",
            user_id,
            questions_today,
            settings.free_questions_per_day,
            has_free,
        )
        return has_free

    except SubscriptionServiceError:
        raise
    except Exception as e:
        error_msg = f"Failed to check free questions for user_id={user_id}: {e}"
        logger.exception(error_msg)
        raise SubscriptionServiceError(error_msg) from e


async def activate_subscription(
    user_id: UUID,
    plan_type: PlanType,
    stars_paid: int,
    telegram_payment_charge_id: str | None = None,
) -> Subscription:
    """Activate a new subscription for a user.

    Deactivates any existing active subscription before creating a new one.

    Args:
        user_id: The user's internal UUID.
        plan_type: The subscription plan type.
        stars_paid: Number of Telegram Stars paid.
        telegram_payment_charge_id: Telegram payment charge ID for refunds.

    Returns:
        The newly created active Subscription.

    Raises:
        SubscriptionServiceError: If activation fails.
    """
    try:
        sub_repo = SubscriptionRepository()

        # Check for existing active subscription to extend from
        existing = await sub_repo.get_active_by_user_id(user_id)
        now = datetime.now(UTC)
        duration = PLAN_DURATIONS[plan_type]

        if existing is not None and existing.expires_at > now:
            # Extend: new subscription starts where old one ends
            starts_at = existing.expires_at
            await sub_repo.deactivate(existing.id)
            logger.info(
                "Deactivated previous subscription %s for user_id=%s, "
                "extending from %s",
                existing.id,
                user_id,
                starts_at.isoformat(),
            )
        elif existing is not None:
            await sub_repo.deactivate(existing.id)
            starts_at = now
            logger.info(
                "Deactivated expired subscription %s for user_id=%s",
                existing.id,
                user_id,
            )
        else:
            starts_at = now

        subscription = Subscription(
            user_id=user_id,
            plan_type=plan_type,
            stars_paid=stars_paid,
            telegram_payment_charge_id=telegram_payment_charge_id,
            starts_at=starts_at,
            expires_at=starts_at + duration,
        )

        created = await sub_repo.create(subscription)

        logger.info(
            "Activated subscription for user_id=%s: plan=%s, expires=%s",
            user_id,
            plan_type.value,
            created.expires_at.isoformat(),
        )
        return created

    except SubscriptionServiceError:
        raise
    except Exception as e:
        error_msg = f"Failed to activate subscription for user_id={user_id}: {e}"
        logger.exception(error_msg)
        raise SubscriptionServiceError(error_msg) from e


async def get_active_subscription(user_id: UUID) -> Subscription | None:
    """Get the active subscription for a user.

    Args:
        user_id: The user's internal UUID.

    Returns:
        Active Subscription if exists, None otherwise.

    Raises:
        SubscriptionServiceError: If the lookup fails.
    """
    try:
        sub_repo = SubscriptionRepository()
        return await sub_repo.get_active_by_user_id(user_id)
    except Exception as e:
        error_msg = f"Failed to get subscription for user_id={user_id}: {e}"
        logger.exception(error_msg)
        raise SubscriptionServiceError(error_msg) from e
