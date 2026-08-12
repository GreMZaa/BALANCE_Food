"""Tests for Question, QuestionSession, and Evaluation domain entities."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from bot.domain.entities import (
    AnswerType,
    Category,
    Evaluation,
    Question,
    QuestionSession,
)


class TestQuestion:
    """Tests for Question domain model."""

    def test_question_creation_with_required_fields(self) -> None:
        """Test creating a Question with required fields."""
        question = Question(
            text="What is polymorphism?",
            category=Category.LANGUAGE,
            difficulty=5,
        )
        assert question.text == "What is polymorphism?"
        assert question.category == Category.LANGUAGE
        assert question.difficulty == 5
        assert isinstance(question.id, UUID)

    def test_question_creation_with_custom_id(self) -> None:
        """Test creating a Question with a custom ID."""
        custom_id = uuid4()
        question = Question(
            id=custom_id,
            text="Explain SOLID principles",
            category=Category.ARCHITECTURE,
            difficulty=7,
        )
        assert question.id == custom_id

    def test_question_difficulty_validation_min(self) -> None:
        """Test that difficulty must be at least 1."""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                text="Test question",
                category=Category.ALGORITHMS,
                difficulty=0,
            )
        assert "greater than or equal to 1" in str(exc_info.value)

    def test_question_difficulty_validation_max(self) -> None:
        """Test that difficulty must be at most 10."""
        with pytest.raises(ValidationError) as exc_info:
            Question(
                text="Test question",
                category=Category.ALGORITHMS,
                difficulty=11,
            )
        assert "less than or equal to 10" in str(exc_info.value)

    def test_question_text_validation_empty(self) -> None:
        """Test that question text cannot be empty."""
        with pytest.raises(ValidationError):
            Question(
                text="",
                category=Category.DATABASES,
                difficulty=3,
            )

    def test_question_serialization(self) -> None:
        """Test Question serialization to JSON."""
        question = Question(
            text="What is REST?",
            category=Category.API_DESIGN,
            difficulty=4,
        )
        json_data = question.model_dump_json()
        assert "What is REST?" in json_data
        assert "api_design" in json_data
        assert "4" in json_data

    def test_question_all_categories(self) -> None:
        """Test that Question accepts all Category values."""
        for category in Category:
            question = Question(
                text=f"Question about {category}",
                category=category,
                difficulty=5,
            )
            assert question.category == category


class TestQuestionSession:
    """Tests for QuestionSession domain model."""

    def test_session_creation_minimal(self) -> None:
        """Test creating a QuestionSession with minimal fields."""
        user_id = uuid4()
        session = QuestionSession(
            user_id=user_id,
            question_text="What is a binary tree?",
        )
        assert session.user_id == user_id
        assert session.question_text == "What is a binary tree?"
        assert session.user_answer is None
        assert session.ai_score is None
        assert session.answer_type == AnswerType.TEXT
        assert isinstance(session.id, UUID)
        assert isinstance(session.created_at, datetime)

    def test_session_creation_full(self) -> None:
        """Test creating a QuestionSession with all fields."""
        user_id = uuid4()
        session_id = uuid4()
        created = datetime.now(UTC)

        session = QuestionSession(
            id=session_id,
            user_id=user_id,
            question_text="Explain microservices architecture",
            question_category=Category.MICROSERVICES,
            question_difficulty=8,
            user_answer="Microservices is an architectural style...",
            answer_type=AnswerType.VOICE,
            ai_score=7,
            ai_feedback="Good explanation of the concept.",
            reference_answer="Microservices architecture is...",
            response_time_ms=45000,
            created_at=created,
        )

        assert session.id == session_id
        assert session.user_id == user_id
        assert session.question_text == "Explain microservices architecture"
        assert session.question_category == Category.MICROSERVICES
        assert session.question_difficulty == 8
        assert session.user_answer == "Microservices is an architectural style..."
        assert session.answer_type == AnswerType.VOICE
        assert session.ai_score == 7
        assert session.ai_feedback == "Good explanation of the concept."
        assert session.reference_answer == "Microservices architecture is..."
        assert session.response_time_ms == 45000
        assert session.created_at == created

    def test_session_is_answered_false(self) -> None:
        """Test is_answered returns False when no answer provided."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="Test question",
        )
        assert session.is_answered() is False

    def test_session_is_answered_true(self) -> None:
        """Test is_answered returns True when answer provided."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="Test question",
            user_answer="My answer",
        )
        assert session.is_answered() is True

    def test_session_is_evaluated_false_no_score(self) -> None:
        """Test is_evaluated returns False when no score."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="Test question",
            ai_feedback="Some feedback",
        )
        assert session.is_evaluated() is False

    def test_session_is_evaluated_false_no_feedback(self) -> None:
        """Test is_evaluated returns False when no feedback."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="Test question",
            ai_score=8,
        )
        assert session.is_evaluated() is False

    def test_session_is_evaluated_true(self) -> None:
        """Test is_evaluated returns True when both score and feedback present."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="Test question",
            ai_score=8,
            ai_feedback="Good answer!",
        )
        assert session.is_evaluated() is True

    def test_session_ai_score_validation_min(self) -> None:
        """Test that ai_score must be at least 1."""
        with pytest.raises(ValidationError):
            QuestionSession(
                user_id=uuid4(),
                question_text="Test",
                ai_score=0,
            )

    def test_session_ai_score_validation_max(self) -> None:
        """Test that ai_score must be at most 10."""
        with pytest.raises(ValidationError):
            QuestionSession(
                user_id=uuid4(),
                question_text="Test",
                ai_score=11,
            )

    def test_session_difficulty_validation_min(self) -> None:
        """Test that question_difficulty must be at least 1."""
        with pytest.raises(ValidationError):
            QuestionSession(
                user_id=uuid4(),
                question_text="Test",
                question_difficulty=0,
            )

    def test_session_difficulty_validation_max(self) -> None:
        """Test that question_difficulty must be at most 10."""
        with pytest.raises(ValidationError):
            QuestionSession(
                user_id=uuid4(),
                question_text="Test",
                question_difficulty=11,
            )

    def test_session_response_time_validation(self) -> None:
        """Test that response_time_ms must be non-negative."""
        with pytest.raises(ValidationError):
            QuestionSession(
                user_id=uuid4(),
                question_text="Test",
                response_time_ms=-1,
            )

    def test_session_answer_type_values(self) -> None:
        """Test both answer types are accepted."""
        for answer_type in AnswerType:
            session = QuestionSession(
                user_id=uuid4(),
                question_text="Test",
                answer_type=answer_type,
            )
            assert session.answer_type == answer_type

    def test_session_serialization(self) -> None:
        """Test QuestionSession serialization to JSON."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="What is SQL injection?",
            question_category=Category.DATABASES,
            question_difficulty=6,
            user_answer="SQL injection is...",
            ai_score=8,
        )
        json_data = session.model_dump_json()
        assert "What is SQL injection?" in json_data
        assert "databases" in json_data


class TestEvaluation:
    """Tests for Evaluation domain model."""

    def test_evaluation_creation(self) -> None:
        """Test creating an Evaluation with required fields."""
        evaluation = Evaluation(
            score=8,
            reference_answer="A complete answer would be...",
        )
        assert evaluation.score == 8
        assert evaluation.strengths == []
        assert evaluation.improvements == []
        assert evaluation.reference_answer == "A complete answer would be..."

    def test_evaluation_creation_full(self) -> None:
        """Test creating an Evaluation with all fields."""
        evaluation = Evaluation(
            score=7,
            strengths=["Good structure", "Clear explanation"],
            improvements=["Add more examples", "Mention edge cases"],
            reference_answer="The ideal answer is...",
        )
        assert evaluation.score == 7
        assert len(evaluation.strengths) == 2
        assert len(evaluation.improvements) == 2
        assert "Good structure" in evaluation.strengths
        assert "Add more examples" in evaluation.improvements

    def test_evaluation_score_validation_min(self) -> None:
        """Test that score must be at least 1."""
        with pytest.raises(ValidationError):
            Evaluation(score=0, reference_answer="Answer")

    def test_evaluation_score_validation_max(self) -> None:
        """Test that score must be at most 10."""
        with pytest.raises(ValidationError):
            Evaluation(score=11, reference_answer="Answer")

    def test_evaluation_reference_answer_required(self) -> None:
        """Test that reference_answer is required."""
        with pytest.raises(ValidationError):
            Evaluation(score=5)  # type: ignore[call-arg]

    def test_evaluation_serialization(self) -> None:
        """Test Evaluation serialization to JSON."""
        evaluation = Evaluation(
            score=9,
            strengths=["Excellent"],
            improvements=[],
            reference_answer="Perfect answer",
        )
        json_data = evaluation.model_dump_json()
        assert "9" in json_data
        assert "Excellent" in json_data
        assert "Perfect answer" in json_data

    def test_evaluation_from_dict(self) -> None:
        """Test Evaluation creation from dictionary."""
        data = {
            "score": 6,
            "strengths": ["Point 1"],
            "improvements": ["Area 1", "Area 2"],
            "reference_answer": "Reference",
        }
        evaluation = Evaluation.model_validate(data)
        assert evaluation.score == 6
        assert evaluation.strengths == ["Point 1"]
        assert len(evaluation.improvements) == 2
