"""Handler for /stats command — user statistics display."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from bot.domain.entities.enums import Grade
from bot.domain.entities.user import User
from bot.repositories.profile_repository import ProfileRepository
from bot.repositories.progress_repository import ProgressRepository
from bot.repositories.session_repository import SessionRepository

logger = logging.getLogger(__name__)

router = Router(name="stats")

DAILY_GOAL = 5

GRADE_LABELS: dict[Grade, str] = {
    Grade.JUNIOR: "Junior",
    Grade.MIDDLE: "Middle",
    Grade.SENIOR: "Senior",
}


def _progress_bar(current: int, total: int, length: int = 10) -> str:
    """Build a text-based progress bar.

    Args:
        current: Current value (clamped to total).
        total: Maximum value.
        length: Bar width in characters.

    Returns:
        A string like [======    ] 6/10.
    """
    filled = min(current, total) * length // total if total > 0 else 0
    bar = "\u2588" * filled + "\u2591" * (length - filled)
    return f"[{bar}] {min(current, total)}/{total}"


def _format_stats_message(
    *,
    first_name: str | None,
    grade: Grade,
    current_difficulty: int,
    difficulty_range: tuple[int, int],
    current_streak: int,
    longest_streak: int,
    total_questions: int,
    questions_today: int,
    average_score: float | None,
) -> str:
    """Format the statistics message.

    Returns:
        HTML-formatted statistics text.
    """
    name = first_name or "User"
    grade_label = GRADE_LABELS.get(grade, grade.value.capitalize())

    parts: list[str] = []

    parts.append(f"<b>\U0001f4ca {name}, \u0442\u0432\u043e\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430</b>\n")

    # --- Profile section ---
    parts.append(f"\U0001f3af <b>\u041f\u0440\u043e\u0444\u0438\u043b\u044c:</b> {grade_label}")
    parts.append(
        f"\U0001f4c8 <b>\u0421\u043b\u043e\u0436\u043d\u043e\u0441\u0442\u044c:</b> {current_difficulty} "
        f"(\u0434\u0438\u0430\u043f\u0430\u0437\u043e\u043d {difficulty_range[0]}\u2013{difficulty_range[1]})\n"
    )

    # --- Streak section ---
    parts.append(f"\U0001f525 <b>\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0441\u0442\u0440\u0438\u043a:</b> {current_streak} \u0434\u043d.")
    parts.append(f"\U0001f3c6 <b>\u041b\u0443\u0447\u0448\u0438\u0439 \u0441\u0442\u0440\u0438\u043a:</b> {longest_streak} \u0434\u043d.\n")

    # --- Daily progress section ---
    bar = _progress_bar(questions_today, DAILY_GOAL)
    parts.append(f"\U0001f4c5 <b>\u0421\u0435\u0433\u043e\u0434\u043d\u044f:</b> {bar}")
    parts.append(f"\U0001f4da <b>\u0412\u0441\u0435\u0433\u043e \u0432\u043e\u043f\u0440\u043e\u0441\u043e\u0432:</b> {total_questions}\n")

    # --- Performance section ---
    if average_score is not None:
        if average_score >= 8:
            indicator = "\U0001f7e2"
        elif average_score >= 5:
            indicator = "\U0001f7e1"
        else:
            indicator = "\U0001f534"
        parts.append(
            f"{indicator} <b>\u0421\u0440\u0435\u0434\u043d\u0438\u0439 \u0431\u0430\u043b\u043b (\u043f\u043e\u0441\u043b. 10):</b> {average_score:.1f}/10"
        )
    else:
        parts.append("\u2139\ufe0f \u041e\u0442\u0432\u0435\u0442\u044c \u043d\u0430 \u0432\u043e\u043f\u0440\u043e\u0441\u044b, \u0447\u0442\u043e\u0431\u044b \u0443\u0432\u0438\u0434\u0435\u0442\u044c \u0441\u0440\u0435\u0434\u043d\u0438\u0439 \u0431\u0430\u043b\u043b.")

    return "\n".join(parts)


@router.message(Command("stats"))
async def cmd_stats(message: Message, user: User | None = None) -> None:
    """Handle /stats command — display user statistics.

    Args:
        message: The incoming Telegram message.
        user: User domain object injected by AuthMiddleware.
    """
    if message.from_user is None:
        return

    profile_repo = ProfileRepository()
    progress_repo = ProgressRepository()
    session_repo = SessionRepository()

    if user is None:
        await message.answer(
            "\u041d\u0430\u0436\u043c\u0438 /start, \u0447\u0442\u043e\u0431\u044b \u043d\u0430\u0447\u0430\u0442\u044c \u0440\u0430\u0431\u043e\u0442\u0443 \u0441 \u0431\u043e\u0442\u043e\u043c."
        )
        return

    # 2. Look up profile
    profile = await profile_repo.get_by_user_id(user.id)
    if profile is None:
        await message.answer(
            "\u0421\u043d\u0430\u0447\u0430\u043b\u0430 \u043f\u0440\u043e\u0439\u0434\u0438 \u043e\u043d\u0431\u043e\u0440\u0434\u0438\u043d\u0433 \u2014 \u043d\u0430\u0436\u043c\u0438 /start."
        )
        return

    # 3. Look up progress (may not exist yet)
    progress = await progress_repo.get_by_user_id(user.id)

    # 4. Get average score for last 10 sessions
    average_score = await session_repo.get_average_score(user.id, last_n=10)

    # 5. Build message
    text = _format_stats_message(
        first_name=user.first_name,
        grade=profile.grade,
        current_difficulty=profile.current_difficulty,
        difficulty_range=profile.get_difficulty_range(),
        current_streak=progress.current_streak if progress else 0,
        longest_streak=progress.longest_streak if progress else 0,
        total_questions=progress.total_questions_answered if progress else 0,
        questions_today=progress.questions_today if progress else 0,
        average_score=average_score,
    )

    logger.info("Stats requested by telegram_id=%d", user.telegram_id)
    await message.answer(text)
