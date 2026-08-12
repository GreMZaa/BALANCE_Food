"""Bot application factory and lifecycle management."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from bot.core.config import settings
from bot.handlers import (
    help_router,
    onboarding_router,
    practice_router,
    settings_router,
    start_router,
    stats_router,
    subscription_router,
)
from bot.infrastructure.database import close_supabase_client, init_supabase_client
from bot.infrastructure.openai.client import close_openai_client, init_openai_client
from bot.middlewares import (
    AuthMiddleware,
    InputValidationMiddleware,
    RateLimitMiddleware,
    SubscriptionMiddleware,
)
from bot.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    """Create and configure the Telegram bot instance.

    Returns:
        Bot: Configured aiogram Bot instance.
    """
    return Bot(
        token=settings.telegram_bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    """Create and configure the Dispatcher with routers and middleware.

    Returns:
        Dispatcher: Configured aiogram Dispatcher instance.
    """
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Register rate limit middleware (runs first, before any DB calls)
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())

    # Register input validation middleware (validates text length and callback data)
    dp.message.middleware(InputValidationMiddleware())
    dp.callback_query.middleware(InputValidationMiddleware())

    # Register auth middleware (runs on every message and callback)
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    # Register subscription check middleware on practice router
    # (must be added before the router is included in the dispatcher)
    practice_router.message.middleware(SubscriptionMiddleware())
    practice_router.callback_query.middleware(SubscriptionMiddleware())

    # Register routers
    dp.include_router(start_router)
    dp.include_router(onboarding_router)
    dp.include_router(practice_router)
    dp.include_router(stats_router)
    dp.include_router(settings_router)
    dp.include_router(subscription_router)
    dp.include_router(help_router)

    return dp


@asynccontextmanager
async def lifespan(bot: Bot) -> AsyncGenerator[None]:
    """Manage application lifecycle: startup and shutdown.

    Args:
        bot: The Bot instance for lifecycle management.

    Yields:
        None during the application's active period.
    """
    # Startup
    logger.info("Starting bot application...")

    try:
        await init_supabase_client()
        logger.info("Database connection established")

        init_openai_client()
        logger.info("OpenAI client initialized")
    except Exception as e:
        logger.exception("Failed to connect to database: %s", e)
        raise

    bot_info = await bot.get_me()
    logger.info("Bot started: @%s (ID: %d)", bot_info.username, bot_info.id)

    start_scheduler(bot)
    logger.info("Reminder scheduler started")

    yield

    # Shutdown
    logger.info("Shutting down bot application...")
    shutdown_scheduler()
    await close_openai_client()
    await close_supabase_client()
    await bot.session.close()
    logger.info("Bot shutdown complete")
