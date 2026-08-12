"""Business logic services."""

from bot.services.difficulty_service import (
    DifficultyServiceError,
    adjust_difficulty,
)
from bot.services.evaluation_service import (
    EvaluationError,
    EvaluationParseError,
    EvaluationServiceError,
    evaluate_answer,
)
from bot.services.progress_service import (
    ProgressServiceError,
    check_daily_goal,
    check_milestone,
    record_answer,
)
from bot.services.question_service import (
    QuestionGenerationError,
    QuestionParseError,
    QuestionServiceError,
    generate_question,
)
from bot.services.subscription_service import (
    SubscriptionServiceError,
    activate_subscription,
    check_access,
    get_active_subscription,
    has_free_questions_today,
)
from bot.services.transcription_service import (
    InvalidAudioError,
    TranscriptionError,
    TranscriptionServiceError,
    transcribe,
)

__all__ = [
    # Difficulty service
    "DifficultyServiceError",
    "adjust_difficulty",
    # Evaluation service
    "EvaluationError",
    "EvaluationParseError",
    "EvaluationServiceError",
    "evaluate_answer",
    # Progress service
    "ProgressServiceError",
    "check_daily_goal",
    "check_milestone",
    "record_answer",
    # Question service
    "QuestionGenerationError",
    "QuestionParseError",
    "QuestionServiceError",
    "generate_question",
    # Subscription service
    "SubscriptionServiceError",
    "activate_subscription",
    "check_access",
    "get_active_subscription",
    "has_free_questions_today",
    # Transcription service
    "InvalidAudioError",
    "TranscriptionError",
    "TranscriptionServiceError",
    "transcribe",
]
