"""Practice command handler for interview question sessions."""

import logging
import os
import tempfile
import time
from pathlib import Path
from uuid import UUID

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.domain.entities.enums import AnswerType, Category
from bot.domain.entities.question import Evaluation, Question, QuestionSession
from bot.domain.entities.user import User
from bot.keyboards.practice import NextQuestionCallback, get_next_question_keyboard
from bot.middlewares.input_validation import sanitize_text
from bot.repositories.profile_repository import ProfileRepository
from bot.repositories.session_repository import SessionRepository
from bot.services.difficulty_service import adjust_difficulty
from bot.services.evaluation_service import (
    EvaluationError,
    EvaluationParseError,
    evaluate_answer,
)
from bot.services.progress_service import check_milestone, record_answer
from bot.services.question_service import (
    QuestionGenerationError,
    QuestionParseError,
    generate_question,
)
from bot.services.transcription_service import (
    InvalidAudioError,
    TranscriptionError,
    transcribe,
)
from bot.states.practice import PracticeStates

logger = logging.getLogger(__name__)

router = Router(name="practice")


# =============================================================================
# Category labels for display (Russian)
# =============================================================================

CATEGORY_DISPLAY_LABELS: dict[Category, str] = {
    Category.LANGUAGE: "💻 Язык программирования",
    Category.ALGORITHMS: "🧮 Алгоритмы",
    Category.DATABASES: "🗄️ Базы данных",
    Category.API_DESIGN: "🔌 API Design",
    Category.SYSTEM_DESIGN: "🏗️ System Design",
    Category.ARCHITECTURE: "📐 Архитектура",
    Category.MICROSERVICES: "🔀 Микросервисы",
    Category.DEVOPS: "⚙️ DevOps",
}


def _get_difficulty_label(difficulty: int) -> str:
    """Get human-readable difficulty label.

    Args:
        difficulty: Difficulty level (1-10)

    Returns:
        Difficulty label with visual indicator
    """
    if difficulty <= 3:
        return f"🟢 {difficulty}/10 (легко)"
    elif difficulty <= 6:
        return f"🟡 {difficulty}/10 (средне)"
    else:
        return f"🔴 {difficulty}/10 (сложно)"


def _format_question_message(question: Question) -> str:
    """Format a question for display.

    Args:
        question: The generated question

    Returns:
        Formatted message string
    """
    category_label = CATEGORY_DISPLAY_LABELS.get(
        question.category, f"📝 {question.category.value}"
    )
    difficulty_label = _get_difficulty_label(question.difficulty)

    return (
        f"<b>📋 Вопрос</b>\n\n"
        f"<b>Категория:</b> {category_label}\n"
        f"<b>Сложность:</b> {difficulty_label}\n\n"
        f"<b>Вопрос:</b>\n{question.text}\n\n"
        f"<i>Напиши свой ответ текстом или отправь голосовое сообщение.</i>"
    )


@router.message(Command("practice"))
async def cmd_practice(message: Message, state: FSMContext, user: User | None = None) -> None:
    """Handle /practice command to start a new practice session.

    Args:
        message: The incoming Telegram message
        state: FSM context for managing conversation state
        user: User domain object injected by AuthMiddleware
    """
    if message.from_user is None:
        logger.warning("Received /practice without from_user")
        return

    telegram_id = message.from_user.id
    profile_repo = ProfileRepository()

    if user is None:
        logger.warning(
            "User not found for telegram_id=%d, redirecting to /start", telegram_id
        )
        await message.answer(
            "Похоже, ты ещё не зарегистрирован. "
            "Отправь /start для начала работы."
        )
        return

    # Check if user has a profile (completed onboarding)
    profile = await profile_repo.get_by_user_id(user.id)
    if profile is None:
        logger.info(
            "User telegram_id=%d has no profile, redirecting to onboarding",
            telegram_id,
        )
        await message.answer(
            "Чтобы начать практику, нужно сначала настроить профиль.\n\n"
            "Отправь /start чтобы пройти настройку — это займёт пару минут "
            "и поможет мне подбирать вопросы под твой уровень и стек технологий."
        )
        return

    # Generate a question based on user profile
    logger.info(
        "Generating question for user telegram_id=%d, grade=%s, difficulty=%d",
        telegram_id,
        profile.grade,
        profile.current_difficulty,
    )

    # Show typing indicator while generating
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Fetch recent questions to avoid repeats
    recent_questions: list[str] | None = None
    try:
        session_repo = SessionRepository()
        recent_sessions = await session_repo.get_last_n_by_user(user.id, 20)
        if recent_sessions:
            recent_questions = [s.question_text for s in recent_sessions]
    except Exception as e:
        logger.warning(
            "Failed to fetch recent sessions for dedup, telegram_id=%d: %s",
            telegram_id,
            e,
        )

    try:
        question = await generate_question(profile, recent_questions)
    except (QuestionGenerationError, QuestionParseError) as e:
        logger.error(
            "Failed to generate question for telegram_id=%d: %s", telegram_id, e
        )
        await message.answer(
            "Произошла ошибка при генерации вопроса. "
            "Пожалуйста, попробуй ещё раз через /practice."
        )
        return
    except Exception as e:
        logger.exception(
            "Unexpected error generating question for telegram_id=%d: %s",
            telegram_id,
            e,
        )
        await message.answer(
            "Произошла неожиданная ошибка. "
            "Пожалуйста, попробуй ещё раз позже."
        )
        return

    # Store question in FSM state for later evaluation
    # Include question_started_at for response_time_ms calculation
    await state.update_data(
        question_id=str(question.id),
        question_text=question.text,
        question_category=question.category.value,
        question_difficulty=question.difficulty,
        user_id=str(user.id),
        question_started_at=time.time(),
    )

    # Set FSM state to waiting for answer
    await state.set_state(PracticeStates.waiting_answer)

    # Send the question
    question_message = _format_question_message(question)
    await message.answer(question_message)

    logger.info(
        "Sent question to telegram_id=%d: category=%s, difficulty=%d",
        telegram_id,
        question.category,
        question.difficulty,
    )


MILESTONE_MESSAGES: dict[int, str] = {
    7: (
        "🎉🎉🎉 <b>MILESTONE!</b> 🎉🎉🎉\n\n"
        "🔥 <b>7 дней подряд!</b> Целая неделя практики!\n\n"
        "Ты выработал отличную привычку — большинство людей сдаются "
        "в первые дни. Продолжай в том же духе, и результат не заставит себя ждать! 💪"
    ),
    30: (
        "🏆🏆🏆 <b>MILESTONE!</b> 🏆🏆🏆\n\n"
        "🔥 <b>30 дней подряд!</b> Целый месяц без пропусков!\n\n"
        "Это серьёзное достижение — ты точно на пути к успешному интервью. "
        "Твои знания растут с каждым днём. Так держать! 🚀"
    ),
    100: (
        "👑👑👑 <b>LEGENDARY MILESTONE!</b> 👑👑👑\n\n"
        "🔥 <b>100 дней подряд!</b> Это невероятная дисциплина!\n\n"
        "Ты в числе самых преданных пользователей. "
        "С такой подготовкой любое интервью тебе по плечу. Респект! 🫡"
    ),
}


def _format_milestone_message(milestone: int) -> str | None:
    """Format a milestone celebration message.

    Args:
        milestone: The milestone value (7, 30, or 100)

    Returns:
        Formatted celebration message, or None if not a known milestone
    """
    return MILESTONE_MESSAGES.get(milestone)


def _format_feedback_message(
    evaluation: Evaluation,
    questions_today: int,
    daily_goal: int = 5,
    current_streak: int = 0,
) -> str:
    """Format evaluation feedback for display.

    Args:
        evaluation: The evaluation result from AI
        questions_today: Number of questions answered today
        daily_goal: Daily goal for questions (default: 5)
        current_streak: User's current streak in days

    Returns:
        Formatted feedback message string
    """
    # Score with visual indicator
    score = evaluation.score
    if score <= 3:
        score_indicator = "🔴"
        score_text = "Нужно поработать"
    elif score <= 5:
        score_indicator = "🟠"
        score_text = "Неплохо, но есть куда расти"
    elif score <= 7:
        score_indicator = "🟡"
        score_text = "Хорошо!"
    elif score <= 9:
        score_indicator = "🟢"
        score_text = "Отлично!"
    else:
        score_indicator = "⭐"
        score_text = "Превосходно!"

    message_parts = [
        "<b>📊 Оценка твоего ответа</b>\n",
        f"\n{score_indicator} <b>Балл: {score}/10</b> — {score_text}\n",
    ]

    # Strengths
    if evaluation.strengths:
        message_parts.append("\n<b>✅ Сильные стороны:</b>")
        for strength in evaluation.strengths:
            message_parts.append(f"\n• {strength}")

    # Improvements
    if evaluation.improvements:
        message_parts.append("\n\n<b>📈 Что можно улучшить:</b>")
        for improvement in evaluation.improvements:
            message_parts.append(f"\n• {improvement}")

    # Reference answer
    message_parts.append(
        f"\n\n<b>📚 Эталонный ответ:</b>\n{evaluation.reference_answer}"
    )

    # Daily progress and streak
    message_parts.append("\n\n" + "-" * 20)
    if questions_today >= daily_goal:
        message_parts.append(
            f"\n🎯 <b>Прогресс дня:</b> {questions_today}/{daily_goal} ✅ "
            "Дневная норма выполнена!"
        )
    else:
        remaining = daily_goal - questions_today
        message_parts.append(
            f"\n🎯 <b>Прогресс дня:</b> {questions_today}/{daily_goal} "
            f"(ещё {remaining})"
        )

    if current_streak > 0:
        message_parts.append(f"\n🔥 <b>Streak:</b> {current_streak} д.")

    return "".join(message_parts)


@router.message(PracticeStates.waiting_answer, F.text)
async def process_text_answer(message: Message, state: FSMContext) -> None:
    """Handle text answer from user.

    Args:
        message: The incoming Telegram message with user's answer
        state: FSM context with question data
    """
    if message.from_user is None or message.text is None:
        logger.warning("Received answer without from_user or text")
        return

    telegram_id = message.from_user.id
    user_answer = sanitize_text(message.text)

    if not user_answer:
        await message.answer(
            "Твой ответ пустой. Пожалуйста, напиши что-нибудь или отправь голосовое."
        )
        return

    # Get question data from FSM state
    state_data = await state.get_data()
    question_text = state_data.get("question_text")
    user_id_str = state_data.get("user_id")
    question_category_str = state_data.get("question_category")
    question_difficulty = state_data.get("question_difficulty")
    question_started_at = state_data.get("question_started_at")

    if not question_text or not user_id_str:
        logger.warning(
            "Missing question data in FSM state for telegram_id=%d", telegram_id
        )
        await message.answer(
            "Что-то пошло не так. Пожалуйста, начни новую сессию через /practice."
        )
        await state.clear()
        return

    # Calculate response time from question start
    response_time_ms: int | None = None
    if question_started_at:
        response_time_ms = int((time.time() - question_started_at) * 1000)

    # Get user profile to determine grade for evaluation context
    user_id = UUID(user_id_str)
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user_id)

    if profile is None:
        logger.warning(
            "Profile not found for user_id=%s during answer evaluation", user_id
        )
        await message.answer(
            "Не удалось найти твой профиль. "
            "Пожалуйста, пройди настройку через /start."
        )
        await state.clear()
        return

    # Set state to processing
    await state.set_state(PracticeStates.processing_answer)

    # Show typing indicator during evaluation
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    logger.info(
        "Evaluating answer from telegram_id=%d: answer_len=%d, grade=%s",
        telegram_id,
        len(user_answer),
        profile.grade,
    )

    try:
        evaluation = await evaluate_answer(
            question=question_text,
            answer=user_answer,
            grade=profile.grade,
        )
    except (EvaluationError, EvaluationParseError) as e:
        logger.error(
            "Failed to evaluate answer for telegram_id=%d: %s", telegram_id, e
        )
        await message.answer(
            "Произошла ошибка при оценке ответа. "
            "Пожалуйста, попробуй ещё раз через /practice."
        )
        await state.clear()
        return
    except Exception as e:
        logger.exception(
            "Unexpected error evaluating answer for telegram_id=%d: %s",
            telegram_id,
            e,
        )
        await message.answer(
            "Произошла неожиданная ошибка. "
            "Пожалуйста, попробуй ещё раз позже."
        )
        await state.clear()
        return

    # Parse question category from stored string
    question_category: Category | None = None
    if question_category_str:
        try:
            question_category = Category(question_category_str)
        except ValueError:
            logger.warning(
                "Unknown category from state: %s", question_category_str
            )

    # Create and save QuestionSession to database
    session_repo = SessionRepository()

    # Format AI feedback for storage (combine strengths and improvements)
    ai_feedback_parts = []
    if evaluation.strengths:
        ai_feedback_parts.append("Сильные стороны: " + "; ".join(evaluation.strengths))
    if evaluation.improvements:
        ai_feedback_parts.append("Что улучшить: " + "; ".join(evaluation.improvements))
    ai_feedback = "\n".join(ai_feedback_parts) if ai_feedback_parts else None

    session = QuestionSession(
        user_id=user_id,
        question_text=question_text,
        question_category=question_category,
        question_difficulty=question_difficulty,
        user_answer=user_answer,
        answer_type=AnswerType.TEXT,
        ai_score=evaluation.score,
        ai_feedback=ai_feedback,
        reference_answer=evaluation.reference_answer,
        response_time_ms=response_time_ms,
    )

    try:
        saved_session = await session_repo.create(session)
        logger.info(
            "Saved question session to database: id=%s, user_id=%s, score=%d",
            saved_session.id,
            saved_session.user_id,
            saved_session.ai_score or 0,
        )
    except Exception as e:
        # Log error but don't fail the user experience
        logger.error(
            "Failed to save session to database for telegram_id=%d: %s",
            telegram_id,
            e,
        )

    # Record answer in progress (streak, daily count)
    current_streak = 0
    milestone: int | None = None
    try:
        progress = await record_answer(user_id)
        questions_today = progress.questions_today
        current_streak = progress.current_streak

        # Check for streak milestone
        milestone = check_milestone(progress)
        if milestone:
            logger.info(
                "User telegram_id=%d reached streak milestone: %d days",
                telegram_id,
                milestone,
            )
    except Exception as e:
        logger.warning(
            "Failed to record progress for user_id=%s: %s", user_id, e
        )
        # Fallback to session count
        try:
            questions_today = await session_repo.get_today_count(user_id)
        except Exception:
            questions_today = 1

    # Adapt difficulty based on recent performance
    try:
        new_difficulty = await adjust_difficulty(user_id)
        if new_difficulty is not None:
            logger.info(
                "Difficulty adjusted for telegram_id=%d: new_difficulty=%d",
                telegram_id,
                new_difficulty,
            )
    except Exception as e:
        logger.warning(
            "Failed to adjust difficulty for user_id=%s: %s", user_id, e
        )

    # Format and send feedback with 'Next Question' button
    feedback_message = _format_feedback_message(
        evaluation=evaluation,
        questions_today=questions_today,
        current_streak=current_streak,
    )
    await message.answer(
        feedback_message,
        reply_markup=get_next_question_keyboard(),
    )

    # Send milestone celebration as a separate message
    if milestone:
        celebration = _format_milestone_message(milestone)
        if celebration:
            await message.answer(celebration)

    logger.info(
        "Sent feedback to telegram_id=%d: score=%d, response_time_ms=%s, "
        "questions_today=%d, streak=%d",
        telegram_id,
        evaluation.score,
        response_time_ms,
        questions_today,
        current_streak,
    )

    # Clear FSM state after successful evaluation
    await state.clear()


@router.message(PracticeStates.waiting_answer, F.voice)
async def process_voice_answer(message: Message, state: FSMContext) -> None:
    """Handle voice message answer from user.

    Downloads the voice message, transcribes it using Whisper API,
    and evaluates the transcribed text.

    Args:
        message: The incoming Telegram message with user's voice answer
        state: FSM context with question data
    """
    if message.from_user is None or message.voice is None:
        logger.warning("Received voice answer without from_user or voice")
        return

    telegram_id = message.from_user.id
    voice = message.voice

    # Get question data from FSM state
    state_data = await state.get_data()
    question_text = state_data.get("question_text")
    user_id_str = state_data.get("user_id")
    question_category_str = state_data.get("question_category")
    question_difficulty = state_data.get("question_difficulty")
    question_started_at = state_data.get("question_started_at")

    if not question_text or not user_id_str:
        logger.warning(
            "Missing question data in FSM state for telegram_id=%d", telegram_id
        )
        await message.answer(
            "Что-то пошло не так. Пожалуйста, начни новую сессию через /practice."
        )
        await state.clear()
        return

    # Calculate response time from question start
    response_time_ms: int | None = None
    if question_started_at:
        response_time_ms = int((time.time() - question_started_at) * 1000)

    # Get user profile to determine grade for evaluation context
    user_id = UUID(user_id_str)
    profile_repo = ProfileRepository()
    profile = await profile_repo.get_by_user_id(user_id)

    if profile is None:
        logger.warning(
            "Profile not found for user_id=%s during voice answer evaluation", user_id
        )
        await message.answer(
            "Не удалось найти твой профиль. "
            "Пожалуйста, пройди настройку через /start."
        )
        await state.clear()
        return

    # Set state to processing
    await state.set_state(PracticeStates.processing_answer)

    # Show typing indicator during download and transcription
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    logger.info(
        "Processing voice answer from telegram_id=%d: duration=%ds, file_size=%d",
        telegram_id,
        voice.duration,
        voice.file_size or 0,
    )

    # Download voice file to temporary location
    temp_file_path: Path | None = None
    try:
        # Get file from Telegram
        file = await message.bot.get_file(voice.file_id)
        if file.file_path is None:
            logger.error("Failed to get file path for voice message")
            await message.answer(
                "Не удалось загрузить голосовое сообщение. "
                "Пожалуйста, попробуй ещё раз или напиши ответ текстом."
            )
            await state.clear()
            return

        # Create temp file with .ogg extension (Telegram voice format)
        with tempfile.NamedTemporaryFile(
            suffix=".ogg", delete=False
        ) as temp_file:
            temp_file_path = Path(temp_file.name)

        # Download file
        await message.bot.download_file(file.file_path, destination=temp_file_path)

        logger.info(
            "Downloaded voice file to temp path: %s, size=%d",
            temp_file_path,
            temp_file_path.stat().st_size,
        )

        # Show typing indicator during transcription
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

        # Transcribe the audio
        try:
            user_answer = await transcribe(temp_file_path, language="ru")
        except InvalidAudioError as e:
            logger.error(
                "Invalid audio file from telegram_id=%d: %s", telegram_id, e
            )
            await message.answer(
                "Не удалось распознать голосовое сообщение. "
                "Попробуй записать его ещё раз или напиши ответ текстом."
            )
            await state.clear()
            return
        except TranscriptionError as e:
            logger.error(
                "Transcription failed for telegram_id=%d: %s", telegram_id, e
            )
            await message.answer(
                "Произошла ошибка при распознавании речи. "
                "Пожалуйста, попробуй ещё раз или напиши ответ текстом."
            )
            await state.clear()
            return

        user_answer = sanitize_text(user_answer)
        if not user_answer:
            logger.warning(
                "Empty transcription result for telegram_id=%d", telegram_id
            )
            await message.answer(
                "Не удалось распознать речь в голосовом сообщении. "
                "Попробуй записать его ещё раз или напиши ответ текстом."
            )
            await state.clear()
            return
        logger.info(
            "Transcription successful for telegram_id=%d: %d characters",
            telegram_id,
            len(user_answer),
        )

    finally:
        # Always clean up temp file
        if temp_file_path and temp_file_path.exists():
            try:
                os.unlink(temp_file_path)
                logger.debug("Deleted temp file: %s", temp_file_path)
            except OSError as e:
                logger.warning("Failed to delete temp file %s: %s", temp_file_path, e)

    # Show typing indicator during evaluation
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    logger.info(
        "Evaluating voice answer from telegram_id=%d: answer_len=%d, grade=%s",
        telegram_id,
        len(user_answer),
        profile.grade,
    )

    try:
        evaluation = await evaluate_answer(
            question=question_text,
            answer=user_answer,
            grade=profile.grade,
        )
    except (EvaluationError, EvaluationParseError) as e:
        logger.error(
            "Failed to evaluate voice answer for telegram_id=%d: %s", telegram_id, e
        )
        await message.answer(
            "Произошла ошибка при оценке ответа. "
            "Пожалуйста, попробуй ещё раз через /practice."
        )
        await state.clear()
        return
    except Exception as e:
        logger.exception(
            "Unexpected error evaluating voice answer for telegram_id=%d: %s",
            telegram_id,
            e,
        )
        await message.answer(
            "Произошла неожиданная ошибка. "
            "Пожалуйста, попробуй ещё раз позже."
        )
        await state.clear()
        return

    # Parse question category from stored string
    question_category: Category | None = None
    if question_category_str:
        try:
            question_category = Category(question_category_str)
        except ValueError:
            logger.warning(
                "Unknown category from state: %s", question_category_str
            )

    # Create and save QuestionSession to database
    session_repo = SessionRepository()

    # Format AI feedback for storage (combine strengths and improvements)
    ai_feedback_parts = []
    if evaluation.strengths:
        ai_feedback_parts.append("Сильные стороны: " + "; ".join(evaluation.strengths))
    if evaluation.improvements:
        ai_feedback_parts.append("Что улучшить: " + "; ".join(evaluation.improvements))
    ai_feedback = "\n".join(ai_feedback_parts) if ai_feedback_parts else None

    session = QuestionSession(
        user_id=user_id,
        question_text=question_text,
        question_category=question_category,
        question_difficulty=question_difficulty,
        user_answer=user_answer,
        answer_type=AnswerType.VOICE,
        ai_score=evaluation.score,
        ai_feedback=ai_feedback,
        reference_answer=evaluation.reference_answer,
        response_time_ms=response_time_ms,
    )

    try:
        saved_session = await session_repo.create(session)
        logger.info(
            "Saved voice question session to database: id=%s, user_id=%s, score=%d",
            saved_session.id,
            saved_session.user_id,
            saved_session.ai_score or 0,
        )
    except Exception as e:
        # Log error but don't fail the user experience
        logger.error(
            "Failed to save voice session to database for telegram_id=%d: %s",
            telegram_id,
            e,
        )

    # Record answer in progress (streak, daily count)
    current_streak = 0
    milestone: int | None = None
    try:
        progress = await record_answer(user_id)
        questions_today = progress.questions_today
        current_streak = progress.current_streak

        # Check for streak milestone
        milestone = check_milestone(progress)
        if milestone:
            logger.info(
                "User telegram_id=%d reached streak milestone: %d days",
                telegram_id,
                milestone,
            )
    except Exception as e:
        logger.warning(
            "Failed to record progress for user_id=%s: %s", user_id, e
        )
        # Fallback to session count
        try:
            questions_today = await session_repo.get_today_count(user_id)
        except Exception:
            questions_today = 1

    # Adapt difficulty based on recent performance
    try:
        new_difficulty = await adjust_difficulty(user_id)
        if new_difficulty is not None:
            logger.info(
                "Difficulty adjusted for telegram_id=%d: new_difficulty=%d",
                telegram_id,
                new_difficulty,
            )
    except Exception as e:
        logger.warning(
            "Failed to adjust difficulty for user_id=%s: %s", user_id, e
        )

    # Send transcription to user for reference
    await message.answer(
        f"<i>🎤 Распознанный текст:</i>\n{user_answer}"
    )

    # Format and send feedback with 'Next Question' button
    feedback_message = _format_feedback_message(
        evaluation=evaluation,
        questions_today=questions_today,
        current_streak=current_streak,
    )
    await message.answer(
        feedback_message,
        reply_markup=get_next_question_keyboard(),
    )

    # Send milestone celebration as a separate message
    if milestone:
        celebration = _format_milestone_message(milestone)
        if celebration:
            await message.answer(celebration)

    logger.info(
        "Sent voice feedback to telegram_id=%d: score=%d, response_time_ms=%s, "
        "questions_today=%d, streak=%d",
        telegram_id,
        evaluation.score,
        response_time_ms,
        questions_today,
        current_streak,
    )

    # Clear FSM state after successful evaluation
    await state.clear()


@router.callback_query(NextQuestionCallback.filter(F.action == "next"))
async def process_next_question_callback(
    callback: CallbackQuery, state: FSMContext, user: User | None = None
) -> None:
    """Handle 'Next Question' button callback.

    Args:
        callback: The callback query from the button press
        state: FSM context for managing conversation state
        user: User domain object injected by AuthMiddleware
    """
    if callback.message is None:
        logger.warning("Received next question callback without message")
        await callback.answer()
        return

    # Acknowledge the callback
    await callback.answer()

    if callback.from_user is None:
        logger.warning("Received callback without from_user")
        return

    telegram_id = callback.from_user.id
    profile_repo = ProfileRepository()

    if user is None:
        logger.warning(
            "User not found for telegram_id=%d in next question callback",
            telegram_id,
        )
        await callback.message.answer(
            "Похоже, ты ещё не зарегистрирован. "
            "Отправь /start для начала работы."
        )
        return

    # Check if user has a profile
    profile = await profile_repo.get_by_user_id(user.id)
    if profile is None:
        logger.info(
            "User telegram_id=%d has no profile in next question callback",
            telegram_id,
        )
        await callback.message.answer(
            "Чтобы продолжить практику, нужно сначала настроить профиль.\n\n"
            "Отправь /start чтобы пройти настройку."
        )
        return

    # Generate a new question
    logger.info(
        "Generating next question for user telegram_id=%d via callback",
        telegram_id,
    )

    # Show typing indicator while generating
    await callback.message.bot.send_chat_action(
        chat_id=callback.message.chat.id, action="typing"
    )

    # Fetch recent questions to avoid repeats
    recent_questions: list[str] | None = None
    try:
        session_repo = SessionRepository()
        recent_sessions = await session_repo.get_last_n_by_user(user.id, 20)
        if recent_sessions:
            recent_questions = [s.question_text for s in recent_sessions]
    except Exception as e:
        logger.warning(
            "Failed to fetch recent sessions for dedup, telegram_id=%d: %s",
            telegram_id,
            e,
        )

    try:
        question = await generate_question(profile, recent_questions)
    except (QuestionGenerationError, QuestionParseError) as e:
        logger.error(
            "Failed to generate question for telegram_id=%d: %s", telegram_id, e
        )
        await callback.message.answer(
            "Произошла ошибка при генерации вопроса. "
            "Пожалуйста, попробуй ещё раз через /practice."
        )
        return
    except Exception as e:
        logger.exception(
            "Unexpected error generating question for telegram_id=%d: %s",
            telegram_id,
            e,
        )
        await callback.message.answer(
            "Произошла неожиданная ошибка. "
            "Пожалуйста, попробуй ещё раз позже."
        )
        return

    # Store question in FSM state for later evaluation
    # Include question_started_at for response_time_ms calculation
    await state.update_data(
        question_id=str(question.id),
        question_text=question.text,
        question_category=question.category.value,
        question_difficulty=question.difficulty,
        user_id=str(user.id),
        question_started_at=time.time(),
    )

    # Set FSM state to waiting for answer
    await state.set_state(PracticeStates.waiting_answer)

    # Send the question
    question_message = _format_question_message(question)
    await callback.message.answer(question_message)

    logger.info(
        "Sent next question to telegram_id=%d via callback: category=%s, difficulty=%d",
        telegram_id,
        question.category,
        question.difficulty,
    )
