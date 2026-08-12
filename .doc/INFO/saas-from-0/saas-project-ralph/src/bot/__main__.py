"""Entry point for the Interview Trainer Bot."""

import asyncio
import contextlib
import logging

from bot.app import create_bot, create_dispatcher, lifespan
from bot.core.config import settings
from bot.core.logging import setup_logging


async def main() -> None:
    """Run the bot in long-polling mode."""
    setup_logging(level=settings.log_level, json_output=settings.log_json)
    logger = logging.getLogger(__name__)

    bot = create_bot()
    dp = create_dispatcher()

    async with lifespan(bot):
        logger.info("Starting long-polling...")
        try:
            await dp.start_polling(
                bot,
                allowed_updates=dp.resolve_used_update_types(),
            )
        except asyncio.CancelledError:
            logger.info("Polling cancelled")
        finally:
            logger.info("Polling stopped")


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        asyncio.run(main())
