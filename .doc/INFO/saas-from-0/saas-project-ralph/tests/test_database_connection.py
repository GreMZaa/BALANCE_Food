"""Tests for database connection module."""

import pytest

from bot.infrastructure.database.connection import (
    DatabaseConnectionError,
    close_supabase_client,
    get_supabase_client,
    init_supabase_client,
)


@pytest.fixture(autouse=True)
async def reset_client():
    """Reset the global client before each test."""
    import bot.infrastructure.database.connection as conn_module

    conn_module._supabase_client = None
    yield
    conn_module._supabase_client = None


def test_get_supabase_client_not_initialized_raises_error():
    """Test that getting client before initialization raises error."""
    with pytest.raises(DatabaseConnectionError) as exc_info:
        get_supabase_client()

    assert "not initialized" in str(exc_info.value)


async def test_init_supabase_client_creates_client():
    """Test that init_supabase_client creates an async client."""
    client = await init_supabase_client()
    assert client is not None

    # Second call should return the same client (singleton)
    client2 = await init_supabase_client()
    assert client is client2


async def test_get_supabase_client_after_init():
    """Test that get_supabase_client works after initialization."""
    await init_supabase_client()
    client = get_supabase_client()
    assert client is not None


async def test_close_supabase_client():
    """Test that close_supabase_client clears the client."""
    import bot.infrastructure.database.connection as conn_module

    await init_supabase_client()
    assert conn_module._supabase_client is not None

    await close_supabase_client()
    assert conn_module._supabase_client is None


async def test_close_supabase_client_when_not_initialized():
    """Test that close_supabase_client is safe when client not initialized."""
    # Should not raise any error
    await close_supabase_client()


def test_database_connection_error_inherits_from_exception():
    """Test that DatabaseConnectionError is a proper exception."""
    error = DatabaseConnectionError("test error")
    assert isinstance(error, Exception)
    assert str(error) == "test error"
