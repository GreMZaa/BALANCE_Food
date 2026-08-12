"""Subscription command and Telegram Payments handlers."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery

from bot.domain.entities.enums import PlanType
from bot.domain.entities.user import User
from bot.infrastructure.telegram.payments import send_invoice
from bot.keyboards.subscription import (
    SubscriptionPlanCallback,
    get_subscription_plans_keyboard,
)
from bot.services.subscription_service import (
    PLAN_PRICES,
    SubscriptionServiceError,
    activate_subscription,
    get_active_subscription,
)

logger = logging.getLogger(__name__)

router = Router(name="subscription")


# ── /subscribe command ────────────────────────────────────────────────


@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message, user: User | None = None) -> None:
    """Handle /subscribe command — show plans or current subscription status.

    Args:
        message: Incoming Telegram message.
        user: User domain object injected by AuthMiddleware.
    """
    if message.from_user is None:
        return

    telegram_id = message.from_user.id

    if user is None:
        await message.answer(
            "Сначала зарегистрируйся — отправь /start."
        )
        return

    # Check if user already has an active subscription
    try:
        existing = await get_active_subscription(user.id)
    except SubscriptionServiceError as e:
        logger.error(
            "Failed to check subscription for telegram_id=%d: %s",
            telegram_id,
            e,
        )
        existing = None

    if existing is not None:
        expires = existing.expires_at.strftime("%d.%m.%Y")
        await message.answer(
            f"У тебя уже есть активная подписка "
            f"<b>{existing.plan_type.value}</b>.\n"
            f"Действует до: <b>{expires}</b>\n\n"
            "Если хочешь продлить — выбери новый план ниже.",
            reply_markup=get_subscription_plans_keyboard(),
        )
        return

    await message.answer(
        "<b>Подписка на Interview Trainer</b>\n\n"
        "С подпиской ты получаешь безлимитный доступ "
        "к вопросам для подготовки к собеседованиям.\n\n"
        "Выбери план:",
        reply_markup=get_subscription_plans_keyboard(),
    )


# ── Plan selection callback ───────────────────────────────────────────


@router.callback_query(SubscriptionPlanCallback.filter())
async def process_plan_selection(
    callback: CallbackQuery,
    callback_data: SubscriptionPlanCallback,
    user: User | None = None,
) -> None:
    """Handle plan button press — send a Stars invoice.

    Args:
        callback: Callback query from the plan button.
        callback_data: Parsed callback data with selected plan.
        user: User domain object injected by AuthMiddleware.
    """
    await callback.answer()

    if callback.message is None or callback.from_user is None:
        return

    if user is None:
        await callback.message.answer("Сначала зарегистрируйся — отправь /start.")
        return

    try:
        plan_type = PlanType(callback_data.plan)
    except ValueError:
        logger.warning("Invalid plan in callback: %s", callback_data.plan)
        await callback.message.answer("Неизвестный план. Попробуй /subscribe.")
        return

    logger.info(
        "User telegram_id=%d selected plan %s",
        callback.from_user.id,
        plan_type.value,
    )

    try:
        await send_invoice(
            bot=callback.message.bot,
            chat_id=callback.message.chat.id,
            plan_type=plan_type,
        )
    except Exception as e:
        logger.exception(
            "Failed to send invoice for telegram_id=%d: %s",
            callback.from_user.id,
            e,
        )
        await callback.message.answer(
            "Не удалось создать счёт. Попробуй ещё раз позже."
        )


# ── Pre-checkout query ────────────────────────────────────────────────


@router.pre_checkout_query()
async def process_pre_checkout(query: PreCheckoutQuery) -> None:
    """Approve or reject a pre-checkout query.

    Telegram requires a response within 10 seconds.

    Args:
        query: The pre-checkout query from Telegram.
    """
    payload = query.invoice_payload

    # Validate payload format: "sub:<plan_type>"
    if not payload.startswith("sub:"):
        logger.warning("Unknown invoice payload: %s", payload)
        await query.answer(ok=False, error_message="Неизвестный тип платежа.")
        return

    plan_str = payload.removeprefix("sub:")
    try:
        plan_type = PlanType(plan_str)
    except ValueError:
        logger.warning("Invalid plan type in payload: %s", plan_str)
        await query.answer(ok=False, error_message="Неизвестный план подписки.")
        return

    # Verify the amount matches expected price
    expected_price = PLAN_PRICES[plan_type]
    if query.total_amount != expected_price:
        logger.warning(
            "Price mismatch for plan %s: expected=%d, got=%d",
            plan_type.value,
            expected_price,
            query.total_amount,
        )
        await query.answer(ok=False, error_message="Сумма платежа не совпадает.")
        return

    logger.info(
        "Pre-checkout approved: user_id=%d, plan=%s, amount=%d",
        query.from_user.id,
        plan_type.value,
        query.total_amount,
    )
    await query.answer(ok=True)


# ── Successful payment ────────────────────────────────────────────────


@router.message(F.successful_payment)
async def process_successful_payment(
    message: Message,
    user: User | None = None,
) -> None:
    """Handle successful Telegram Stars payment.

    Activates the subscription in the database and confirms to the user.

    Args:
        message: Message containing successful_payment data.
        user: User domain object injected by AuthMiddleware.
    """
    payment = message.successful_payment
    if payment is None or message.from_user is None:
        return

    telegram_id = message.from_user.id
    payload = payment.invoice_payload

    logger.info(
        "Successful payment received: telegram_id=%d, payload=%s, amount=%d, "
        "charge_id=%s",
        telegram_id,
        payload,
        payment.total_amount,
        payment.telegram_payment_charge_id,
    )

    if user is None:
        logger.error(
            "Payment received but user not found: telegram_id=%d", telegram_id
        )
        await message.answer(
            "Оплата получена, но произошла ошибка. "
            "Обратись в поддержку для активации подписки."
        )
        return

    # Parse plan from payload
    plan_str = payload.removeprefix("sub:")
    try:
        plan_type = PlanType(plan_str)
    except ValueError:
        logger.error("Invalid plan in successful payment payload: %s", payload)
        await message.answer(
            "Оплата получена, но произошла ошибка. "
            "Обратись в поддержку для активации подписки."
        )
        return

    # Activate subscription
    try:
        subscription = await activate_subscription(
            user_id=user.id,
            plan_type=plan_type,
            stars_paid=payment.total_amount,
            telegram_payment_charge_id=payment.telegram_payment_charge_id,
        )
    except SubscriptionServiceError as e:
        logger.exception(
            "Failed to activate subscription after payment: telegram_id=%d, error=%s",
            telegram_id,
            e,
        )
        await message.answer(
            "Оплата получена, но не удалось активировать подписку. "
            "Обратись в поддержку — мы всё исправим."
        )
        return

    expires = subscription.expires_at.strftime("%d.%m.%Y")
    await message.answer(
        "Подписка активирована!\n\n"
        f"<b>План:</b> {plan_type.value}\n"
        f"<b>Действует до:</b> {expires}\n\n"
        "Теперь у тебя безлимитный доступ к вопросам. "
        "Отправь /practice чтобы продолжить практику!"
    )
