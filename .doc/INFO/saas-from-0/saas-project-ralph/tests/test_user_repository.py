"""Tests for user repository module."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.user import User
from bot.repositories.user_repository import (
    UserNotFoundError,
    UserRepository,
    UserRepositoryError,
)


@pytest.fixture
def user_repo():
    """Create a UserRepository instance."""
    return UserRepository()


@pytest.fixture
def sample_user_data():
    """Sample user data as it would come from database."""
    return {
        "id": str(uuid4()),
        "telegram_id": 123456789,
        "username": "testuser",
        "first_name": "Test",
        "last_name": "User",
        "language_code": "en",
        "timezone": "Europe/Moscow",
        "created_at": "2026-01-27T10:00:00+00:00",
        "updated_at": "2026-01-27T10:00:00+00:00",
    }


@pytest.fixture
def sample_user():
    """Create a sample User domain model."""
    return User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        language_code="en",
    )


class TestUserRepositoryGetByTelegramId:
    """Tests for get_by_telegram_id method."""

    async def test_get_by_telegram_id_found(
        self, user_repo: UserRepository, sample_user_data: dict
    ):
        """Test getting existing user by telegram_id."""
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await user_repo.get_by_telegram_id(123456789)

        assert result is not None
        assert isinstance(result, User)
        assert result.telegram_id == 123456789
        assert result.username == "testuser"

    async def test_get_by_telegram_id_not_found(self, user_repo: UserRepository):
        """Test getting non-existent user returns None."""
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
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await user_repo.get_by_telegram_id(999999999)

        assert result is None

    async def test_get_by_telegram_id_error(self, user_repo: UserRepository):
        """Test that database errors raise UserRepositoryError."""
        with (
            patch(
                "bot.repositories.user_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(UserRepositoryError) as exc_info,
        ):
            await user_repo.get_by_telegram_id(123)

        assert "Failed to get user" in str(exc_info.value)


class TestUserRepositoryGetById:
    """Tests for get_by_id method."""

    async def test_get_by_id_found(
        self, user_repo: UserRepository, sample_user_data: dict
    ):
        """Test getting existing user by id."""
        user_id = sample_user_data["id"]
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            result = await user_repo.get_by_id(UUID(user_id))

        assert result is not None
        assert isinstance(result, User)

    async def test_get_by_id_not_found(self, user_repo: UserRepository):
        """Test getting non-existent user by id returns None."""
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
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await user_repo.get_by_id(uuid4())

        assert result is None


class TestUserRepositoryCreate:
    """Tests for create method."""

    async def test_create_user_success(
        self, user_repo: UserRepository, sample_user: User, sample_user_data: dict
    ):
        """Test creating a new user."""
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await user_repo.create(sample_user)

        assert result is not None
        assert isinstance(result, User)
        assert result.telegram_id == sample_user_data["telegram_id"]

    async def test_create_user_no_data_returned(
        self, user_repo: UserRepository, sample_user: User
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
                "bot.repositories.user_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(UserRepositoryError) as exc_info,
        ):
            await user_repo.create(sample_user)

        assert "No data returned" in str(exc_info.value)


class TestUserRepositoryUpdate:
    """Tests for update method."""

    async def test_update_user_success(
        self, user_repo: UserRepository, sample_user_data: dict
    ):
        """Test updating an existing user."""
        user = User.model_validate(sample_user_data)
        user.first_name = "Updated"

        updated_data = sample_user_data.copy()
        updated_data["first_name"] = "Updated"

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
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await user_repo.update(user)

        assert result is not None
        assert result.first_name == "Updated"

    async def test_update_user_not_found(
        self, user_repo: UserRepository, sample_user: User
    ):
        """Test that updating non-existent user raises UserNotFoundError."""
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
                "bot.repositories.user_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(UserNotFoundError) as exc_info,
        ):
            await user_repo.update(sample_user)

        assert "not found" in str(exc_info.value)


class TestUserRepositoryGetOrCreate:
    """Tests for get_or_create method."""

    async def test_get_or_create_existing_user(
        self, user_repo: UserRepository, sample_user_data: dict
    ):
        """Test get_or_create returns existing user."""
        mock_response = MagicMock()
        mock_response.data = [sample_user_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            user, created = await user_repo.get_or_create(123456789)

        assert user is not None
        assert created is False
        assert user.telegram_id == 123456789

    async def test_get_or_create_new_user(
        self, user_repo: UserRepository, sample_user_data: dict
    ):
        """Test get_or_create creates new user when not found."""
        # First call returns empty list (user not found)
        mock_response_none = MagicMock()
        mock_response_none.data = []

        # Second call returns created user
        mock_response_created = MagicMock()
        mock_response_created.data = [sample_user_data]

        mock_query_none = AsyncMock()
        mock_query_none.execute = AsyncMock(return_value=mock_response_none)

        mock_query_created = AsyncMock()
        mock_query_created.execute = AsyncMock(return_value=mock_response_created)

        mock_limit = MagicMock(return_value=mock_query_none)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_insert = MagicMock(return_value=mock_query_created)

        mock_table = MagicMock(
            return_value=MagicMock(select=mock_select, insert=mock_insert)
        )

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.user_repository.get_supabase_client",
            return_value=mock_client,
        ):
            user, created = await user_repo.get_or_create(
                telegram_id=123456789,
                username="testuser",
                first_name="Test",
            )

        assert user is not None
        assert created is True


class TestUserRepositoryErrors:
    """Tests for error handling."""

    def test_user_repository_error_is_exception(self):
        """Test UserRepositoryError inherits from Exception."""
        error = UserRepositoryError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_user_not_found_error_is_repository_error(self):
        """Test UserNotFoundError inherits from UserRepositoryError."""
        error = UserNotFoundError("user not found")
        assert isinstance(error, UserRepositoryError)
        assert isinstance(error, Exception)
