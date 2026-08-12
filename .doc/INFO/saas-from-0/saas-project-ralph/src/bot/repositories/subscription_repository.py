"""Subscription repository for database operations."""

import logging
from uuid import UUID

from bot.domain.entities.enums import PlanType
from bot.domain.entities.subscription import Subscription
from bot.infrastructure.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class SubscriptionRepositoryError(Exception):
    """Base exception for subscription repository errors."""


class SubscriptionNotFoundError(SubscriptionRepositoryError):
    """Raised when subscription is not found."""


class SubscriptionRepository:
    """Repository for Subscription entity database operations.

    Handles CRUD operations for subscriptions table in Supabase.
    Returns domain models instead of raw dictionaries.
    """

    TABLE_NAME = "subscriptions"

    def _to_domain_model(self, data: dict) -> Subscription:
        """Convert database row to Subscription domain model.

        Args:
            data: Raw database row as dictionary.

        Returns:
            Subscription domain model.
        """
        plan_type = PlanType(data["plan_type"])

        return Subscription(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            user_id=UUID(data["user_id"])
            if isinstance(data["user_id"], str)
            else data["user_id"],
            plan_type=plan_type,
            stars_paid=data["stars_paid"],
            telegram_payment_charge_id=data.get("telegram_payment_charge_id"),
            starts_at=data["starts_at"],
            expires_at=data["expires_at"],
            is_active=data.get("is_active", True),
            created_at=data.get("created_at"),
        )

    def _to_db_dict(self, subscription: Subscription) -> dict:
        """Convert Subscription domain model to database dictionary.

        Args:
            subscription: Subscription domain model.

        Returns:
            Dictionary suitable for database insertion.
        """
        return {
            "user_id": str(subscription.user_id),
            "plan_type": subscription.plan_type.value,
            "stars_paid": subscription.stars_paid,
            "telegram_payment_charge_id": subscription.telegram_payment_charge_id,
            "starts_at": subscription.starts_at.isoformat(),
            "expires_at": subscription.expires_at.isoformat(),
            "is_active": subscription.is_active,
        }

    async def get_active_by_user_id(self, user_id: UUID) -> Subscription | None:
        """Get the active subscription for a user.

        Finds a subscription that is marked active and not yet expired.

        Args:
            user_id: The internal user UUID.

        Returns:
            Subscription domain model if found, None otherwise.

        Raises:
            SubscriptionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("user_id", str(user_id))
                .eq("is_active", True)
                .order("expires_at", desc=True)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("No active subscription for user_id=%s", user_id)
                return None

            row = response.data[0] if isinstance(response.data, list) else response.data
            subscription = self._to_domain_model(row)

            if subscription.is_expired():
                logger.debug(
                    "Subscription %s for user_id=%s is expired", subscription.id, user_id
                )
                return None

            logger.debug("Found active subscription for user_id=%s", user_id)
            return subscription

        except Exception as e:
            error_msg = f"Failed to get active subscription for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise SubscriptionRepositoryError(error_msg) from e

    async def create(self, subscription: Subscription) -> Subscription:
        """Create a new subscription in the database.

        Args:
            subscription: The Subscription domain model to create.

        Returns:
            Created Subscription domain model with database-assigned fields.

        Raises:
            SubscriptionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = self._to_db_dict(subscription)

            response = await client.table(self.TABLE_NAME).insert(data).execute()

            if not response.data:
                raise SubscriptionRepositoryError("No data returned after insert")

            created = self._to_domain_model(response.data[0])
            logger.info(
                "Created subscription: user_id=%s, plan=%s, id=%s",
                created.user_id,
                created.plan_type.value,
                created.id,
            )
            return created

        except SubscriptionRepositoryError:
            raise
        except Exception as e:
            error_msg = (
                f"Failed to create subscription for user_id={subscription.user_id}: {e}"
            )
            logger.exception(error_msg)
            raise SubscriptionRepositoryError(error_msg) from e

    async def deactivate(self, subscription_id: UUID) -> Subscription:
        """Deactivate a subscription by setting is_active to False.

        Args:
            subscription_id: The subscription UUID.

        Returns:
            Updated Subscription domain model.

        Raises:
            SubscriptionNotFoundError: If subscription does not exist.
            SubscriptionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            response = (
                await client.table(self.TABLE_NAME)
                .update({"is_active": False})
                .eq("id", str(subscription_id))
                .execute()
            )

            if not response.data:
                raise SubscriptionNotFoundError(
                    f"Subscription with id={subscription_id} not found"
                )

            deactivated = self._to_domain_model(response.data[0])
            logger.info(
                "Deactivated subscription: id=%s, user_id=%s",
                deactivated.id,
                deactivated.user_id,
            )
            return deactivated

        except (SubscriptionNotFoundError, SubscriptionRepositoryError):
            raise
        except Exception as e:
            error_msg = (
                f"Failed to deactivate subscription id={subscription_id}: {e}"
            )
            logger.exception(error_msg)
            raise SubscriptionRepositoryError(error_msg) from e
