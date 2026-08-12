"""Question and QuestionSession domain entities."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from bot.domain.entities.enums import AnswerType, Category


def _utc_now() -> datetime:
    """Get current UTC time (timezone-aware)."""
    return datetime.now(UTC)


class Question(BaseModel):
    """Question domain model.

    Represents an interview question generated for the user.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal question ID")
    text: str = Field(..., min_length=1, description="The interview question text")
    category: Category = Field(..., description="Category of the question")
    difficulty: int = Field(
        ..., ge=1, le=10, description="Difficulty level from 1 to 10"
    )

    model_config = {"from_attributes": True}


class QuestionSession(BaseModel):
    """Question session domain model.

    Represents a complete Q&A session including the question,
    user's answer, and AI evaluation.
    """

    id: UUID = Field(default_factory=uuid4, description="Internal session ID")
    user_id: UUID = Field(..., description="Reference to User.id")
    question_text: str = Field(..., description="The interview question text")
    question_category: Category | None = Field(
        default=None, description="Category of the question"
    )
    question_difficulty: int | None = Field(
        default=None, ge=1, le=10, description="Difficulty level 1-10"
    )
    user_answer: str | None = Field(
        default=None, description="User's answer text (transcribed if voice)"
    )
    answer_type: AnswerType = Field(
        default=AnswerType.TEXT, description="How user answered: text or voice"
    )
    ai_score: int | None = Field(
        default=None, ge=1, le=10, description="AI evaluation score 1-10"
    )
    ai_feedback: str | None = Field(
        default=None, description="Detailed AI feedback with strengths and improvements"
    )
    reference_answer: str | None = Field(
        default=None, description="Example good answer for comparison"
    )
    response_time_ms: int | None = Field(
        default=None, ge=0, description="Time user took to answer in milliseconds"
    )
    created_at: datetime = Field(
        default_factory=_utc_now, description="When the session was created"
    )

    model_config = {"from_attributes": True}

    def is_answered(self) -> bool:
        """Check if user has provided an answer."""
        return self.user_answer is not None

    def is_evaluated(self) -> bool:
        """Check if the answer has been evaluated by AI."""
        return self.ai_score is not None and self.ai_feedback is not None


class Evaluation(BaseModel):
    """AI evaluation result model.

    Contains the AI's assessment of a user's answer.
    """

    score: int = Field(..., ge=1, le=10, description="Overall score from 1 to 10")
    strengths: list[str] = Field(
        default_factory=list, description="List of strong points in the answer"
    )
    improvements: list[str] = Field(
        default_factory=list, description="List of areas for improvement"
    )
    reference_answer: str = Field(
        ..., description="Example of a good answer for comparison"
    )

    model_config = {"from_attributes": True}
