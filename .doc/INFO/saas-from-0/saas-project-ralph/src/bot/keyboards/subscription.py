"""Subscription plan selection keyboards."""

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.domain.entities.enums import PlanType
from bot.services.subscription_service import PLAN_PRICES


class SubscriptionPlanCallback(CallbackData, prefix="sub_plan"):
    """Callback data for subscription plan selection."""

    plan: str


# Labels displayed on plan buttons
_PLAN_BUTTON_LABELS: dict[PlanType, str] = {
    PlanType.WEEK: "1 неделя",
    PlanType.MONTH: "1 месяц",
    PlanType.THREE_MONTHS: "3 месяца",
}


def get_subscription_plans_keyboard() -> InlineKeyboardMarkup:
    """Build inline keyboard with subscription plan options.

    Returns:
        InlineKeyboardMarkup with one button per plan.
    """
    builder = InlineKeyboardBuilder()

    for plan_type in (PlanType.WEEK, PlanType.MONTH, PlanType.THREE_MONTHS):
        label = _PLAN_BUTTON_LABELS[plan_type]
        price = PLAN_PRICES[plan_type]
        builder.button(
            text=f"{label} — {price} Stars",
            callback_data=SubscriptionPlanCallback(plan=plan_type.value),
        )

    builder.adjust(1)  # one button per row
    return builder.as_markup()
