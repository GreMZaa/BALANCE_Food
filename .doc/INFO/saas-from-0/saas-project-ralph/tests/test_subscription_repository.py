"""Tests for subscription repository module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import PlanType
from bot.domain.entities.subscription import Subscription
from bot.repositories.subscription_repository import (
    SubscriptionNotFoundError,
    SubscriptionRepository,
    SubscriptionRepositoryError,
)


@pytest.fixture
def sub_repo():
    """Create a SubscriptionRepository instance."""
    return SubscriptionRepository()


@pytest.fixture
def sample_sub_data():
    """Sample subscription data as it would come from database."""
    now = datetime.now(UTC)
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "plan_type": "month",
        "stars_paid": 150,
        "telegram_payment_charge_id": "charge_abc123",
        "starts_at": now.isoformat(),
        "expires_at": (now + timedelta(days=30)).isoformat(),
        "is_active": True,
        "created_at": now.isoformat(),
    }


@pytest.fixture
def expired_sub_data():
    """Sample expired subscription data."""
    past = datetime.now(UTC) - timedelta(days=60)
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "plan_type": "week",
        "stars_paid": 50,
        "telegram_payment_charge_id": "charge_old",
        "starts_at": past.isoformat(),
        "expires_at": (past + timedelta(days=7)).isoformat(),
        "is_active": True,
        "created_at": past.isoformat(),
    }


@pytest.fixture
def sample_subscription():
    """Create a sample Subscription domain model."""
    now = datetime.now(UTC)
    return Subscription(
        user_id=uuid4(),
        plan_type=PlanType.MONTH,
        stars_paid=150,
        telegram_payment_charge_id="charge_abc123",
        expires_at=now + timedelta(days=30),
    )


class TestSubscriptionRepositoryGetActiveByUserId:
    """Tests for get_active_by_user_id method."""

    async def test_get_active_found(
        self, sub_repo: SubscriptionRepository, sample_sub_data: dict
    ):
        """Test getting active subscription for a user."""
        mock_response = MagicMock()
        mock_response.data = [sample_sub_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq_active = MagicMock(return_value=MagicMock(order=mock_order))
        mock_eq_user = MagicMock(return_value=MagicMock(eq=mock_eq_active))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq_user))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        from uuid import UUID

        user_id = UUID(sample_sub_data["user_id"])

        with patch(
            "bot.repositories.subscription_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await sub_repo.get_active_by_user_id(user_id)

        assert result is not None
        assert isinstance(result, Subscription)
        assert result.plan_type == PlanType.MONTH
        assert result.is_active is True

    async def test_get_active_not_found(self, sub_repo: SubscriptionRepository):
        """Test returns None when no active subscription exists."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq_active = MagicMock(return_value=MagicMock(order=mock_order))
        mock_eq_user = MagicMock(return_value=MagicMock(eq=mock_eq_active))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq_user))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.subscription_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await sub_repo.get_active_by_user_id(uuid4())

        assert result is None

    async def test_get_active_expired_returns_none(
        self, sub_repo: SubscriptionRepository, expired_sub_data: dict
    ):
        """Test returns None when subscription is expired."""
        mock_response = MagicMock()
        mock_response.data = [expired_sub_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq_active = MagicMock(return_value=MagicMock(order=mock_order))
        mock_eq_user = MagicMock(return_value=MagicMock(eq=mock_eq_active))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq_user))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        from uuid import UUID

        user_id = UUID(expired_sub_data["user_id"])

        with patch(
            "bot.repositories.subscription_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await sub_repo.get_active_by_user_id(user_id)

        assert result is None

    async def test_get_active_error(self, sub_repo: SubscriptionRepository):
        """Test that database errors raise SubscriptionRepositoryError."""
        with (
            patch(
                "bot.repositories.subscription_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SubscriptionRepositoryError) as exc_info,
        ):
            await sub_repo.get_active_by_user_id(uuid4())

        assert "Failed to get active subscription" in str(exc_info.value)


class TestSubscriptionRepositoryCreate:
    """Tests for create method."""

    async def test_create_success(
        self,
        sub_repo: SubscriptionRepository,
        sample_subscription: Subscription,
        sample_sub_data: dict,
    ):
        """Test creating a new subscription."""
        mock_response = MagicMock()
        mock_response.data = [sample_sub_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.subscription_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await sub_repo.create(sample_subscription)

        assert result is not None
        assert isinstance(result, Subscription)
        assert result.plan_type == PlanType.MONTH
        assert result.stars_paid == 150

    async def test_create_no_data_returned(
        self,
        sub_repo: SubscriptionRepository,
        sample_subscription: Subscription,
    ):
        """Test that create raises error when no data returned."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with (
            patch(
                "bot.repositories.subscription_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(SubscriptionRepositoryError) as exc_info,
        ):
            await sub_repo.create(sample_subscription)

        assert "No data returned" in str(exc_info.value)

    async def test_create_error(
        self,
        sub_repo: SubscriptionRepository,
        sample_subscription: Subscription,
    ):
        """Test that database errors raise SubscriptionRepositoryError."""
        with (
            patch(
                "bot.repositories.subscription_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SubscriptionRepositoryError) as exc_info,
        ):
            await sub_repo.create(sample_subscription)

        assert "Failed to create subscription" in str(exc_info.value)


class TestSubscriptionRepositoryDeactivate:
    """Tests for deactivate method."""

    async def test_deactivate_success(
        self, sub_repo: SubscriptionRepository, sample_sub_data: dict
    ):
        """Test deactivating a subscription."""
        deactivated_data = sample_sub_data.copy()
        deactivated_data["is_active"] = False

        mock_response = MagicMock()
        mock_response.data = [deactivated_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_eq = MagicMock(return_value=mock_query)
        mock_update = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(update=mock_update))

        mock_client = MagicMock()
        mock_client.table = mock_table

        from uuid import UUID

        sub_id = UUID(sample_sub_data["id"])

        with patch(
            "bot.repositories.subscription_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await sub_repo.deactivate(sub_id)

        assert result is not None
        assert isinstance(result, Subscription)
        assert result.is_active is False

    async def test_deactivate_not_found(self, sub_repo: SubscriptionRepository):
        """Test deactivating non-existent subscription raises error."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_eq = MagicMock(return_value=mock_query)
        mock_update = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(update=mock_update))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with (
            patch(
                "bot.repositories.subscription_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(SubscriptionNotFoundError) as exc_info,
        ):
            await sub_repo.deactivate(uuid4())

        assert "not found" in str(exc_info.value)

    async def test_deactivate_error(self, sub_repo: SubscriptionRepository):
        """Test that database errors raise SubscriptionRepositoryError."""
        with (
            patch(
                "bot.repositories.subscription_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SubscriptionRepositoryError) as exc_info,
        ):
            await sub_repo.deactivate(uuid4())

        assert "Failed to deactivate subscription" in str(exc_info.value)


class TestSubscriptionRepositoryErrors:
    """Tests for error handling."""

    def test_subscription_repository_error_is_exception(self):
        """Test SubscriptionRepositoryError inherits from Exception."""
        error = SubscriptionRepositoryError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_subscription_not_found_error_is_repository_error(self):
        """Test SubscriptionNotFoundError inherits from SubscriptionRepositoryError."""
        error = SubscriptionNotFoundError("subscription not found")
        assert isinstance(error, SubscriptionRepositoryError)
        assert isinstance(error, Exception)


class TestSubscriptionRepositoryConversion:
    """Tests for data conversion methods."""

    def test_to_domain_model(self, sub_repo: SubscriptionRepository, sample_sub_data: dict):
        """Test converting database row to domain model."""
        result = sub_repo._to_domain_model(sample_sub_data)

        assert isinstance(result, Subscription)
        assert result.plan_type == PlanType.MONTH
        assert result.stars_paid == 150
        assert result.is_active is True
        assert result.telegram_payment_charge_id == "charge_abc123"

    def test_to_db_dict(
        self, sub_repo: SubscriptionRepository, sample_subscription: Subscription
    ):
        """Test converting domain model to database dictionary."""
        result = sub_repo._to_db_dict(sample_subscription)

        assert result["user_id"] == str(sample_subscription.user_id)
        assert result["plan_type"] == "month"
        assert result["stars_paid"] == 150
        assert result["is_active"] is True
        assert "id" not in result
        assert "created_at" not in result
