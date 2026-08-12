"""User repository for database operations."""

import logging
from uuid import UUID

from bot.domain.entities.user import User
from bot.infrastructure.database.connection import get_supabase_client

logger = logging.getLogger(__name__)


class UserRepositoryError(Exception):
    """Base exception for user repository errors."""


class UserNotFoundError(UserRepositoryError):
    """Raised when user is not found."""


class UserRepository:
    """Repository for User entity database operations.

    Handles CRUD operations for users table in Supabase.
    Returns domain models instead of raw dictionaries.
    """

    TABLE_NAME = "users"

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by Telegram ID.

        Args:
            telegram_id: The Telegram user ID.

        Returns:
            User domain model if found, None otherwise.

        Raises:
            UserRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("telegram_id", telegram_id)
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("User with telegram_id=%d not found", telegram_id)
                return None

            logger.debug("Found user with telegram_id=%d", telegram_id)
            row = response.data[0] if isinstance(response.data, list) else response.data
            return User.model_validate(row)

        except Exception as e:
            error_msg = f"Failed to get user by telegram_id={telegram_id}: {e}"
            logger.exception(error_msg)
            raise UserRepositoryError(error_msg) from e

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get user by internal ID.

        Args:
            user_id: The internal user UUID.

        Returns:
            User domain model if found, None otherwise.

        Raises:
            UserRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()
            response = (
                await client.table(self.TABLE_NAME)
                .select("*")
                .eq("id", str(user_id))
                .limit(1)
                .execute()
            )

            if not response.data:
                logger.debug("User with id=%s not found", user_id)
                return None

            logger.debug("Found user with id=%s", user_id)
            row = response.data[0] if isinstance(response.data, list) else response.data
            return User.model_validate(row)

        except Exception as e:
            error_msg = f"Failed to get user by id={user_id}: {e}"
            logger.exception(error_msg)
            raise UserRepositoryError(error_msg) from e

    async def create(self, user: User) -> User:
        """Create a new user in the database.

        Args:
            user: The User domain model to create.

        Returns:
            Created User domain model with database-assigned fields.

        Raises:
            UserRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            # Prepare data for insertion
            data = {
                "telegram_id": user.telegram_id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
                "timezone": user.timezone,
            }

            response = (
                await client.table(self.TABLE_NAME).insert(data).execute()
            )

            if not response.data:
                raise UserRepositoryError("No data returned after insert")

            created_user = User.model_validate(response.data[0])
            logger.info(
                "Created user: telegram_id=%d, id=%s",
                created_user.telegram_id,
                created_user.id,
            )
            return created_user

        except UserRepositoryError:
            raise
        except Exception as e:
            error_msg = f"Failed to create user with telegram_id={user.telegram_id}: {e}"
            logger.exception(error_msg)
            raise UserRepositoryError(error_msg) from e

    async def update(self, user: User) -> User:
        """Update an existing user in the database.

        Args:
            user: The User domain model with updated fields.

        Returns:
            Updated User domain model.

        Raises:
            UserNotFoundError: If user does not exist.
            UserRepositoryError: If database operation fails.
        """
        try:
            client = get_supabase_client()

            # Prepare data for update (exclude id and created_at)
            data = {
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "language_code": user.language_code,
                "timezone": user.timezone,
            }

            response = (
                await client.table(self.TABLE_NAME)
                .update(data)
                .eq("id", str(user.id))
                .execute()
            )

            if not response.data:
                raise UserNotFoundError(f"User with id={user.id} not found")

            updated_user = User.model_validate(response.data[0])
            logger.info(
                "Updated user: telegram_id=%d, id=%s",
                updated_user.telegram_id,
                updated_user.id,
            )
            return updated_user

        except (UserNotFoundError, UserRepositoryError):
            raise
        except Exception as e:
            error_msg = f"Failed to update user with id={user.id}: {e}"
            logger.exception(error_msg)
            raise UserRepositoryError(error_msg) from e

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str = "ru",
    ) -> tuple[User, bool]:
        """Get existing user or create a new one.

        Args:
            telegram_id: The Telegram user ID.
            username: Telegram username (optional).
            first_name: User's first name (optional).
            last_name: User's last name (optional).
            language_code: User's language code.

        Returns:
            Tuple of (User, created) where created is True if new user was created.

        Raises:
            UserRepositoryError: If database operation fails.
        """
        existing_user = await self.get_by_telegram_id(telegram_id)

        if existing_user is not None:
            return existing_user, False

        new_user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        created_user = await self.create(new_user)
        return created_user, True
