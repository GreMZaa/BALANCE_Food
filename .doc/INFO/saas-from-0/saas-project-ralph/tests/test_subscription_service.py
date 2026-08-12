"""Tests for subscription service module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import PlanType
from bot.domain.entities.progress import Progress
from bot.domain.entities.subscription import Subscription
from bot.services.subscription_service import (
    PLAN_DURATIONS,
    PLAN_PRICES,
    SubscriptionServiceError,
    activate_subscription,
    check_access,
    get_active_subscription,
    has_free_questions_today,
)


@pytest.fixture
def active_subscription():
    """Create an active, non-expired subscription."""
    now = datetime.now(UTC)
    return Subscription(
        user_id=uuid4(),
        plan_type=PlanType.MONTH,
        stars_paid=150,
        telegram_payment_charge_id="charge_123",
        starts_at=now - timedelta(days=5),
        expires_at=now + timedelta(days=25),
    )


@pytest.fixture
def progress_with_questions():
    """Create progress with some questions answered today."""
    return Progress(
        user_id=uuid4(),
        questions_today=3,
        total_questions_answered=30,
        last_activity_date=datetime.now(UTC).date(),
    )


@pytest.fixture
def progress_at_limit():
    """Create progress with free limit exhausted."""
    return Progress(
        user_id=uuid4(),
        questions_today=5,
        total_questions_answered=50,
        last_activity_date=datetime.now(UTC).date(),
    )


class TestCheckAccess:
    """Tests for check_access function."""

    async def test_subscriber_has_access(self, active_subscription: Subscription):
        """Test that user with active subscription has access."""
        user_id = active_subscription.user_id
        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_active_by_user_id = AsyncMock(
            return_value=active_subscription
        )

        with patch(
            "bot.services.subscription_service.SubscriptionRepository",
            return_value=mock_sub_repo,
        ):
            result = await check_access(user_id)

        assert result is True

    async def test_free_user_with_remaining_questions(
        self, progress_with_questions: Progress
    ):
        """Test free user with questions remaining has access."""
        user_id = progress_with_questions.user_id
        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_active_by_user_id = AsyncMock(return_value=None)

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_by_user_id = AsyncMock(
            return_value=progress_with_questions
        )

        with (
            patch(
                "bot.services.subscription_service.SubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await check_access(user_id)

        assert result is True

    async def test_free_user_at_limit_denied(self, progress_at_limit: Progress):
        """Test free user who exhausted limit is denied."""
        user_id = progress_at_limit.user_id
        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_active_by_user_id = AsyncMock(return_value=None)

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_by_user_id = AsyncMock(return_value=progress_at_limit)

        with (
            patch(
                "bot.services.subscription_service.SubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_progress_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await check_access(user_id)

        assert result is False

    async def test_new_user_has_access(self):
        """Test brand new user (no progress) has access."""
        user_id = uuid4()
        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_active_by_user_id = AsyncMock(return_value=None)

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_by_user_id = AsyncMock(return_value=None)

        with (
            patch(
                "bot.services.subscription_service.SubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_progress_repo,
            ),
        ):
            result = await check_access(user_id)

        assert result is True

    async def test_check_access_error_raises_service_error(self):
        """Test that errors are wrapped in SubscriptionServiceError."""
        mock_sub_repo = AsyncMock()
        mock_sub_repo.get_active_by_user_id = AsyncMock(
            side_effect=Exception("DB down")
        )

        with (
            patch(
                "bot.services.subscription_service.SubscriptionRepository",
                return_value=mock_sub_repo,
            ),
            pytest.raises(SubscriptionServiceError) as exc_info,
        ):
            await check_access(uuid4())

        assert "Failed to check access" in str(exc_info.value)


class TestHasFreeQuestionsToday:
    """Tests for has_free_questions_today function."""

    async def test_no_progress_returns_true(self):
        """Test returns True when user has no progress record."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(return_value=None)

        with patch(
            "bot.services.subscription_service.ProgressRepository",
            return_value=mock_repo,
        ):
            result = await has_free_questions_today(uuid4())

        assert result is True

    async def test_below_limit_returns_true(self):
        """Test returns True when user is below daily limit."""
        user_id = uuid4()
        progress = Progress(
            user_id=user_id,
            questions_today=3,
            last_activity_date=datetime.now(UTC).date(),
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(return_value=progress)

        with (
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await has_free_questions_today(user_id)

        assert result is True

    async def test_at_limit_returns_false(self):
        """Test returns False when user has reached the limit."""
        user_id = uuid4()
        progress = Progress(
            user_id=user_id,
            questions_today=5,
            last_activity_date=datetime.now(UTC).date(),
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(return_value=progress)

        with (
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await has_free_questions_today(user_id)

        assert result is False

    async def test_above_limit_returns_false(self):
        """Test returns False when user exceeded the limit."""
        user_id = uuid4()
        progress = Progress(
            user_id=user_id,
            questions_today=7,
            last_activity_date=datetime.now(UTC).date(),
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(return_value=progress)

        with (
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await has_free_questions_today(user_id)

        assert result is False

    async def test_different_day_resets_counter(self):
        """Test that questions from a previous day don't count."""
        user_id = uuid4()
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        progress = Progress(
            user_id=user_id,
            questions_today=5,
            last_activity_date=yesterday,
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(return_value=progress)

        with (
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await has_free_questions_today(user_id)

        assert result is True

    async def test_zero_questions_returns_true(self):
        """Test returns True with zero questions answered today."""
        user_id = uuid4()
        progress = Progress(
            user_id=user_id,
            questions_today=0,
            last_activity_date=datetime.now(UTC).date(),
        )
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(return_value=progress)

        with (
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_repo,
            ),
            patch("bot.services.subscription_service.settings") as mock_settings,
        ):
            mock_settings.free_questions_per_day = 5
            result = await has_free_questions_today(user_id)

        assert result is True

    async def test_error_raises_service_error(self):
        """Test that errors are wrapped in SubscriptionServiceError."""
        mock_repo = AsyncMock()
        mock_repo.get_by_user_id = AsyncMock(side_effect=Exception("DB error"))

        with (
            patch(
                "bot.services.subscription_service.ProgressRepository",
                return_value=mock_repo,
            ),
            pytest.raises(SubscriptionServiceError) as exc_info,
        ):
            await has_free_questions_today(uuid4())

        assert "Failed to check free questions" in str(exc_info.value)


class TestActivateSubscription:
    """Tests for activate_subscription function."""

    async def test_activate_new_subscription(self):
        """Test activating a subscription for user without existing one."""
        user_id = uuid4()
        now = datetime.now(UTC)

        created_sub = Subscription(
            user_id=user_id,
            plan_type=PlanType.MONTH,
            stars_paid=150,
            telegram_payment_charge_id="charge_abc",
            starts_at=now,
            expires_at=now + timedelta(days=30),
        )

        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=created_sub)

        with patch(
            "bot.services.subscription_service.SubscriptionRepository",
            return_value=mock_repo,
        ):
            result = await activate_subscription(
                user_id=user_id,
                plan_type=PlanType.MONTH,
                stars_paid=150,
                telegram_payment_charge_id="charge_abc",
            )

        assert result.plan_type == PlanType.MONTH
        assert result.stars_paid == 150
        assert result.user_id == user_id
        mock_repo.deactivate.assert_not_awaited()
        mock_repo.create.assert_awaited_once()

    async def test_activate_deactivates_existing(
        self, active_subscription: Subscription
    ):
        """Test that existing subscription is deactivated first."""
        user_id = active_subscription.user_id
        now = datetime.now(UTC)

        new_sub = Subscription(
            user_id=user_id,
            plan_type=PlanType.THREE_MONTHS,
            stars_paid=350,
            starts_at=now,
            expires_at=now + timedelta(days=90),
        )

        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(
            return_value=active_subscription
        )
        mock_repo.deactivate = AsyncMock(return_value=active_subscription)
        mock_repo.create = AsyncMock(return_value=new_sub)

        with patch(
            "bot.services.subscription_service.SubscriptionRepository",
            return_value=mock_repo,
        ):
            result = await activate_subscription(
                user_id=user_id,
                plan_type=PlanType.THREE_MONTHS,
                stars_paid=350,
            )

        mock_repo.deactivate.assert_awaited_once_with(active_subscription.id)
        assert result.plan_type == PlanType.THREE_MONTHS

    async def test_activate_week_plan(self):
        """Test activating a weekly subscription."""
        user_id = uuid4()
        now = datetime.now(UTC)

        created_sub = Subscription(
            user_id=user_id,
            plan_type=PlanType.WEEK,
            stars_paid=50,
            starts_at=now,
            expires_at=now + timedelta(days=7),
        )

        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(return_value=None)
        mock_repo.create = AsyncMock(return_value=created_sub)

        with patch(
            "bot.services.subscription_service.SubscriptionRepository",
            return_value=mock_repo,
        ):
            result = await activate_subscription(
                user_id=user_id,
                plan_type=PlanType.WEEK,
                stars_paid=50,
            )

        assert result.plan_type == PlanType.WEEK
        assert result.stars_paid == 50

    async def test_activate_error_raises_service_error(self):
        """Test that errors are wrapped in SubscriptionServiceError."""
        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(
            side_effect=Exception("DB error")
        )

        with (
            patch(
                "bot.services.subscription_service.SubscriptionRepository",
                return_value=mock_repo,
            ),
            pytest.raises(SubscriptionServiceError) as exc_info,
        ):
            await activate_subscription(
                user_id=uuid4(),
                plan_type=PlanType.MONTH,
                stars_paid=150,
            )

        assert "Failed to activate subscription" in str(exc_info.value)


class TestGetActiveSubscription:
    """Tests for get_active_subscription function."""

    async def test_returns_active_subscription(
        self, active_subscription: Subscription
    ):
        """Test returning active subscription."""
        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(
            return_value=active_subscription
        )

        with patch(
            "bot.services.subscription_service.SubscriptionRepository",
            return_value=mock_repo,
        ):
            result = await get_active_subscription(active_subscription.user_id)

        assert result is not None
        assert result.plan_type == PlanType.MONTH

    async def test_returns_none_when_no_subscription(self):
        """Test returns None when user has no active subscription."""
        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(return_value=None)

        with patch(
            "bot.services.subscription_service.SubscriptionRepository",
            return_value=mock_repo,
        ):
            result = await get_active_subscription(uuid4())

        assert result is None

    async def test_error_raises_service_error(self):
        """Test that errors are wrapped in SubscriptionServiceError."""
        mock_repo = AsyncMock()
        mock_repo.get_active_by_user_id = AsyncMock(
            side_effect=Exception("DB error")
        )

        with (
            patch(
                "bot.services.subscription_service.SubscriptionRepository",
                return_value=mock_repo,
            ),
            pytest.raises(SubscriptionServiceError) as exc_info,
        ):
            await get_active_subscription(uuid4())

        assert "Failed to get subscription" in str(exc_info.value)


class TestPlanConstants:
    """Tests for plan pricing and duration constants."""

    def test_all_plan_types_have_prices(self):
        """Test that all plan types have defined prices."""
        for plan_type in PlanType:
            assert plan_type in PLAN_PRICES
            assert PLAN_PRICES[plan_type] > 0

    def test_all_plan_types_have_durations(self):
        """Test that all plan types have defined durations."""
        for plan_type in PlanType:
            assert plan_type in PLAN_DURATIONS
            assert PLAN_DURATIONS[plan_type].days > 0

    def test_week_plan_pricing(self):
        """Test weekly plan price."""
        assert PLAN_PRICES[PlanType.WEEK] == 50

    def test_month_plan_pricing(self):
        """Test monthly plan price."""
        assert PLAN_PRICES[PlanType.MONTH] == 150

    def test_three_months_plan_pricing(self):
        """Test quarterly plan price."""
        assert PLAN_PRICES[PlanType.THREE_MONTHS] == 350

    def test_week_duration(self):
        """Test weekly plan duration."""
        assert PLAN_DURATIONS[PlanType.WEEK] == timedelta(days=7)

    def test_month_duration(self):
        """Test monthly plan duration."""
        assert PLAN_DURATIONS[PlanType.MONTH] == timedelta(days=30)

    def test_three_months_duration(self):
        """Test quarterly plan duration."""
        assert PLAN_DURATIONS[PlanType.THREE_MONTHS] == timedelta(days=90)


class TestImports:
    """Tests for module imports."""

    def test_import_from_services_init(self):
        """Test that subscription service functions can be imported from services."""
        from bot.services import (
            SubscriptionServiceError,
            activate_subscription,
            check_access,
            get_active_subscription,
            has_free_questions_today,
        )

        assert check_access is not None
        assert has_free_questions_today is not None
        assert activate_subscription is not None
        assert get_active_subscription is not None
        assert SubscriptionServiceError is not None

    def test_subscription_service_error_is_exception(self):
        """Test SubscriptionServiceError inherits from Exception."""
        error = SubscriptionServiceError("test")
        assert isinstance(error, Exception)
        assert str(error) == "test"
