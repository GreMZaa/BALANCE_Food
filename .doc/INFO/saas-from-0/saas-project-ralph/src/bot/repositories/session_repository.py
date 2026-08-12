"""Session repository for database operations."""

import logging
from datetime import UTC, datetime
from uuid import UUID

from bot.domain.entities.enums import AnswerType, Category
from bot.domain.entities.question import QuestionSession
from bot.infrastructure.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class SessionRepositoryError(Exception):
    """Base exception for session repository errors."""


class SessionNotFoundError(SessionRepositoryError):
    """Raised when session is not found."""


class SessionRepository:
    """Repository for QuestionSession entity database operations.

    Handles CRUD operations for question_sessions table in Supabase.
    Returns domain models instead of raw dictionaries.
    """

    TABLE_NAME = "question_sessions"

    def _convert_db_row_to_session(self, row: dict) -> QuestionSession:
        """Convert database row to QuestionSession domain model.

        Handles conversion of enum strings to Python enums.

        Args:
            row: Database row as dictionary.

        Returns:
            QuestionSession domain model.
        """
        # Convert category string to Category enum if present
        question_category = None
        if row.get("question_category"):
            try:
                question_category = Category(row["question_category"])
            except ValueError:
                logger.warning(
                    "Unknown category: %s, setting to None", row["question_category"]
                )

        # Convert answer_type string to AnswerType enum
        answer_type = AnswerType.TEXT
        if row.get("answer_type"):
            try:
                answer_type = AnswerType(row["answer_type"])
            except ValueError:
                logger.warning(
                    "Unknown answer_type: %s, defaulting to TEXT", row["answer_type"]
                )

        return QuestionSession(
            id=UUID(row["id"]) if isinstance(row["id"], str) else row["id"],
            user_id=UUID(row["user_id"])
            if isinstance(row["user_id"], str)
            else row["user_id"],
            question_text=row["question_text"],
            question_category=question_category,
            question_difficulty=row.get("question_difficulty"),
            user_answer=row.get("user_answer"),
            answer_type=answer_type,
            ai_score=row.get("ai_score"),
            ai_feedback=row.get("ai_feedback"),
            reference_answer=row.get("reference_answer"),
            response_time_ms=row.get("response_time_ms"),
            created_at=row.get("created_at"),
        )

    def _session_to_db_dict(self, session: QuestionSession) -> dict:
        """Convert QuestionSession to database dictionary.

        Args:
            session: QuestionSession domain model.

        Returns:
            Dictionary suitable for database insertion.
        """
        data = {
            "user_id": str(session.user_id),
            "question_text": session.question_text,
            "question_category": session.question_category.value
            if session.question_category
            else None,
            "question_difficulty": session.question_difficulty,
            "user_answer": session.user_answer,
            "answer_type": session.answer_type.value,
            "ai_score": session.ai_score,
            "ai_feedback": session.ai_feedback,
            "reference_answer": session.reference_answer,
            "response_time_ms": session.response_time_ms,
        }
        return data

    async def create(self, session: QuestionSession) -> QuestionSession:
        """Create a new question session in the database.

        Args:
            session: The QuestionSession domain model to create.

        Returns:
            Created QuestionSession domain model with database-assigned fields.

        Raises:
            SessionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = self._session_to_db_dict(session)

            response = await client.table(self.TABLE_NAME).insert(data).execute()

            if not response.data:
                raise SessionRepositoryError("No data returned after insert")

            created_session = self._convert_db_row_to_session(response.data[0])
            logger.info(
                "Created question session: user_id=%s, id=%s",
                created_session.user_id,
                created_session.id,
            )
            return created_session

        except SessionRepositoryError:
            raise
        except Exception as e:
            error_msg = f"Failed to create session for user_id={session.user_id}: {e}"
            logger.exception(error_msg)
            raise SessionRepositoryError(error_msg) from e

    async def get_by_id(self, session_id: UUID) -> QuestionSession | None:
        """Get question session by ID.

        Args:
            session_id: The session UUID.

        Returns:
            QuestionSession domain model if found, None otherwise.

        Raises:
            SessionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("id", str(session_id))
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("Session with id=%s not found", session_id)
                return None

            logger.debug("Found session with id=%s", session_id)
            row = response.data[0] if isinstance(response.data, list) else response.data
            return self._convert_db_row_to_session(row)

        except Exception as e:
            error_msg = f"Failed to get session by id={session_id}: {e}"
            logger.exception(error_msg)
            raise SessionRepositoryError(error_msg) from e

    async def get_last_n_by_user(
        self, user_id: UUID, n: int = 5
    ) -> list[QuestionSession]:
        """Get last N question sessions for a user.

        Sessions are ordered by created_at descending (most recent first).

        Args:
            user_id: The user's internal UUID.
            n: Number of sessions to retrieve (default 5).

        Returns:
            List of QuestionSession models, ordered by most recent first.

        Raises:
            SessionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(n)
                .execute()
            )

            sessions = [
                self._convert_db_row_to_session(row) for row in (response.data or [])
            ]
            logger.debug(
                "Found %d sessions for user_id=%s (requested %d)",
                len(sessions),
                user_id,
                n,
            )
            return sessions

        except Exception as e:
            error_msg = f"Failed to get last {n} sessions for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise SessionRepositoryError(error_msg) from e

    async def get_today_count(self, user_id: UUID) -> int:
        """Get count of question sessions for today.

        Uses UTC time for day boundary calculation.

        Args:
            user_id: The user's internal UUID.

        Returns:
            Number of sessions created today.

        Raises:
            SessionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            # Get start of today in UTC
            today_start = datetime.now(UTC).replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            response = (
                await client.table(self.TABLE_NAME)
                .select("id", count="exact")
                .eq("user_id", str(user_id))
                .gte("created_at", today_start.isoformat())
                .execute()
            )

            count = response.count if response.count is not None else 0
            logger.debug(
                "User %s has %d sessions today (since %s)",
                user_id,
                count,
                today_start.isoformat(),
            )
            return count

        except Exception as e:
            error_msg = f"Failed to get today's session count for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise SessionRepositoryError(error_msg) from e

    async def update(self, session: QuestionSession) -> QuestionSession:
        """Update an existing question session.

        Args:
            session: The QuestionSession domain model with updated fields.

        Returns:
            Updated QuestionSession domain model.

        Raises:
            SessionNotFoundError: If session does not exist.
            SessionRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            data = self._session_to_db_dict(session)

            response = (
                await client.table(self.TABLE_NAME)
                .update(data)
                .eq("id", str(session.id))
                .execute()
            )

            if not response.data:
                raise SessionNotFoundError(f"Session with id={session.id} not found")

            updated_session = self._convert_db_row_to_session(response.data[0])
            logger.info(
                "Updated question session: id=%s, ai_score=%s",
                updated_session.id,
                updated_session.ai_score,
            )
            return updated_session

        except (SessionNotFoundError, SessionRepositoryError):
            raise
        except Exception as e:
            error_msg = f"Failed to update session with id={session.id}: {e}"
            logger.exception(error_msg)
            raise SessionRepositoryError(error_msg) from e

    async def get_average_score(
        self, user_id: UUID, last_n: int = 5
    ) -> float | None:
        """Get average AI score for last N sessions.

        Only considers sessions that have been evaluated (ai_score is not null).

        Args:
            user_id: The user's internal UUID.
            last_n: Number of recent sessions to consider.

        Returns:
            Average score as float, or None if no evaluated sessions.

        Raises:
            SessionRepositoryError: If database operation fails.
        """
        try:
            sessions = await self.get_last_n_by_user(user_id, last_n)
            scores = [s.ai_score for s in sessions if s.ai_score is not None]

            if not scores:
                return None

            average = sum(scores) / len(scores)
            logger.debug(
                "Average score for user %s (last %d with scores): %.2f",
                user_id,
                len(scores),
                average,
            )
            return average

        except SessionRepositoryError:
            raise
        except Exception as e:
            error_msg = f"Failed to get average score for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise SessionRepositoryError(error_msg) from e
