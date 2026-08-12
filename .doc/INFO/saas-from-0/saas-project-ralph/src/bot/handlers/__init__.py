"""Telegram message handlers."""

from bot.handlers.help import router as help_router
from bot.handlers.onboarding import router as onboarding_router
from bot.handlers.practice import router as practice_router
from bot.handlers.settings import router as settings_router
from bot.handlers.start import router as start_router
from bot.handlers.stats import router as stats_router
from bot.handlers.subscription import router as subscription_router

__all__ = [
    "start_router",
    "onboarding_router",
    "practice_router",
    "stats_router",
    "settings_router",
    "subscription_router",
    "help_router",
]
