"""Scheduled jobs for reminder notifications."""

import logging
from datetime import datetime, time

from aiogram import Bot
from aiogram.enums import ParseMode

from bot.core.config import settings
from bot.keyboards.reminder import get_reminder_practice_keyboard
from bot.repositories.progress_repository import ProgressRepository
from bot.repositories.reminder_repository import ReminderRepository
from bot.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

MOTIVATIONAL_MESSAGES = [
    "\U0001f680 \u041a\u0430\u0436\u0434\u044b\u0439 \u0432\u043e\u043f\u0440\u043e\u0441 \u043f\u0440\u0438\u0431\u043b\u0438\u0436\u0430\u0435\u0442 \u0442\u0435\u0431\u044f \u043a \u043e\u0444\u0444\u0435\u0440\u0443!",
    "\U0001f4aa \u0420\u0435\u0433\u0443\u043b\u044f\u0440\u043d\u043e\u0441\u0442\u044c \u2014 \u043a\u043b\u044e\u0447 \u043a \u0443\u0441\u043f\u0435\u0445\u0443 \u043d\u0430 \u0441\u043e\u0431\u0435\u0441\u0435\u0434\u043e\u0432\u0430\u043d\u0438\u0438!",
    "\U0001f3af \u041d\u0435 \u0441\u0434\u0430\u0432\u0430\u0439\u0441\u044f, \u0442\u044b \u043d\u0430 \u043f\u0440\u0430\u0432\u0438\u043b\u044c\u043d\u043e\u043c \u043f\u0443\u0442\u0438!",
]


async def check_and_send_reminders(bot: Bot) -> None:
    """Check for users needing reminders and send them.

    Runs every minute. Matches the current minute (truncated to HH:MM)
    against each user's configured reminder_times.

    Args:
        bot: The aiogram Bot instance for sending messages.
    """
    try:
        import zoneinfo

        tz = zoneinfo.ZoneInfo(settings.timezone)
    except Exception:
        logger.warning(
            "Invalid timezone %s, falling back to UTC",
            settings.timezone,
        )
        from datetime import UTC

        tz = UTC

    now = datetime.now(tz)
    current_time = time(now.hour, now.minute)

    logger.debug("Checking reminders for time=%s", current_time.isoformat())

    reminder_repo = ReminderRepository()
    user_repo = UserRepository()
    progress_repo = ProgressRepository()

    try:
        eligible = await reminder_repo.get_users_for_reminder(current_time)
    except Exception:
        logger.exception("Failed to fetch users for reminder at %s", current_time)
        return

    if not eligible:
        return

    logger.info("Found %d users eligible for reminder at %s", len(eligible), current_time)

    for reminder_settings in eligible:
        try:
            user = await user_repo.get_by_id(reminder_settings.user_id)
            if user is None:
                logger.warning(
                    "User not found for reminder: user_id=%s",
                    reminder_settings.user_id,
                )
                continue

            progress = await progress_repo.get_by_user_id(reminder_settings.user_id)
            questions_today = progress.questions_today if progress else 0
            remaining = max(0, settings.daily_goal - questions_today)

            if remaining == 0:
                logger.debug(
                    "User %s already reached daily goal, skipping reminder",
                    user.telegram_id,
                )
                continue

            text = _build_reminder_text(
                remaining, user.first_name, reminder_settings.reminders_sent_today
            )
            keyboard = get_reminder_practice_keyboard()

            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard,
            )

            reminder_settings.record_reminder_sent()
            await reminder_repo.update(reminder_settings)

            logger.info(
                "Sent reminder to user telegram_id=%d (remaining=%d)",
                user.telegram_id,
                remaining,
            )

        except Exception:
            logger.exception(
                "Failed to send reminder to user_id=%s",
                reminder_settings.user_id,
            )


def _build_reminder_text(
    remaining: int, first_name: str | None, reminders_sent_today: int
) -> str:
    """Build a motivational reminder message text.

    Args:
        remaining: Number of questions remaining to reach daily goal.
        first_name: User's first name for personalization.
        reminders_sent_today: How many reminders already sent today (0-based,
            before the current one is recorded).

    Returns:
        Formatted HTML reminder message string.
    """
    greeting = first_name if first_name else "\u0434\u0440\u0443\u0433"

    if remaining == 1:
        questions_word = "\u0432\u043e\u043f\u0440\u043e\u0441"
    elif remaining in (2, 3, 4):
        questions_word = "\u0432\u043e\u043f\u0440\u043e\u0441\u0430"
    else:
        questions_word = "\u0432\u043e\u043f\u0440\u043e\u0441\u043e\u0432"

    motivational = MOTIVATIONAL_MESSAGES[
        reminders_sent_today % len(MOTIVATIONAL_MESSAGES)
    ]

    return (
        f"\U0001f514 <b>\u041f\u0440\u0438\u0432\u0435\u0442, {greeting}!</b>\n\n"
        f"\u0421\u0435\u0433\u043e\u0434\u043d\u044f \u043e\u0441\u0442\u0430\u043b\u043e\u0441\u044c <b>{remaining}</b> {questions_word} "
        f"\u0434\u043e \u0434\u043d\u0435\u0432\u043d\u043e\u0439 \u0446\u0435\u043b\u0438.\n\n"
        f"{motivational}"
    )
