"""Profile repository for database operations."""

import logging
from uuid import UUID

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.infrastructure.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class ProfileRepositoryError(Exception):
    """Base exception for profile repository errors."""


class ProfileNotFoundError(ProfileRepositoryError):
    """Raised when profile is not found."""


class ProfileRepository:
    """Repository for UserProfile entity database operations.

    Handles CRUD operations for user_profiles table in Supabase.
    Returns domain models instead of raw dictionaries.
    """

    TABLE_NAME = "user_profiles"

    def _to_domain_model(self, data: dict) -> UserProfile:
        """Convert database row to domain model.

        Args:
            data: Raw database row as dictionary.

        Returns:
            UserProfile domain model.
        """
        # Convert focus_areas from strings to Category enums
        focus_areas = []
        for area in data.get("focus_areas", []) or []:
            try:
                focus_areas.append(Category(area))
            except ValueError:
                logger.warning("Unknown focus area: %s, skipping", area)

        return UserProfile(
            id=UUID(data["id"]) if isinstance(data["id"], str) else data["id"],
            user_id=UUID(data["user_id"]) if isinstance(data["user_id"], str) else data["user_id"],
            specialty=Specialty(data["specialty"]),
            grade=Grade(data["grade"]),
            tech_stack=data.get("tech_stack", []) or [],
            focus_areas=focus_areas,
            current_difficulty=data.get("current_difficulty", 3),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def _to_db_dict(self, profile: UserProfile, *, include_id: bool = False) -> dict:
        """Convert domain model to database dictionary.

        Args:
            profile: UserProfile domain model.
            include_id: Whether to include the id field.

        Returns:
            Dictionary suitable for database operations.
        """
        data = {
            "user_id": str(profile.user_id),
            "specialty": profile.specialty.value,
            "grade": profile.grade.value,
            "tech_stack": profile.tech_stack,
            "focus_areas": [area.value for area in profile.focus_areas],
            "current_difficulty": profile.current_difficulty,
        }
        if include_id:
            data["id"] = str(profile.id)
        return data

    async def get_by_user_id(self, user_id: UUID) -> UserProfile | None:
        """Get profile by user ID.

        Args:
            user_id: The internal user UUID.

        Returns:
            UserProfile domain model if found, None otherwise.

        Raises:
            ProfileRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("user_id", str(user_id))
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("Profile for user_id=%s not found", user_id)
                return None

            logger.debug("Found profile for user_id=%s", user_id)
            row = response.data[0] if isinstance(response.data, list) else response.data
            return self._to_domain_model(row)

        except Exception as e:
            error_msg = f"Failed to get profile by user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise ProfileRepositoryError(error_msg) from e

    async def get_by_id(self, profile_id: UUID) -> UserProfile | None:
        """Get profile by internal ID.

        Args:
            profile_id: The internal profile UUID.

        Returns:
            UserProfile domain model if found, None otherwise.

        Raises:
            ProfileRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("id", str(profile_id))
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("Profile with id=%s not found", profile_id)
                return None

            logger.debug("Found profile with id=%s", profile_id)
            row = response.data[0] if isinstance(response.data, list) else response.data
            return self._to_domain_model(row)

        except Exception as e:
            error_msg = f"Failed to get profile by id={profile_id}: {e}"
            logger.exception(error_msg)
            raise ProfileRepositoryError(error_msg) from e

    async def create(self, profile: UserProfile) -> UserProfile:
        """Create a new profile in the database.

        Args:
            profile: The UserProfile domain model to create.

        Returns:
            Created UserProfile domain model with database-assigned fields.

        Raises:
            ProfileRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            data = self._to_db_dict(profile)

            response = (
                await client.table(self.TABLE_NAME).insert(data).execute()
            )

            if not response.data:
                raise ProfileRepositoryError("No data returned after insert")

            created_profile = self._to_domain_model(response.data[0])
            logger.info(
                "Created profile: user_id=%s, id=%s",
                created_profile.user_id,
                created_profile.id,
            )
            return created_profile

        except ProfileRepositoryError:
            raise
        except Exception as e:
            error_msg = f"Failed to create profile for user_id={profile.user_id}: {e}"
            logger.exception(error_msg)
            raise ProfileRepositoryError(error_msg) from e

    async def update(self, profile: UserProfile) -> UserProfile:
        """Update an existing profile in the database.

        Args:
            profile: The UserProfile domain model with updated fields.

        Returns:
            Updated UserProfile domain model.

        Raises:
            ProfileNotFoundError: If profile does not exist.
            ProfileRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            data = self._to_db_dict(profile)

            response = (
                await client.table(self.TABLE_NAME)
                .update(data)
                .eq("id", str(profile.id))
                .execute()
            )

            if not response.data:
                raise ProfileNotFoundError(f"Profile with id={profile.id} not found")

            updated_profile = self._to_domain_model(response.data[0])
            logger.info(
                "Updated profile: user_id=%s, id=%s",
                updated_profile.user_id,
                updated_profile.id,
            )
            return updated_profile

        except (ProfileNotFoundError, ProfileRepositoryError):
            raise
        except Exception as e:
            error_msg = f"Failed to update profile with id={profile.id}: {e}"
            logger.exception(error_msg)
            raise ProfileRepositoryError(error_msg) from e

    async def update_difficulty(self, user_id: UUID, new_difficulty: int) -> UserProfile:
        """Update difficulty level for a user's profile.

        Args:
            user_id: The user's internal UUID.
            new_difficulty: The new difficulty level (1-10).

        Returns:
            Updated UserProfile domain model.

        Raises:
            ProfileNotFoundError: If profile does not exist.
            ProfileRepositoryError: If database operation fails.
            ValueError: If difficulty is out of range.
        """
        if not 1 <= new_difficulty <= 10:
            raise ValueError(f"Difficulty must be between 1 and 10, got {new_difficulty}")

        try:
            client = get_supabase_client()

            response = (
                await client.table(self.TABLE_NAME)
                .update({"current_difficulty": new_difficulty})
                .eq("user_id", str(user_id))
                .execute()
            )

            if not response.data:
                raise ProfileNotFoundError(f"Profile for user_id={user_id} not found")

            updated_profile = self._to_domain_model(response.data[0])
            logger.info(
                "Updated difficulty for user_id=%s to %d",
                user_id,
                new_difficulty,
            )
            return updated_profile

        except (ProfileNotFoundError, ProfileRepositoryError, ValueError):
            raise
        except Exception as e:
            error_msg = f"Failed to update difficulty for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise ProfileRepositoryError(error_msg) from e

    async def delete_by_user_id(self, user_id: UUID) -> bool:
        """Delete profile by user ID.

        Args:
            user_id: The user's internal UUID.

        Returns:
            True if profile was deleted, False if not found.

        Raises:
            ProfileRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            response = (
                await client.table(self.TABLE_NAME)
                .delete()
                .eq("user_id", str(user_id))
                .execute()
            )

            deleted = bool(response.data)
            if deleted:
                logger.info("Deleted profile for user_id=%s", user_id)
            else:
                logger.debug("No profile found to delete for user_id=%s", user_id)

            return deleted

        except Exception as e:
            error_msg = f"Failed to delete profile for user_id={user_id}: {e}"
            logger.exception(error_msg)
            raise ProfileRepositoryError(error_msg) from e
