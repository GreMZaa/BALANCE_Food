"""Tests for profile repository module."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.repositories.profile_repository import (
    ProfileNotFoundError,
    ProfileRepository,
    ProfileRepositoryError,
)


@pytest.fixture
def profile_repo():
    """Create a ProfileRepository instance."""
    return ProfileRepository()


@pytest.fixture
def sample_user_id():
    """Generate a sample user ID."""
    return uuid4()


@pytest.fixture
def sample_profile_data(sample_user_id):
    """Sample profile data as it would come from database."""
    return {
        "id": str(uuid4()),
        "user_id": str(sample_user_id),
        "specialty": "backend",
        "grade": "junior",
        "tech_stack": ["python", "postgresql"],
        "focus_areas": ["algorithms", "databases"],
        "current_difficulty": 3,
        "created_at": "2026-01-27T10:00:00+00:00",
        "updated_at": "2026-01-27T10:00:00+00:00",
    }


@pytest.fixture
def sample_profile(sample_user_id):
    """Create a sample UserProfile domain model."""
    return UserProfile(
        user_id=sample_user_id,
        specialty=Specialty.BACKEND,
        grade=Grade.JUNIOR,
        tech_stack=["python", "postgresql"],
        focus_areas=[Category.ALGORITHMS, Category.DATABASES],
        current_difficulty=3,
    )


class TestProfileRepositoryGetByUserId:
    """Tests for get_by_user_id method."""

    async def test_get_by_user_id_found(
        self, profile_repo: ProfileRepository, sample_profile_data: dict, sample_user_id
    ):
        """Test getting existing profile by user_id."""
        mock_response = MagicMock()
        mock_response.data = [sample_profile_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.get_by_user_id(sample_user_id)

        assert result is not None
        assert isinstance(result, UserProfile)
        assert result.user_id == sample_user_id
        assert result.specialty == Specialty.BACKEND
        assert result.grade == Grade.JUNIOR
        assert result.tech_stack == ["python", "postgresql"]
        assert result.focus_areas == [Category.ALGORITHMS, Category.DATABASES]

    async def test_get_by_user_id_not_found(
        self, profile_repo: ProfileRepository, sample_user_id
    ):
        """Test getting non-existent profile returns None."""
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
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.get_by_user_id(sample_user_id)

        assert result is None

    async def test_get_by_user_id_error(
        self, profile_repo: ProfileRepository, sample_user_id
    ):
        """Test that database errors raise ProfileRepositoryError."""
        with (
            patch(
                "bot.repositories.profile_repository.get_supabase_client",
                side_effect=Exception("Database error"),
            ),
            pytest.raises(ProfileRepositoryError) as exc_info,
        ):
            await profile_repo.get_by_user_id(sample_user_id)

        assert "Failed to get profile" in str(exc_info.value)


class TestProfileRepositoryGetById:
    """Tests for get_by_id method."""

    async def test_get_by_id_found(
        self, profile_repo: ProfileRepository, sample_profile_data: dict
    ):
        """Test getting existing profile by id."""
        profile_id = sample_profile_data["id"]
        mock_response = MagicMock()
        mock_response.data = [sample_profile_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_limit = MagicMock(return_value=mock_query)
        mock_eq = MagicMock(return_value=MagicMock(limit=mock_limit))
        mock_select = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(select=mock_select))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            from uuid import UUID

            result = await profile_repo.get_by_id(UUID(profile_id))

        assert result is not None
        assert isinstance(result, UserProfile)

    async def test_get_by_id_not_found(self, profile_repo: ProfileRepository):
        """Test getting non-existent profile by id returns None."""
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
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.get_by_id(uuid4())

        assert result is None


class TestProfileRepositoryCreate:
    """Tests for create method."""

    async def test_create_profile_success(
        self,
        profile_repo: ProfileRepository,
        sample_profile: UserProfile,
        sample_profile_data: dict,
    ):
        """Test creating a new profile."""
        mock_response = MagicMock()
        mock_response.data = [sample_profile_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_insert = MagicMock(return_value=mock_query)
        mock_table = MagicMock(return_value=MagicMock(insert=mock_insert))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.create(sample_profile)

        assert result is not None
        assert isinstance(result, UserProfile)
        assert result.specialty == Specialty.BACKEND
        assert result.tech_stack == ["python", "postgresql"]

    async def test_create_profile_no_data_returned(
        self, profile_repo: ProfileRepository, sample_profile: UserProfile
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
                "bot.repositories.profile_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProfileRepositoryError) as exc_info,
        ):
            await profile_repo.create(sample_profile)

        assert "No data returned" in str(exc_info.value)


class TestProfileRepositoryUpdate:
    """Tests for update method."""

    async def test_update_profile_success(
        self, profile_repo: ProfileRepository, sample_profile_data: dict, sample_user_id
    ):
        """Test updating an existing profile."""
        profile = UserProfile(
            id=sample_profile_data["id"],
            user_id=sample_user_id,
            specialty=Specialty.BACKEND,
            grade=Grade.MIDDLE,  # Changed from JUNIOR
            tech_stack=["python", "postgresql", "go"],  # Added go
            focus_areas=[Category.ALGORITHMS],
            current_difficulty=5,  # Changed from 3
        )

        updated_data = sample_profile_data.copy()
        updated_data["grade"] = "middle"
        updated_data["tech_stack"] = ["python", "postgresql", "go"]
        updated_data["current_difficulty"] = 5

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
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.update(profile)

        assert result is not None
        assert result.grade == Grade.MIDDLE
        assert "go" in result.tech_stack

    async def test_update_profile_not_found(
        self, profile_repo: ProfileRepository, sample_profile: UserProfile
    ):
        """Test that updating non-existent profile raises ProfileNotFoundError."""
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
                "bot.repositories.profile_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProfileNotFoundError) as exc_info,
        ):
            await profile_repo.update(sample_profile)

        assert "not found" in str(exc_info.value)


class TestProfileRepositoryUpdateDifficulty:
    """Tests for update_difficulty method."""

    async def test_update_difficulty_success(
        self, profile_repo: ProfileRepository, sample_profile_data: dict, sample_user_id
    ):
        """Test updating difficulty level."""
        updated_data = sample_profile_data.copy()
        updated_data["current_difficulty"] = 5

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
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.update_difficulty(sample_user_id, 5)

        assert result is not None
        assert result.current_difficulty == 5

    async def test_update_difficulty_not_found(
        self, profile_repo: ProfileRepository, sample_user_id
    ):
        """Test that updating difficulty for non-existent profile raises error."""
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
                "bot.repositories.profile_repository.get_supabase_client",
                return_value=mock_client,
            ),
            pytest.raises(ProfileNotFoundError),
        ):
            await profile_repo.update_difficulty(sample_user_id, 5)

    async def test_update_difficulty_invalid_value_low(
        self, profile_repo: ProfileRepository, sample_user_id
    ):
        """Test that difficulty below 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await profile_repo.update_difficulty(sample_user_id, 0)

        assert "Difficulty must be between 1 and 10" in str(exc_info.value)

    async def test_update_difficulty_invalid_value_high(
        self, profile_repo: ProfileRepository, sample_user_id
    ):
        """Test that difficulty above 10 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            await profile_repo.update_difficulty(sample_user_id, 11)

        assert "Difficulty must be between 1 and 10" in str(exc_info.value)


class TestProfileRepositoryDeleteByUserId:
    """Tests for delete_by_user_id method."""

    async def test_delete_by_user_id_success(
        self, profile_repo: ProfileRepository, sample_profile_data: dict, sample_user_id
    ):
        """Test deleting profile by user_id."""
        mock_response = MagicMock()
        mock_response.data = [sample_profile_data]

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_eq = MagicMock(return_value=mock_query)
        mock_delete = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(delete=mock_delete))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.delete_by_user_id(sample_user_id)

        assert result is True

    async def test_delete_by_user_id_not_found(
        self, profile_repo: ProfileRepository, sample_user_id
    ):
        """Test deleting non-existent profile returns False."""
        mock_response = MagicMock()
        mock_response.data = []

        mock_query = AsyncMock()
        mock_query.execute = AsyncMock(return_value=mock_response)

        mock_eq = MagicMock(return_value=mock_query)
        mock_delete = MagicMock(return_value=MagicMock(eq=mock_eq))
        mock_table = MagicMock(return_value=MagicMock(delete=mock_delete))

        mock_client = MagicMock()
        mock_client.table = mock_table

        with patch(
            "bot.repositories.profile_repository.get_supabase_client",
            return_value=mock_client,
        ):
            result = await profile_repo.delete_by_user_id(sample_user_id)

        assert result is False


class TestProfileRepositoryToDomainModel:
    """Tests for _to_domain_model helper method."""

    def test_to_domain_model_with_empty_arrays(self, profile_repo: ProfileRepository):
        """Test conversion with empty tech_stack and focus_areas."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "specialty": "backend",
            "grade": "junior",
            "tech_stack": [],
            "focus_areas": [],
            "current_difficulty": 3,
            "created_at": "2026-01-27T10:00:00+00:00",
            "updated_at": "2026-01-27T10:00:00+00:00",
        }

        result = profile_repo._to_domain_model(data)

        assert result.tech_stack == []
        assert result.focus_areas == []

    def test_to_domain_model_with_null_arrays(self, profile_repo: ProfileRepository):
        """Test conversion with null tech_stack and focus_areas."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "specialty": "backend",
            "grade": "junior",
            "tech_stack": None,
            "focus_areas": None,
            "current_difficulty": 3,
            "created_at": "2026-01-27T10:00:00+00:00",
            "updated_at": "2026-01-27T10:00:00+00:00",
        }

        result = profile_repo._to_domain_model(data)

        assert result.tech_stack == []
        assert result.focus_areas == []

    def test_to_domain_model_with_unknown_focus_area(
        self, profile_repo: ProfileRepository
    ):
        """Test conversion skips unknown focus areas."""
        data = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "specialty": "backend",
            "grade": "junior",
            "tech_stack": ["python"],
            "focus_areas": ["algorithms", "unknown_area", "databases"],
            "current_difficulty": 3,
            "created_at": "2026-01-27T10:00:00+00:00",
            "updated_at": "2026-01-27T10:00:00+00:00",
        }

        result = profile_repo._to_domain_model(data)

        assert len(result.focus_areas) == 2
        assert Category.ALGORITHMS in result.focus_areas
        assert Category.DATABASES in result.focus_areas


class TestProfileRepositoryErrors:
    """Tests for error handling."""

    def test_profile_repository_error_is_exception(self):
        """Test ProfileRepositoryError inherits from Exception."""
        error = ProfileRepositoryError("test error")
        assert isinstance(error, Exception)
        assert str(error) == "test error"

    def test_profile_not_found_error_is_repository_error(self):
        """Test ProfileNotFoundError inherits from ProfileRepositoryError."""
        error = ProfileNotFoundError("profile not found")
        assert isinstance(error, ProfileRepositoryError)
        assert isinstance(error, Exception)
