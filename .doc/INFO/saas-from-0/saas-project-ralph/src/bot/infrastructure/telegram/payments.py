"""Telegram Payments (Stars) — invoice creation and payment processing."""

import logging

from aiogram import Bot
from aiogram.types import LabeledPrice, Message

from bot.domain.entities.enums import PlanType
from bot.services.subscription_service import PLAN_PRICES

logger = logging.getLogger(__name__)

# Human-readable plan labels (Russian)
PLAN_LABELS: dict[PlanType, str] = {
    PlanType.WEEK: "Подписка на 1 неделю",
    PlanType.MONTH: "Подписка на 1 месяц",
    PlanType.THREE_MONTHS: "Подписка на 3 месяца",
}


async def send_invoice(
    bot: Bot,
    chat_id: int,
    plan_type: PlanType,
) -> Message:
    """Send a Telegram Stars invoice to the user.

    Args:
        bot: The aiogram Bot instance.
        chat_id: Target chat ID.
        plan_type: Subscription plan to invoice for.

    Returns:
        The sent Message containing the invoice.
    """
    price = PLAN_PRICES[plan_type]
    label = PLAN_LABELS[plan_type]

    logger.info(
        "Sending Stars invoice: chat_id=%d, plan=%s, price=%d",
        chat_id,
        plan_type.value,
        price,
    )

    return await bot.send_invoice(
        chat_id=chat_id,
        title=label,
        description=f"{label} — безлимит вопросов для подготовки к собеседованиям.",
        payload=f"sub:{plan_type.value}",
        currency="XTR",
        prices=[LabeledPrice(label=label, amount=price)],
        provider_token="",
    )
