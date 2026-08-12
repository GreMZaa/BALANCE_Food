"""Supabase database connection management."""

import logging
from typing import TYPE_CHECKING

from supabase import AsyncClient, create_async_client

from bot.core.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_supabase_client: AsyncClient | None = None


class DatabaseConnectionError(Exception):
    """Raised when database connection fails."""


async def init_supabase_client() -> AsyncClient:
    """Initialize the Supabase async client.

    Returns:
        AsyncClient: Initialized Supabase client.

    Raises:
        DatabaseConnectionError: If connection fails.
    """
    global _supabase_client

    if _supabase_client is not None:
        return _supabase_client

    try:
        url = settings.supabase_url
        key = settings.supabase_key.get_secret_value()

        logger.info("Initializing Supabase client for URL: %s", url)
        _supabase_client = await create_async_client(url, key)
        logger.info("Supabase client initialized successfully")

        return _supabase_client

    except Exception as e:
        error_msg = f"Failed to initialize Supabase client: {e}"
        logger.exception(error_msg)
        raise DatabaseConnectionError(error_msg) from e


def get_supabase_client() -> AsyncClient:
    """Get the initialized Supabase client.

    Returns:
        AsyncClient: The Supabase client instance.

    Raises:
        DatabaseConnectionError: If client is not initialized.
    """
    if _supabase_client is None:
        raise DatabaseConnectionError(
            "Supabase client is not initialized. Call init_supabase_client() first."
        )
    return _supabase_client


async def close_supabase_client() -> None:
    """Close the Supabase client connection."""
    global _supabase_client

    if _supabase_client is not None:
        try:
            await _supabase_client.auth.sign_out()
            logger.info("Supabase client closed successfully")
        except Exception as e:
            logger.warning("Error while closing Supabase client: %s", e)
        finally:
            _supabase_client = None


async def check_connection() -> bool:
    """Check if the database connection is working.

    Returns:
        bool: True if connection is healthy, False otherwise.
    """
    try:
        client = get_supabase_client()
        # Simple query to verify connection
        await client.table("_health_check_nonexistent").select("*").limit(1).execute()
        return True
    except DatabaseConnectionError:
        return False
    except Exception as e:
        # Table doesn't exist is OK - it means connection works
        error_str = str(e).lower()
        if "does not exist" in error_str or "not found" in error_str:
            return True
        logger.warning("Database connection check failed: %s", e)
        return False
