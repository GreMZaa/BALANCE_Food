"""Tests for bot application factory and lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.app import create_bot, create_dispatcher


class TestCreateBot:
    """Tests for create_bot function."""

    @patch("bot.app.settings")
    def test_create_bot_returns_bot_instance(self, mock_settings: MagicMock) -> None:
        """Test that create_bot returns a Bot instance."""
        # Token format: <bot_id>:<secret> where bot_id is numeric
        mock_settings.telegram_bot_token.get_secret_value.return_value = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

        bot = create_bot()

        assert isinstance(bot, Bot)
        mock_settings.telegram_bot_token.get_secret_value.assert_called_once()

    @patch("bot.app.settings")
    def test_create_bot_uses_html_parse_mode(self, mock_settings: MagicMock) -> None:
        """Test that bot is configured with HTML parse mode."""
        mock_settings.telegram_bot_token.get_secret_value.return_value = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

        bot = create_bot()

        assert bot.default is not None
        assert bot.default.parse_mode == "HTML"


class TestCreateDispatcher:
    """Tests for create_dispatcher function."""

    @patch.object(Dispatcher, "include_router")
    def test_create_dispatcher_returns_dispatcher_instance(
        self, mock_include_router: MagicMock
    ) -> None:
        """Test that create_dispatcher returns a Dispatcher instance."""
        dp = create_dispatcher()

        assert isinstance(dp, Dispatcher)

    @patch.object(Dispatcher, "include_router")
    def test_create_dispatcher_uses_memory_storage(
        self, mock_include_router: MagicMock
    ) -> None:
        """Test that dispatcher uses MemoryStorage for FSM."""
        dp = create_dispatcher()

        assert isinstance(dp.storage, MemoryStorage)

    @patch.object(Dispatcher, "include_router")
    def test_create_dispatcher_includes_routers(
        self, mock_include_router: MagicMock
    ) -> None:
        """Test that dispatcher includes all handler routers."""
        from bot.handlers import (
            help_router,
            onboarding_router,
            practice_router,
            settings_router,
            start_router,
            stats_router,
            subscription_router,
        )

        create_dispatcher()

        assert mock_include_router.call_count == 7
        calls = mock_include_router.call_args_list
        assert calls[0][0][0] == start_router
        assert calls[1][0][0] == onboarding_router
        assert calls[2][0][0] == practice_router
        assert calls[3][0][0] == stats_router
        assert calls[4][0][0] == settings_router
        assert calls[5][0][0] == subscription_router
        assert calls[6][0][0] == help_router


class TestLifespan:
    """Tests for lifespan context manager."""

    @patch("bot.app.close_supabase_client", new_callable=AsyncMock)
    @patch("bot.app.init_supabase_client", new_callable=AsyncMock)
    async def test_lifespan_initializes_database(
        self,
        mock_init_supabase: AsyncMock,
        mock_close_supabase: AsyncMock,
    ) -> None:
        """Test that lifespan initializes database on startup."""
        from bot.app import lifespan

        mock_bot = MagicMock(spec=Bot)
        mock_bot.get_me = AsyncMock(
            return_value=MagicMock(username="test_bot", id=123456)
        )
        mock_bot.session = MagicMock()
        mock_bot.session.close = AsyncMock()

        async with lifespan(mock_bot):
            mock_init_supabase.assert_called_once()

    @patch("bot.app.close_supabase_client", new_callable=AsyncMock)
    @patch("bot.app.init_supabase_client", new_callable=AsyncMock)
    async def test_lifespan_closes_resources_on_shutdown(
        self,
        mock_init_supabase: AsyncMock,
        mock_close_supabase: AsyncMock,
    ) -> None:
        """Test that lifespan closes resources on shutdown."""
        from bot.app import lifespan

        mock_bot = MagicMock(spec=Bot)
        mock_bot.get_me = AsyncMock(
            return_value=MagicMock(username="test_bot", id=123456)
        )
        mock_bot.session = MagicMock()
        mock_bot.session.close = AsyncMock()

        async with lifespan(mock_bot):
            pass

        mock_close_supabase.assert_called_once()
        mock_bot.session.close.assert_called_once()

    @patch("bot.app.close_supabase_client", new_callable=AsyncMock)
    @patch("bot.app.init_supabase_client", new_callable=AsyncMock)
    async def test_lifespan_gets_bot_info(
        self,
        mock_init_supabase: AsyncMock,
        mock_close_supabase: AsyncMock,
    ) -> None:
        """Test that lifespan retrieves bot info on startup."""
        from bot.app import lifespan

        mock_bot = MagicMock(spec=Bot)
        mock_bot.get_me = AsyncMock(
            return_value=MagicMock(username="test_bot", id=123456)
        )
        mock_bot.session = MagicMock()
        mock_bot.session.close = AsyncMock()

        async with lifespan(mock_bot):
            mock_bot.get_me.assert_called_once()

    @patch("bot.app.close_supabase_client", new_callable=AsyncMock)
    @patch("bot.app.init_supabase_client", new_callable=AsyncMock)
    async def test_lifespan_raises_on_db_failure(
        self,
        mock_init_supabase: AsyncMock,
        mock_close_supabase: AsyncMock,
    ) -> None:
        """Test that lifespan raises exception if database init fails."""
        from bot.app import lifespan

        mock_init_supabase.side_effect = Exception("Connection failed")

        mock_bot = MagicMock(spec=Bot)
        mock_bot.session = MagicMock()
        mock_bot.session.close = AsyncMock()

        with pytest.raises(Exception, match="Connection failed"):
            async with lifespan(mock_bot):
                pass
