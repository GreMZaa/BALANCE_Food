"""APScheduler lifecycle management."""

import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.scheduler.jobs import check_and_send_reminders

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None

JOB_ID = "check_and_send_reminders"
INTERVAL_SECONDS = 60


def start_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Start the APScheduler with reminder check job.

    Creates an AsyncIOScheduler and adds an interval job that
    runs check_and_send_reminders every minute.

    Args:
        bot: The aiogram Bot instance passed to the job.

    Returns:
        The started AsyncIOScheduler instance.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.warning("Scheduler is already running")
        return _scheduler

    _scheduler = AsyncIOScheduler()

    _scheduler.add_job(
        check_and_send_reminders,
        trigger="interval",
        seconds=INTERVAL_SECONDS,
        id=JOB_ID,
        kwargs={"bot": bot},
        replace_existing=True,
        misfire_grace_time=60,
    )

    _scheduler.start()
    logger.info(
        "Scheduler started: job '%s' running every %d seconds",
        JOB_ID,
        INTERVAL_SECONDS,
    )
    return _scheduler


def shutdown_scheduler() -> None:
    """Shut down the scheduler gracefully.

    Waits for running jobs to complete before stopping.
    """
    global _scheduler

    if _scheduler is None:
        return

    if _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("Scheduler shut down successfully")

    _scheduler = None


def get_scheduler() -> AsyncIOScheduler | None:
    """Get the current scheduler instance.

    Returns:
        The scheduler instance, or None if not started.
    """
    return _scheduler
