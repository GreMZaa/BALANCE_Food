"""Tests for progress repository module."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.progress import Progress
from bot.repositories.progress_repository import (
    ProgressNotFoundError,
    ProgressRepository,
    ProgressRepositoryError,
)


@pytest.fixture
def progress_repo():
    """Create a ProgressRepository instance."""
    return ProgressRepository()


@pytest.fixture
def sample_progress_data():
    """Sample progress data as it would come from database."""
    return {
        "id": str(uuid4()),
        "user_id": str(uuid4()),
        "current_streak": 5,
        "longest_streak": 12,
        "total_questions_answered": 47,
        "questions_today": 3,
        "last_activity_date": "2026-01-30",
        "streak_updated_at": "2026-01-30T10:00:00+00:00",
        "created_at": "2026-01-20T08:00:00+00:00",
    }


@pytest.fixture
def sample_progress():
    """Create a sample Progress domain model."""
    return Progress(
        user_id=uuid4(),
        current_streak=5,
        longest_streak=12,
        total_questions_answered=47,
        questions_today=3,
        last_activity_date=date(2026, 1, 30),
    )


class TestProgressRepositoryConversion:
    """Tests for conversion methods."""

    def test_to_domain_model(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test converting database row to Progress model."""
        progress = progress_repo._to_domain_model(sample_progress_data)

        assert isinstance(progress, Progress)
        assert progress.current_streak == 5
        assert progress.longest_streak == 12
        assert progress.total_questions_answered == 47
        assert progress.questions_today == 3
        assert progress.last_activity_date == date(2026, 1, 30)

    def test_to_domain_model_with_null_last_activity(
        self, progress_repo: ProgressRepository
    ):
        """Test converting row with null last_activity_date."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "current_streak": 0,
            "longest_streak": 0,
            "total_questions_answered": 0,
            "questions_today": 0,
            "last_activity_date": None,
            "streak_updated_at": None,
            "created_at": "2026-01-20T08:00:00+00:00",
        }
        progress = progress_repo._to_domain_model(data)

        assert progress.last_activity_date is None
        assert progress.streak_updated_at is None
        assert progress.current_streak == 0

    def test_to_domain_model_with_defaults(self, progress_repo: ProgressRepository):
        """Test converting row with missing optional fields uses defaults."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "last_activity_date": None,
            "streak_updated_at": None,
            "created_at": "2026-01-30T10:00:00+00:00",
        }
        progress = progress_repo._to_domain_model(data)

        assert progress.current_streak == 0
        assert progress.longest_streak == 0
        assert progress.total_questions_answered == 0
        assert progress.questions_today == 0

    def test_to_db_dict(
        self, progress_repo: ProgressRepository, sample_progress: Progress
    ):
        """Test converting Progress model to database dict."""
        data = progress_repo._to_db_dict(sample_progress)

        assert data["user_id"] == str(sample_progress.user_id)
        assert data["current_streak"] == 5
        assert data["longest_streak"] == 12
        assert data["total_questions_answered"] == 47
        assert data["questions_today"] == 3
        assert data["last_activity_date"] == "2026-01-30"

    def test_to_db_dict_with_null_date(self, progress_repo: ProgressRepository):
        """Test converting Progress with null dates to dict."""
        progress = Progress(user_id=uuid4())
        data = progress_repo._to_db_dict(progress)

        assert data["last_activity_date"] is None
        assert data["streak_updated_at"] is None


class TestProgressRepositoryGetByUserId:
    """Tests for get_by_user_id method."""

    async def test_get_by_user_id_found(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test getting existing progress by user_id."""
        user_id = sample_progress_data["user_id"]
        mock_response = MagicMock()
        mock_response.data = [sample_progress_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            result = await progress_repo.get_by_user_id(UUID(user_id))

        assert result is not None
        assert isinstance(result, Progress)
        assert result.current_streak == 5

    async def test_get_by_user_id_not_found(
        self, progress_repo: ProgressRepository
    ):
        """Test getting non-existent progress returns None."""
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
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await progress_repo.get_by_user_id(uuid4())

        assert result is None

    async def test_get_by_user_id_error(self, progress_repo: ProgressRepository):
        """Test that database errors raise ProgressRepositoryError."""
        with (
            patch(
                "bot.repositories.progress_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(ProgressRepositoryError) as exc_info,
        ):
            await progress_repo.get_by_user_id(uuid4())

        assert "Failed to get progress" in str(exc_info.value)


class TestProgressRepositoryCreate:
    """Tests for create method."""

    async def test_create_progress_success(
        self,
        progress_repo: ProgressRepository,
        sample_progress: Progress,
        sample_progress_data: dict,
    ):
        """Test creating a new progress record."""
        mock_response = MagicMock()
        mock_response.data = [sample_progress_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await progress_repo.create(sample_progress)

        assert result is not None
        assert isinstance(result, Progress)
        assert result.current_streak == 5

    async def test_create_progress_no_data_returned(
        self, progress_repo: ProgressRepository, sample_progress: Progress
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
                "bot.repositories.progress_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProgressRepositoryError) as exc_info,
        ):
            await progress_repo.create(sample_progress)

        assert "No data returned" in str(exc_info.value)

    async def test_create_progress_error(
        self, progress_repo: ProgressRepository, sample_progress: Progress
    ):
        """Test that database errors raise ProgressRepositoryError."""
        with (
            patch(
                "bot.repositories.progress_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(ProgressRepositoryError) as exc_info,
        ):
            await progress_repo.create(sample_progress)

        assert "Failed to create progress" in str(exc_info.value)


class TestProgressRepositoryUpdate:
    """Tests for update method."""

    async def test_update_progress_success(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test updating an existing progress record."""
        progress = progress_repo._to_domain_model(sample_progress_data)
        progress.questions_today = 4
        progress.total_questions_answered = 48

        updated_data = sample_progress_data.copy()
        updated_data["questions_today"] = 4
        updated_data["total_questions_answered"] = 48

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
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await progress_repo.update(progress)

        assert result is not None
        assert result.questions_today == 4
        assert result.total_questions_answered == 48

    async def test_update_progress_not_found(
        self, progress_repo: ProgressRepository, sample_progress: Progress
    ):
        """Test that updating non-existent progress raises ProgressNotFoundError."""
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
                "bot.repositories.progress_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProgressNotFoundError) as exc_info,
        ):
            await progress_repo.update(sample_progress)

        assert "not found" in str(exc_info.value)

    async def test_update_progress_error(
        self, progress_repo: ProgressRepository, sample_progress: Progress
    ):
        """Test that database errors raise ProgressRepositoryError."""
        with (
            patch(
                "bot.repositories.progress_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(ProgressRepositoryError) as exc_info,
        ):
            await progress_repo.update(sample_progress)

        assert "Failed to update progress" in str(exc_info.value)


class TestProgressRepositoryUpdateStreak:
    """Tests for update_streak method."""

    async def test_update_streak_success(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test updating streak values."""
        updated_data = sample_progress_data.copy()
        updated_data["current_streak"] = 6
        updated_data["longest_streak"] = 12

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
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            user_id = UUID(sample_progress_data["user_id"])
            result = await progress_repo.update_streak(user_id, 6, 12)

        assert result is not None
        assert result.current_streak == 6
        assert result.longest_streak == 12

    async def test_update_streak_not_found(
        self, progress_repo: ProgressRepository
    ):
        """Test that updating streak for non-existent progress raises error."""
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
                "bot.repositories.progress_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProgressNotFoundError) as exc_info,
        ):
            await progress_repo.update_streak(uuid4(), 1, 1)

        assert "not found" in str(exc_info.value)

    async def test_update_streak_error(self, progress_repo: ProgressRepository):
        """Test that database errors raise ProgressRepositoryError."""
        with (
            patch(
                "bot.repositories.progress_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(ProgressRepositoryError) as exc_info,
        ):
            await progress_repo.update_streak(uuid4(), 1, 1)

        assert "Failed to update streak" in str(exc_info.value)


class TestProgressRepositoryIncrementQuestionsToday:
    """Tests for increment_questions_today method."""

    async def test_increment_same_day(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test incrementing questions_today on the same day."""
        current_date = date(2026, 1, 30)

        # Mock get_by_user_id to return existing progress
        get_response = MagicMock()
        get_response.data = [sample_progress_data]

        get_query = AsyncMock()
        get_query.execute = AsyncMock(return_value=get_response)

        get_limit = MagicMock(return_value=get_query)
        get_eq = MagicMock(return_value=MagicMock(limit=get_limit))
        get_select = MagicMock(return_value=MagicMock(eq=get_eq))

        # Mock update to return updated data
        updated_data = sample_progress_data.copy()
        updated_data["questions_today"] = 4
        updated_data["total_questions_answered"] = 48

        update_response = MagicMock()
        update_response.data = [updated_data]

        update_query = AsyncMock()
        update_query.execute = AsyncMock(return_value=update_response)

        update_eq = MagicMock(return_value=update_query)
        update_fn = MagicMock(return_value=MagicMock(eq=update_eq))

        # Build mock table that supports both select and update
        mock_table_instance = MagicMock()
        mock_table_instance.select = get_select
        mock_table_instance.update = update_fn
        mock_table = MagicMock(return_value=mock_table_instance)

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            user_id = UUID(sample_progress_data["user_id"])
            result = await progress_repo.increment_questions_today(
                user_id, current_date
            )

        assert result is not None
        assert result.questions_today == 4
        assert result.total_questions_answered == 48

    async def test_increment_new_day_resets(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test that questions_today resets to 1 on a new day."""
        # Current date is different from last_activity_date
        current_date = date(2026, 1, 31)

        get_response = MagicMock()
        get_response.data = [sample_progress_data]

        get_query = AsyncMock()
        get_query.execute = AsyncMock(return_value=get_response)

        get_limit = MagicMock(return_value=get_query)
        get_eq = MagicMock(return_value=MagicMock(limit=get_limit))
        get_select = MagicMock(return_value=MagicMock(eq=get_eq))

        # After reset, questions_today should be 1
        updated_data = sample_progress_data.copy()
        updated_data["questions_today"] = 1
        updated_data["total_questions_answered"] = 48
        updated_data["last_activity_date"] = "2026-01-31"

        update_response = MagicMock()
        update_response.data = [updated_data]

        update_query = AsyncMock()
        update_query.execute = AsyncMock(return_value=update_response)

        update_eq = MagicMock(return_value=update_query)
        update_fn = MagicMock(return_value=MagicMock(eq=update_eq))

        mock_table_instance = MagicMock()
        mock_table_instance.select = get_select
        mock_table_instance.update = update_fn
        mock_table = MagicMock(return_value=mock_table_instance)

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            user_id = UUID(sample_progress_data["user_id"])
            result = await progress_repo.increment_questions_today(
                user_id, current_date
            )

        assert result is not None
        assert result.questions_today == 1
        assert result.total_questions_answered == 48

    async def test_increment_not_found(self, progress_repo: ProgressRepository):
        """Test that incrementing for non-existent progress raises error."""
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

        with (
            patch(
                "bot.repositories.progress_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProgressNotFoundError) as exc_info,
        ):
            await progress_repo.increment_questions_today(uuid4())

        assert "not found" in str(exc_info.value)


class TestProgressRepositoryGetOrCreate:
    """Tests for get_or_create method."""

    async def test_get_or_create_existing(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test get_or_create returns existing progress."""
        mock_response = MagicMock()
        mock_response.data = [sample_progress_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            user_id = UUID(sample_progress_data["user_id"])
            progress, created = await progress_repo.get_or_create(user_id)

        assert progress is not None
        assert created is False
        assert progress.current_streak == 5

    async def test_get_or_create_new(
        self, progress_repo: ProgressRepository, sample_progress_data: dict
    ):
        """Test get_or_create creates new progress when not found."""
        # First call (get_by_user_id) returns empty
        get_response = MagicMock()
        get_response.data = []

        get_query = AsyncMock()
        get_query.execute = AsyncMock(return_value=get_response)

        get_limit = MagicMock(return_value=get_query)
        get_eq = MagicMock(return_value=MagicMock(limit=get_limit))
        get_select = MagicMock(return_value=MagicMock(eq=get_eq))

        # Second call (create) returns new data
        new_data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "current_streak": 0,
            "longest_streak": 0,
            "total_questions_answered": 0,
            "questions_today": 0,
            "last_activity_date": None,
            "streak_updated_at": None,
            "created_at": "2026-01-30T10:00:00+00:00",
        }

        create_response = MagicMock()
        create_response.data = [new_data]

        create_query = AsyncMock()
        create_query.execute = AsyncMock(return_value=create_response)

        create_insert = MagicMock(return_value=create_query)

        mock_table_instance = MagicMock()
        mock_table_instance.select = get_select
        mock_table_instance.insert = create_insert
        mock_table = MagicMock(return_value=mock_table_instance)

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.progress_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            user_id = UUID(new_data["user_id"])
            progress, created = await progress_repo.get_or_create(user_id)

        assert progress is not None
        assert created is True
        assert progress.current_streak == 0


class TestProgressRepositoryErrors:
    """Tests for error classes."""

    def test_progress_repository_error_is_exception(self):
        """Test ProgressRepositoryError inherits from Exception."""
        error = ProgressRepositoryError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_progress_not_found_error_is_repository_error(self):
        """Test ProgressNotFoundError inherits from ProgressRepositoryError."""
        error = ProgressNotFoundError("progress not found")
        assert isinstance(error, ProgressRepositoryError)
        assert isinstance(error, Exception)


class TestProgressRepositoryImports:
    """Tests for module imports."""

    def test_import_from_init(self):
        """Test that classes can be imported from repositories package."""
        from bot.repositories import (
            ProgressNotFoundError,
            ProgressRepository,
            ProgressRepositoryError,
        )

        assert ProgressRepository is not None
        assert ProgressRepositoryError is not None
        assert ProgressNotFoundError is not None
