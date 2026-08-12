"""Tests for session repository module."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import AnswerType, Category
from bot.domain.entities.question import QuestionSession
from bot.repositories.session_repository import (
    SessionNotFoundError,
    SessionRepository,
    SessionRepositoryError,
)


@pytest.fixture
def session_repo():
    """Create a SessionRepository instance."""
    return SessionRepository()


@pytest.fixture
def sample_session_data():
    """Sample session data as it would come from database."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "question_text": "What is a REST API?",
        "question_category": "api_design",
        "question_difficulty": 5,
        "user_answer": "REST API is...",
        "answer_type": "text",
        "ai_score": 7,
        "ai_feedback": "Good explanation.",
        "reference_answer": "A REST API is...",
        "response_time_ms": 30000,
        "created_at": "2026-01-27T10:00:00+00:00",
    }


@pytest.fixture
def sample_session():
    """Create a sample QuestionSession domain model."""
    return QuestionSession(
        user_id=uuid4(),
        question_text="What is a REST API?",
        question_category=Category.API_DESIGN,
        question_difficulty=5,
    )


class TestSessionRepositoryConversion:
    """Tests for conversion methods."""

    def test_convert_db_row_to_session(
        self, session_repo: SessionRepository, sample_session_data: dict
    ):
        """Test converting database row to QuestionSession model."""
        session = session_repo._convert_db_row_to_session(sample_session_data)

        assert isinstance(session, QuestionSession)
        assert session.question_text == "What is a REST API?"
        assert session.question_category == Category.API_DESIGN
        assert session.question_difficulty == 5
        assert session.user_answer == "REST API is..."
        assert session.answer_type == AnswerType.TEXT
        assert session.ai_score == 7
        assert session.ai_feedback == "Good explanation."
        assert session.reference_answer == "A REST API is..."
        assert session.response_time_ms == 30000

    def test_convert_db_row_with_null_category(self, session_repo: SessionRepository):
        """Test converting row with null category."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "question_text": "Test question",
            "question_category": None,
            "question_difficulty": None,
            "user_answer": None,
            "answer_type": "text",
            "ai_score": None,
            "ai_feedback": None,
            "reference_answer": None,
            "response_time_ms": None,
            "created_at": "2026-01-27T10:00:00+00:00",
        }
        session = session_repo._convert_db_row_to_session(data)

        assert session.question_category is None
        assert session.question_difficulty is None
        assert session.answer_type == AnswerType.TEXT

    def test_convert_db_row_with_unknown_category(
        self, session_repo: SessionRepository
    ):
        """Test converting row with unknown category falls back to None."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "question_text": "Test question",
            "question_category": "unknown_category",
            "question_difficulty": 5,
            "user_answer": None,
            "answer_type": "text",
            "ai_score": None,
            "ai_feedback": None,
            "reference_answer": None,
            "response_time_ms": None,
            "created_at": "2026-01-27T10:00:00+00:00",
        }
        session = session_repo._convert_db_row_to_session(data)

        assert session.question_category is None

    def test_convert_db_row_with_voice_answer_type(
        self, session_repo: SessionRepository
    ):
        """Test converting row with voice answer type."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "question_text": "Test question",
            "question_category": "databases",
            "question_difficulty": 5,
            "user_answer": "transcribed answer",
            "answer_type": "voice",
            "ai_score": 8,
            "ai_feedback": "Great!",
            "reference_answer": "Reference",
            "response_time_ms": 45000,
            "created_at": "2026-01-27T10:00:00+00:00",
        }
        session = session_repo._convert_db_row_to_session(data)

        assert session.answer_type == AnswerType.VOICE
        assert session.question_category == Category.DATABASES

    def test_session_to_db_dict(
        self, session_repo: SessionRepository, sample_session: QuestionSession
    ):
        """Test converting QuestionSession to database dict."""
        sample_session.user_answer = "My answer"
        sample_session.ai_score = 8
        sample_session.ai_feedback = "Good job!"
        sample_session.reference_answer = "Reference answer"

        data = session_repo._session_to_db_dict(sample_session)

        assert data["user_id"] == str(sample_session.user_id)
        assert data["question_text"] == "What is a REST API?"
        assert data["question_category"] == "api_design"
        assert data["question_difficulty"] == 5
        assert data["user_answer"] == "My answer"
        assert data["answer_type"] == "text"
        assert data["ai_score"] == 8
        assert data["ai_feedback"] == "Good job!"
        assert data["reference_answer"] == "Reference answer"

    def test_session_to_db_dict_with_null_category(
        self, session_repo: SessionRepository
    ):
        """Test converting session with null category to dict."""
        session = QuestionSession(
            user_id=uuid4(),
            question_text="Test",
            question_category=None,
        )
        data = session_repo._session_to_db_dict(session)

        assert data["question_category"] is None


class TestSessionRepositoryCreate:
    """Tests for create method."""

    async def test_create_session_success(
        self,
        session_repo: SessionRepository,
        sample_session: QuestionSession,
        sample_session_data: dict,
    ):
        """Test creating a new session."""
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.create(sample_session)

        assert result is not None
        assert isinstance(result, QuestionSession)
        assert result.question_text == sample_session_data["question_text"]

    async def test_create_session_no_data_returned(
        self, session_repo: SessionRepository, sample_session: QuestionSession
    ):
        """Test that create raises error when no data returned."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(SessionRepositoryError) as exc_info,
        ):
            await session_repo.create(sample_session)

        assert "No data returned" in str(exc_info.value)

    async def test_create_session_error(
        self, session_repo: SessionRepository, sample_session: QuestionSession
    ):
        """Test that database errors raise SessionRepositoryError."""
        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SessionRepositoryError) as exc_info,
        ):
            await session_repo.create(sample_session)

        assert "Failed to create session" in str(exc_info.value)


class TestSessionRepositoryGetById:
    """Tests for get_by_id method."""

    async def test_get_by_id_found(
        self, session_repo: SessionRepository, sample_session_data: dict
    ):
        """Test getting existing session by id."""
        session_id = sample_session_data["id"]
        mock_response = MagicMock()
        mock_response.data = [sample_session_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            result = await session_repo.get_by_id(UUID(session_id))

        assert result is not None
        assert isinstance(result, QuestionSession)

    async def test_get_by_id_not_found(self, session_repo: SessionRepository):
        """Test getting non-existent session returns None."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_by_id(uuid4())

        assert result is None

    async def test_get_by_id_error(self, session_repo: SessionRepository):
        """Test that database errors raise SessionRepositoryError."""
        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SessionRepositoryError) as exc_info,
        ):
            await session_repo.get_by_id(uuid4())

        assert "Failed to get session" in str(exc_info.value)


class TestSessionRepositoryGetLastNByUser:
    """Tests for get_last_n_by_user method."""

    async def test_get_last_n_by_user_found(
        self, session_repo: SessionRepository, sample_session_data: dict
    ):
        """Test getting last N sessions for a user."""
        user_id = uuid4()
        # Create multiple session records
        sessions_data = [sample_session_data.copy() for _ in range(3)]
        for s in sessions_data:
            s["id"] = str(uuid4())
            s["user_id"] = str(user_id)

        mock_response = MagicMock()
        mock_response.data = sessions_data

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_last_n_by_user(user_id, n=5)

        assert len(result) == 3
        assert all(isinstance(s, QuestionSession) for s in result)

    async def test_get_last_n_by_user_empty(self, session_repo: SessionRepository):
        """Test getting sessions for user with no sessions."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_last_n_by_user(uuid4(), n=5)

        assert result == []

    async def test_get_last_n_by_user_with_none_data(
        self, session_repo: SessionRepository
    ):
        """Test handling None data response."""
        mock_response = MagicMock()
        mock_response.data = None

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_last_n_by_user(uuid4(), n=5)

        assert result == []

    async def test_get_last_n_by_user_error(self, session_repo: SessionRepository):
        """Test that database errors raise SessionRepositoryError."""
        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SessionRepositoryError) as exc_info,
        ):
            await session_repo.get_last_n_by_user(uuid4(), n=5)

        assert "Failed to get last" in str(exc_info.value)


class TestSessionRepositoryGetTodayCount:
    """Tests for get_today_count method."""

    async def test_get_today_count_with_sessions(
        self, session_repo: SessionRepository
    ):
        """Test getting today's session count."""
        user_id = uuid4()

        mock_response = MagicMock()
        mock_response.count = 5

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_gte = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(gte=mock_gte))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_today_count(user_id)

        assert result == 5

    async def test_get_today_count_zero(self, session_repo: SessionRepository):
        """Test getting today's session count when zero."""
        mock_response = MagicMock()
        mock_response.count = 0

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_gte = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(gte=mock_gte))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_today_count(uuid4())

        assert result == 0

    async def test_get_today_count_none_count(self, session_repo: SessionRepository):
        """Test handling None count response."""
        mock_response = MagicMock()
        mock_response.count = None

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_gte = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(gte=mock_gte))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_today_count(uuid4())

        assert result == 0

    async def test_get_today_count_error(self, session_repo: SessionRepository):
        """Test that database errors raise SessionRepositoryError."""
        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SessionRepositoryError) as exc_info,
        ):
            await session_repo.get_today_count(uuid4())

        assert "Failed to get today's session count" in str(exc_info.value)


class TestSessionRepositoryUpdate:
    """Tests for update method."""

    async def test_update_session_success(
        self, session_repo: SessionRepository, sample_session_data: dict
    ):
        """Test updating an existing session."""
        session = session_repo._convert_db_row_to_session(sample_session_data)
        session.ai_score = 9
        session.ai_feedback = "Excellent!"

        updated_data = sample_session_data.copy()
        updated_data["ai_score"] = 9
        updated_data["ai_feedback"] = "Excellent!"

        mock_response = MagicMock()
        mock_response.data = [updated_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_eq = MagicMock(return_value=mock_query)
        mock_update = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(update=mock_update))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.update(session)

        assert result is not None
        assert result.ai_score == 9
        assert result.ai_feedback == "Excellent!"

    async def test_update_session_not_found(
        self, session_repo: SessionRepository, sample_session: QuestionSession
    ):
        """Test that updating non-existent session raises SessionNotFoundError."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_eq = MagicMock(return_value=mock_query)
        mock_update = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(update=mock_update))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(SessionNotFoundError) as exc_info,
        ):
            await session_repo.update(sample_session)

        assert "not found" in str(exc_info.value)

    async def test_update_session_error(
        self, session_repo: SessionRepository, sample_session: QuestionSession
    ):
        """Test that database errors raise SessionRepositoryError."""
        with (
            patch(
                "bot.repositories.session_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(SessionRepositoryError) as exc_info,
        ):
            await session_repo.update(sample_session)

        assert "Failed to update session" in str(exc_info.value)


class TestSessionRepositoryGetAverageScore:
    """Tests for get_average_score method."""

    async def test_get_average_score_with_scores(
        self, session_repo: SessionRepository
    ):
        """Test getting average score with evaluated sessions."""
        user_id = uuid4()
        # Create sessions with scores
        sessions_data = []
        for score in [8, 7, 9, 6, 8]:  # Average = 7.6
            sessions_data.append(
                {
                    "id": str(uuid4()),
                    "user_id": str(user_id),
                    "question_text": "Test",
                    "question_category": "api_design",
                    "question_difficulty": 5,
                    "user_answer": "answer",
                    "answer_type": "text",
                    "ai_score": score,
                    "ai_feedback": "feedback",
                    "reference_answer": "ref",
                    "response_time_ms": 1000,
                    "created_at": "2026-01-27T10:00:00+00:00",
                }
            )

        mock_response = MagicMock()
        mock_response.data = sessions_data

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_average_score(user_id, last_n=5)

        assert result == 7.6

    async def test_get_average_score_no_evaluated_sessions(
        self, session_repo: SessionRepository
    ):
        """Test getting average score when no sessions have scores."""
        user_id = uuid4()
        sessions_data = [
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "question_text": "Test",
                "question_category": None,
                "question_difficulty": None,
                "user_answer": None,
                "answer_type": "text",
                "ai_score": None,  # Not evaluated
                "ai_feedback": None,
                "reference_answer": None,
                "response_time_ms": None,
                "created_at": "2026-01-27T10:00:00+00:00",
            }
        ]

        mock_response = MagicMock()
        mock_response.data = sessions_data

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_average_score(user_id, last_n=5)

        assert result is None

    async def test_get_average_score_empty_sessions(
        self, session_repo: SessionRepository
    ):
        """Test getting average score when no sessions exist."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_average_score(uuid4(), last_n=5)

        assert result is None

    async def test_get_average_score_mixed_evaluated(
        self, session_repo: SessionRepository
    ):
        """Test average score with mix of evaluated and unevaluated sessions."""
        user_id = uuid4()
        sessions_data = [
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "question_text": "Test",
                "question_category": "api_design",
                "question_difficulty": 5,
                "user_answer": "answer",
                "answer_type": "text",
                "ai_score": 8,
                "ai_feedback": "feedback",
                "reference_answer": "ref",
                "response_time_ms": 1000,
                "created_at": "2026-01-27T10:00:00+00:00",
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "question_text": "Test",
                "question_category": None,
                "question_difficulty": None,
                "user_answer": None,
                "answer_type": "text",
                "ai_score": None,  # Not evaluated
                "ai_feedback": None,
                "reference_answer": None,
                "response_time_ms": None,
                "created_at": "2026-01-27T10:00:00+00:00",
            },
            {
                "id": str(uuid4()),
                "user_id": str(user_id),
                "question_text": "Test",
                "question_category": "databases",
                "question_difficulty": 6,
                "user_answer": "answer2",
                "answer_type": "text",
                "ai_score": 6,
                "ai_feedback": "ok",
                "reference_answer": "ref",
                "response_time_ms": 2000,
                "created_at": "2026-01-27T10:00:00+00:00",
            },
        ]

        mock_response = MagicMock()
        mock_response.data = sessions_data

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_order = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_eq = MagicMock(return_value=MagicMock(order=mock_order))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.session_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await session_repo.get_average_score(user_id, last_n=5)

        # Only 8 and 6 should be counted, average = 7.0
        assert result == 7.0


class TestSessionRepositoryErrors:
    """Tests for error classes."""

    def test_session_repository_error_is_exception(self):
        """Test SessionRepositoryError inherits from Exception."""
        error = SessionRepositoryError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_session_not_found_error_is_repository_error(self):
        """Test SessionNotFoundError inherits from SessionRepositoryError."""
        error = SessionNotFoundError("session not found")
        assert isinstance(error, SessionRepositoryError)
        assert isinstance(error, Exception)


class TestSessionRepositoryImports:
    """Tests for module imports."""

    def test_import_from_init(self):
        """Test that classes can be imported from repositories package."""
        from bot.repositories import (
            SessionNotFoundError,
            SessionRepository,
            SessionRepositoryError,
        )

        assert SessionRepository is not None
        assert SessionRepositoryError is not None
        assert SessionNotFoundError is not None
