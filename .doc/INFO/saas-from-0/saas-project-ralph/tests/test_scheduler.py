"""Tests for scheduler module."""

from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from aiogram.enums import ParseMode

from bot.domain.entities.progress import Progress
from bot.domain.entities.reminder_settings import ReminderSettings
from bot.domain.entities.user import User
from bot.scheduler.jobs import _build_reminder_text, check_and_send_reminders
from bot.scheduler.scheduler import (
    JOB_ID,
    get_scheduler,
    shutdown_scheduler,
    start_scheduler,
)


class TestStartScheduler:
    """Tests for start_scheduler function."""

    async def test_start_scheduler_returns_scheduler(self):
        """Test that start_scheduler returns a running scheduler."""
        mock_bot = MagicMock()

        scheduler = start_scheduler(mock_bot)

        try:
            assert scheduler is not None
            assert scheduler.running is True
        finally:
            scheduler.shutdown(wait=False)
            import bot.scheduler.scheduler as mod

            mod._scheduler = None

    async def test_start_scheduler_adds_reminder_job(self):
        """Test that the reminder check job is added."""
        mock_bot = MagicMock()

        scheduler = start_scheduler(mock_bot)

        try:
            job = scheduler.get_job(JOB_ID)
            assert job is not None
        finally:
            scheduler.shutdown(wait=False)
            import bot.scheduler.scheduler as mod

            mod._scheduler = None

    async def test_start_scheduler_twice_returns_same_instance(self):
        """Test that calling start_scheduler twice returns the same scheduler."""
        mock_bot = MagicMock()

        scheduler1 = start_scheduler(mock_bot)
        scheduler2 = start_scheduler(mock_bot)

        try:
            assert scheduler1 is scheduler2
        finally:
            scheduler1.shutdown(wait=False)
            import bot.scheduler.scheduler as mod

            mod._scheduler = None


class TestShutdownScheduler:
    """Tests for shutdown_scheduler function."""

    async def test_shutdown_running_scheduler(self):
        """Test shutting down a running scheduler."""
        mock_bot = MagicMock()
        start_scheduler(mock_bot)

        shutdown_scheduler()

        assert get_scheduler() is None

    def test_shutdown_when_not_started(self):
        """Test shutdown when scheduler was never started."""
        import bot.scheduler.scheduler as mod

        mod._scheduler = None

        # Should not raise
        shutdown_scheduler()

        assert get_scheduler() is None


class TestGetScheduler:
    """Tests for get_scheduler function."""

    def test_returns_none_when_not_started(self):
        """Test returns None before scheduler is started."""
        import bot.scheduler.scheduler as mod

        mod._scheduler = None

        assert get_scheduler() is None

    async def test_returns_scheduler_after_start(self):
        """Test returns scheduler instance after start."""
        mock_bot = MagicMock()
        scheduler = start_scheduler(mock_bot)

        try:
            assert get_scheduler() is scheduler
        finally:
            scheduler.shutdown(wait=False)
            import bot.scheduler.scheduler as mod

            mod._scheduler = None


class TestCheckAndSendReminders:
    """Tests for check_and_send_reminders job function."""

    @patch("bot.scheduler.jobs.ReminderRepository")
    async def test_no_eligible_users(self, mock_reminder_repo_cls: MagicMock):
        """Test that nothing happens when no users are eligible."""
        mock_repo = AsyncMock()
        mock_repo.get_users_for_reminder = AsyncMock(return_value=[])
        mock_reminder_repo_cls.return_value = mock_repo

        mock_bot = AsyncMock()

        await check_and_send_reminders(mock_bot)

        mock_bot.send_message.assert_not_awaited()

    @patch("bot.scheduler.jobs.settings")
    @patch("bot.scheduler.jobs.ProgressRepository")
    @patch("bot.scheduler.jobs.UserRepository")
    @patch("bot.scheduler.jobs.ReminderRepository")
    async def test_sends_reminder_to_eligible_user(
        self,
        mock_reminder_repo_cls: MagicMock,
        mock_user_repo_cls: MagicMock,
        mock_progress_repo_cls: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test that reminder is sent to an eligible user."""
        user_id = uuid4()
        telegram_id = 12345

        reminder = ReminderSettings(
            user_id=user_id,
            reminders_enabled=True,
            reminder_times=[time(10, 0)],
            reminders_sent_today=0,
        )
        user = User(telegram_id=telegram_id, first_name="Alex")
        progress = Progress(user_id=user_id, questions_today=2)

        mock_reminder_repo = AsyncMock()
        mock_reminder_repo.get_users_for_reminder = AsyncMock(return_value=[reminder])
        mock_reminder_repo.update = AsyncMock(return_value=reminder)
        mock_reminder_repo_cls.return_value = mock_reminder_repo

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_user_repo_cls.return_value = mock_user_repo

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_by_user_id = AsyncMock(return_value=progress)
        mock_progress_repo_cls.return_value = mock_progress_repo

        mock_settings.daily_goal = 5
        mock_settings.timezone = "UTC"

        mock_bot = AsyncMock()

        await check_and_send_reminders(mock_bot)

        mock_bot.send_message.assert_awaited_once()
        call_kwargs = mock_bot.send_message.call_args
        assert call_kwargs.kwargs["chat_id"] == telegram_id
        assert call_kwargs.kwargs["parse_mode"] == ParseMode.HTML
        assert call_kwargs.kwargs["reply_markup"] is not None
        mock_reminder_repo.update.assert_awaited_once()

    @patch("bot.scheduler.jobs.settings")
    @patch("bot.scheduler.jobs.ProgressRepository")
    @patch("bot.scheduler.jobs.UserRepository")
    @patch("bot.scheduler.jobs.ReminderRepository")
    async def test_skips_user_who_reached_daily_goal(
        self,
        mock_reminder_repo_cls: MagicMock,
        mock_user_repo_cls: MagicMock,
        mock_progress_repo_cls: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test that user who reached daily goal is not reminded."""
        user_id = uuid4()

        reminder = ReminderSettings(
            user_id=user_id,
            reminders_enabled=True,
            reminder_times=[time(10, 0)],
            reminders_sent_today=0,
        )
        user = User(telegram_id=99999, first_name="Bob")
        progress = Progress(user_id=user_id, questions_today=5)

        mock_reminder_repo = AsyncMock()
        mock_reminder_repo.get_users_for_reminder = AsyncMock(return_value=[reminder])
        mock_reminder_repo_cls.return_value = mock_reminder_repo

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_user_repo_cls.return_value = mock_user_repo

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_by_user_id = AsyncMock(return_value=progress)
        mock_progress_repo_cls.return_value = mock_progress_repo

        mock_settings.daily_goal = 5
        mock_settings.timezone = "UTC"

        mock_bot = AsyncMock()

        await check_and_send_reminders(mock_bot)

        mock_bot.send_message.assert_not_awaited()

    @patch("bot.scheduler.jobs.settings")
    @patch("bot.scheduler.jobs.ProgressRepository")
    @patch("bot.scheduler.jobs.UserRepository")
    @patch("bot.scheduler.jobs.ReminderRepository")
    async def test_skips_user_not_found(
        self,
        mock_reminder_repo_cls: MagicMock,
        mock_user_repo_cls: MagicMock,
        mock_progress_repo_cls: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test that reminder is skipped if user is not found in DB."""
        user_id = uuid4()

        reminder = ReminderSettings(
            user_id=user_id,
            reminders_enabled=True,
            reminder_times=[time(10, 0)],
        )

        mock_reminder_repo = AsyncMock()
        mock_reminder_repo.get_users_for_reminder = AsyncMock(return_value=[reminder])
        mock_reminder_repo_cls.return_value = mock_reminder_repo

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=None)
        mock_user_repo_cls.return_value = mock_user_repo

        mock_progress_repo = AsyncMock()
        mock_progress_repo_cls.return_value = mock_progress_repo

        mock_settings.timezone = "UTC"

        mock_bot = AsyncMock()

        await check_and_send_reminders(mock_bot)

        mock_bot.send_message.assert_not_awaited()

    @patch("bot.scheduler.jobs.settings")
    @patch("bot.scheduler.jobs.ProgressRepository")
    @patch("bot.scheduler.jobs.UserRepository")
    @patch("bot.scheduler.jobs.ReminderRepository")
    async def test_handles_no_progress_record(
        self,
        mock_reminder_repo_cls: MagicMock,
        mock_user_repo_cls: MagicMock,
        mock_progress_repo_cls: MagicMock,
        mock_settings: MagicMock,
    ):
        """Test reminder is sent when user has no progress record yet."""
        user_id = uuid4()
        telegram_id = 11111

        reminder = ReminderSettings(
            user_id=user_id,
            reminders_enabled=True,
            reminder_times=[time(10, 0)],
            reminders_sent_today=0,
        )
        user = User(telegram_id=telegram_id, first_name="Carol")

        mock_reminder_repo = AsyncMock()
        mock_reminder_repo.get_users_for_reminder = AsyncMock(return_value=[reminder])
        mock_reminder_repo.update = AsyncMock(return_value=reminder)
        mock_reminder_repo_cls.return_value = mock_reminder_repo

        mock_user_repo = AsyncMock()
        mock_user_repo.get_by_id = AsyncMock(return_value=user)
        mock_user_repo_cls.return_value = mock_user_repo

        mock_progress_repo = AsyncMock()
        mock_progress_repo.get_by_user_id = AsyncMock(return_value=None)
        mock_progress_repo_cls.return_value = mock_progress_repo

        mock_settings.daily_goal = 5
        mock_settings.timezone = "UTC"

        mock_bot = AsyncMock()

        await check_and_send_reminders(mock_bot)

        mock_bot.send_message.assert_awaited_once()

    @patch("bot.scheduler.jobs.ReminderRepository")
    async def test_handles_repository_error_gracefully(
        self, mock_reminder_repo_cls: MagicMock
    ):
        """Test that repository errors don't crash the job."""
        mock_repo = AsyncMock()
        mock_repo.get_users_for_reminder = AsyncMock(
            side_effect=Exception("DB connection lost")
        )
        mock_reminder_repo_cls.return_value = mock_repo

        mock_bot = AsyncMock()

        # Should not raise
        await check_and_send_reminders(mock_bot)

        mock_bot.send_message.assert_not_awaited()


class TestBuildReminderText:
    """Tests for _build_reminder_text helper."""

    def test_with_first_name(self):
        """Test reminder text includes user's first name."""
        text = _build_reminder_text(3, "Alex", 0)
        assert "Alex" in text

    def test_without_first_name(self):
        """Test reminder text uses fallback when no first name."""
        text = _build_reminder_text(3, None, 0)
        assert "\u0434\u0440\u0443\u0433" in text

    def test_remaining_included(self):
        """Test remaining count is in the message."""
        text = _build_reminder_text(3, "Alex", 0)
        assert "3" in text

    def test_contains_motivational_message(self):
        """Test that reminder includes a motivational phrase."""
        from bot.scheduler.jobs import MOTIVATIONAL_MESSAGES

        text = _build_reminder_text(3, "Alex", 0)
        assert MOTIVATIONAL_MESSAGES[0] in text

    def test_different_motivational_per_reminder_index(self):
        """Test that different reminder indices get different motivational messages."""
        from bot.scheduler.jobs import MOTIVATIONAL_MESSAGES

        text0 = _build_reminder_text(3, "Alex", 0)
        text1 = _build_reminder_text(3, "Alex", 1)
        text2 = _build_reminder_text(3, "Alex", 2)

        assert MOTIVATIONAL_MESSAGES[0] in text0
        assert MOTIVATIONAL_MESSAGES[1] in text1
        assert MOTIVATIONAL_MESSAGES[2] in text2

    def test_singular_question_word(self):
        """Test Russian grammar for 1 question."""
        text = _build_reminder_text(1, "Alex", 0)
        assert "\u0432\u043e\u043f\u0440\u043e\u0441" in text
        assert "\u0432\u043e\u043f\u0440\u043e\u0441\u0430" not in text
        assert "\u0432\u043e\u043f\u0440\u043e\u0441\u043e\u0432" not in text

    def test_few_questions_word(self):
        """Test Russian grammar for 2-4 questions."""
        text = _build_reminder_text(3, "Alex", 0)
        assert "\u0432\u043e\u043f\u0440\u043e\u0441\u0430" in text

    def test_many_questions_word(self):
        """Test Russian grammar for 5+ questions."""
        text = _build_reminder_text(5, "Alex", 0)
        assert "\u0432\u043e\u043f\u0440\u043e\u0441\u043e\u0432" in text

    def test_html_formatting(self):
        """Test that reminder text uses HTML bold tags."""
        text = _build_reminder_text(3, "Alex", 0)
        assert "<b>" in text
        assert "</b>" in text


class TestReminderKeyboard:
    """Tests for reminder practice keyboard."""

    def test_keyboard_has_one_button(self):
        """Test that the reminder keyboard has exactly one button."""
        from bot.keyboards.reminder import get_reminder_practice_keyboard

        keyboard = get_reminder_practice_keyboard()
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1

    def test_button_text(self):
        """Test the button text contains 'Продолжить практику'."""
        from bot.keyboards.reminder import get_reminder_practice_keyboard

        keyboard = get_reminder_practice_keyboard()
        button = keyboard.inline_keyboard[0][0]
        assert "\u041f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u043f\u0440\u0430\u043a\u0442\u0438\u043a\u0443" in button.text

    def test_button_callback_data(self):
        """Test that the button uses NextQuestionCallback."""
        from bot.keyboards.reminder import get_reminder_practice_keyboard

        keyboard = get_reminder_practice_keyboard()
        button = keyboard.inline_keyboard[0][0]
        assert button.callback_data is not None
        assert "practice" in button.callback_data


class TestSchedulerImports:
    """Tests for scheduler module imports."""

    def test_import_start_scheduler(self):
        """Test start_scheduler is importable from scheduler package."""
        from bot.scheduler import start_scheduler

        assert start_scheduler is not None

    def test_import_shutdown_scheduler(self):
        """Test shutdown_scheduler is importable from scheduler package."""
        from bot.scheduler import shutdown_scheduler

        assert shutdown_scheduler is not None
