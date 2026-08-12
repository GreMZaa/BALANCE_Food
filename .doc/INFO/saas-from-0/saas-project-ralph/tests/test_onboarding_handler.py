"""Tests for onboarding handler."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.user import User
from bot.handlers.onboarding import (
    _complete_onboarding,
    _format_profile_summary,
    process_focus_areas_selection,
    process_grade_selection,
    process_specialty_selection,
    process_tech_stack_selection,
    router,
    start_onboarding,
)
from bot.keyboards.onboarding import (
    FocusAreasCallback,
    GradeCallback,
    SpecialtyCallback,
    TechStackCallback,
)
from bot.states.onboarding import OnboardingStates


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user."""
    user = MagicMock()
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    return user


@pytest.fixture
def mock_message(mock_telegram_user):
    """Create a mock Telegram message."""
    message = AsyncMock()
    message.from_user = mock_telegram_user
    message.answer = AsyncMock()
    return message


@pytest.fixture
def mock_state():
    """Create a mock FSMContext."""
    state = AsyncMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    state.get_data = AsyncMock(return_value={})
    state.clear = AsyncMock()
    return state


@pytest.fixture
def mock_callback(mock_telegram_user):
    """Create a mock CallbackQuery."""
    callback = AsyncMock()
    callback.from_user = mock_telegram_user
    callback.answer = AsyncMock()
    callback.message = AsyncMock()
    callback.message.edit_text = AsyncMock()
    return callback


class TestOnboardingRouter:
    """Tests for onboarding router configuration."""

    def test_router_has_correct_name(self):
        """Test that router has correct name."""
        assert router.name == "onboarding"

    def test_router_has_callback_handlers(self):
        """Test that router has registered callback handlers."""
        # Check that there are callback query handlers
        assert len(router.callback_query.handlers) > 0


class TestStartOnboarding:
    """Tests for start_onboarding function."""

    async def test_start_onboarding_sets_state(self, mock_message, mock_state):
        """Test that start_onboarding sets FSM state to waiting_specialty."""
        await start_onboarding(mock_message, mock_state)

        mock_state.set_state.assert_called_once_with(OnboardingStates.waiting_specialty)

    async def test_start_onboarding_sends_message(self, mock_message, mock_state):
        """Test that start_onboarding sends specialty selection message."""
        await start_onboarding(mock_message, mock_state)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args
        message_text = call_args[0][0]

        assert "Шаг 1 из 4" in message_text
        assert "специальност" in message_text.lower()

    async def test_start_onboarding_includes_keyboard(self, mock_message, mock_state):
        """Test that start_onboarding includes inline keyboard."""
        await start_onboarding(mock_message, mock_state)

        call_args = mock_message.answer.call_args
        assert "reply_markup" in call_args.kwargs


class TestProcessSpecialtySelection:
    """Tests for process_specialty_selection handler."""

    async def test_process_specialty_saves_to_state(self, mock_callback, mock_state):
        """Test that specialty selection saves value to FSM context."""
        callback_data = SpecialtyCallback(value=Specialty.BACKEND.value)

        await process_specialty_selection(mock_callback, callback_data, mock_state)

        mock_state.update_data.assert_called_once_with(specialty=Specialty.BACKEND.value)

    async def test_process_specialty_changes_state_to_grade(
        self, mock_callback, mock_state
    ):
        """Test that specialty selection moves to grade selection state."""
        callback_data = SpecialtyCallback(value=Specialty.BACKEND.value)

        await process_specialty_selection(mock_callback, callback_data, mock_state)

        mock_state.set_state.assert_called_once_with(OnboardingStates.waiting_grade)

    async def test_process_specialty_edits_message(self, mock_callback, mock_state):
        """Test that specialty selection edits message with grade keyboard."""
        callback_data = SpecialtyCallback(value=Specialty.BACKEND.value)

        await process_specialty_selection(mock_callback, callback_data, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]

        assert "Шаг 2 из 4" in message_text
        assert "уровень" in message_text.lower() or "грейд" in message_text.lower()

    async def test_process_specialty_answers_callback(self, mock_callback, mock_state):
        """Test that specialty selection answers the callback."""
        callback_data = SpecialtyCallback(value=Specialty.BACKEND.value)

        await process_specialty_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()

    async def test_process_specialty_invalid_value(self, mock_callback, mock_state):
        """Test that invalid specialty value is handled gracefully."""
        callback_data = SpecialtyCallback(value="invalid_specialty")

        await process_specialty_selection(mock_callback, callback_data, mock_state)

        # Should answer with error message, not update state
        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "Неизвестная" in call_args[0][0] or "специальность" in call_args[0][0].lower()

        # State should not be updated
        mock_state.update_data.assert_not_called()


class TestProcessGradeSelection:
    """Tests for process_grade_selection handler."""

    async def test_process_grade_saves_to_state(self, mock_callback, mock_state):
        """Test that grade selection saves value to FSM context."""
        callback_data = GradeCallback(value=Grade.JUNIOR.value)

        await process_grade_selection(mock_callback, callback_data, mock_state)

        mock_state.update_data.assert_called_once_with(grade=Grade.JUNIOR.value)

    async def test_process_grade_changes_state_to_tech_stack(
        self, mock_callback, mock_state
    ):
        """Test that grade selection moves to tech stack selection state."""
        callback_data = GradeCallback(value=Grade.MIDDLE.value)

        await process_grade_selection(mock_callback, callback_data, mock_state)

        mock_state.set_state.assert_called_once_with(OnboardingStates.waiting_tech_stack)

    async def test_process_grade_edits_message(self, mock_callback, mock_state):
        """Test that grade selection edits message with tech stack keyboard."""
        callback_data = GradeCallback(value=Grade.SENIOR.value)

        await process_grade_selection(mock_callback, callback_data, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]

        assert "Шаг 3 из 4" in message_text
        assert "технолог" in message_text.lower()

    async def test_process_grade_answers_callback(self, mock_callback, mock_state):
        """Test that grade selection answers the callback."""
        callback_data = GradeCallback(value=Grade.JUNIOR.value)

        await process_grade_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()

    async def test_process_grade_invalid_value(self, mock_callback, mock_state):
        """Test that invalid grade value is handled gracefully."""
        callback_data = GradeCallback(value="invalid_grade")

        await process_grade_selection(mock_callback, callback_data, mock_state)

        # Should answer with error message
        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "Неизвестный" in call_args[0][0] or "уровень" in call_args[0][0].lower()

        # State should not be updated
        mock_state.update_data.assert_not_called()

    async def test_process_grade_all_grades_valid(self, mock_callback, mock_state):
        """Test that all Grade enum values are processed correctly."""
        for grade in Grade:
            mock_state.reset_mock()
            mock_callback.reset_mock()

            callback_data = GradeCallback(value=grade.value)
            await process_grade_selection(mock_callback, callback_data, mock_state)

            mock_state.update_data.assert_called_once_with(grade=grade.value)


class TestOnboardingFlow:
    """Integration-like tests for the onboarding flow."""

    async def test_full_onboarding_state_progression(
        self, mock_message, mock_callback, mock_state
    ):
        """Test that states progress correctly through onboarding."""
        # Step 1: Start onboarding
        await start_onboarding(mock_message, mock_state)
        mock_state.set_state.assert_called_with(OnboardingStates.waiting_specialty)

        # Step 2: Select specialty
        mock_state.reset_mock()
        callback_data = SpecialtyCallback(value=Specialty.BACKEND.value)
        await process_specialty_selection(mock_callback, callback_data, mock_state)
        mock_state.set_state.assert_called_with(OnboardingStates.waiting_grade)

        # Step 3: Select grade (leads to tech stack)
        mock_state.reset_mock()
        callback_data = GradeCallback(value=Grade.JUNIOR.value)
        await process_grade_selection(mock_callback, callback_data, mock_state)
        mock_state.set_state.assert_called_with(OnboardingStates.waiting_tech_stack)

    async def test_data_accumulates_in_state(self, mock_message, mock_callback, mock_state):
        """Test that data accumulates correctly in FSM context."""
        # Start onboarding
        await start_onboarding(mock_message, mock_state)

        # Select specialty
        specialty_data = SpecialtyCallback(value=Specialty.BACKEND.value)
        await process_specialty_selection(mock_callback, specialty_data, mock_state)

        # Select grade
        grade_data = GradeCallback(value=Grade.MIDDLE.value)
        await process_grade_selection(mock_callback, grade_data, mock_state)

        # Verify update_data was called with correct values
        calls = mock_state.update_data.call_args_list
        assert len(calls) == 2
        assert calls[0] == (({"specialty": "backend"},),) or calls[0][1] == {"specialty": "backend"}
        assert calls[1] == (({"grade": "middle"},),) or calls[1][1] == {"grade": "middle"}


class TestProcessTechStackSelection:
    """Tests for process_tech_stack_selection handler."""

    async def test_toggle_adds_tech_to_empty_selection(self, mock_callback, mock_state):
        """Test that toggling a tech adds it to empty selection."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = TechStackCallback(action="toggle", value="Python")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_state.update_data.assert_called_once_with(tech_stack=["Python"])

    async def test_toggle_adds_tech_to_existing_selection(self, mock_callback, mock_state):
        """Test that toggling a tech adds it to existing selection."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python"]})
        callback_data = TechStackCallback(action="toggle", value="Go")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        tech_stack = set(call_args[1]["tech_stack"])
        assert tech_stack == {"Python", "Go"}

    async def test_toggle_removes_tech_from_selection(self, mock_callback, mock_state):
        """Test that toggling an already selected tech removes it."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python", "Go"]})
        callback_data = TechStackCallback(action="toggle", value="Python")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        tech_stack = call_args[1]["tech_stack"]
        assert tech_stack == ["Go"]

    async def test_toggle_updates_keyboard(self, mock_callback, mock_state):
        """Test that toggling updates the keyboard with selection count."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = TechStackCallback(action="toggle", value="Python")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]
        assert "Выбрано: 1" in message_text

    async def test_toggle_answers_callback(self, mock_callback, mock_state):
        """Test that toggle answers the callback."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = TechStackCallback(action="toggle", value="Python")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()

    async def test_done_with_no_selection_shows_error(self, mock_callback, mock_state):
        """Test that done with no selection shows error."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = TechStackCallback(action="done", value="")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "хотя бы одну" in call_args[0][0].lower()
        assert call_args[1].get("show_alert") is True

    async def test_done_with_empty_list_shows_error(self, mock_callback, mock_state):
        """Test that done with empty list shows error."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": []})
        callback_data = TechStackCallback(action="done", value="")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "хотя бы одну" in call_args[0][0].lower()

    async def test_done_with_selection_moves_to_focus_areas(self, mock_callback, mock_state):
        """Test that done with selection moves to focus areas state."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python"]})
        callback_data = TechStackCallback(action="done", value="")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_state.set_state.assert_called_once_with(OnboardingStates.waiting_focus_areas)

    async def test_done_edits_message_with_focus_areas(self, mock_callback, mock_state):
        """Test that done edits message with focus areas keyboard."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python", "Go"]})
        callback_data = TechStackCallback(action="done", value="")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]
        assert "Шаг 4 из 4" in message_text
        assert "област" in message_text.lower()

    async def test_done_saves_final_selection(self, mock_callback, mock_state):
        """Test that done saves the final tech stack selection."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python", "Go"]})
        callback_data = TechStackCallback(action="done", value="")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        tech_stack = set(call_args[1]["tech_stack"])
        assert tech_stack == {"Python", "Go"}

    async def test_done_answers_callback(self, mock_callback, mock_state):
        """Test that done answers the callback."""
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python"]})
        callback_data = TechStackCallback(action="done", value="")

        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called()

    async def test_multiple_toggles_work_correctly(self, mock_callback, mock_state):
        """Test that multiple toggles work correctly."""
        # Start with empty
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = TechStackCallback(action="toggle", value="Python")
        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        # Add another
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python"]})
        mock_state.reset_mock()
        callback_data = TechStackCallback(action="toggle", value="Java")
        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        tech_stack = set(call_args[1]["tech_stack"])
        assert tech_stack == {"Python", "Java"}

        # Remove first
        mock_state.get_data = AsyncMock(return_value={"tech_stack": ["Python", "Java"]})
        mock_state.reset_mock()
        callback_data = TechStackCallback(action="toggle", value="Python")
        await process_tech_stack_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        tech_stack = call_args[1]["tech_stack"]
        assert tech_stack == ["Java"]


class TestProcessFocusAreasSelection:
    """Tests for process_focus_areas_selection handler."""

    async def test_toggle_adds_area_to_empty_selection(self, mock_callback, mock_state):
        """Test that toggling an area adds it to empty selection."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = FocusAreasCallback(action="toggle", value=Category.ALGORITHMS.value)

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        mock_state.update_data.assert_called_once()
        call_args = mock_state.update_data.call_args
        focus_areas = call_args[1]["focus_areas"]
        assert focus_areas == [Category.ALGORITHMS.value]

    async def test_toggle_adds_area_to_existing_selection(self, mock_callback, mock_state):
        """Test that toggling an area adds it to existing selection."""
        mock_state.get_data = AsyncMock(
            return_value={"focus_areas": [Category.ALGORITHMS.value]}
        )
        callback_data = FocusAreasCallback(action="toggle", value=Category.DATABASES.value)

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        focus_areas = set(call_args[1]["focus_areas"])
        assert focus_areas == {Category.ALGORITHMS.value, Category.DATABASES.value}

    async def test_toggle_removes_area_from_selection(self, mock_callback, mock_state):
        """Test that toggling an already selected area removes it."""
        mock_state.get_data = AsyncMock(
            return_value={
                "focus_areas": [Category.ALGORITHMS.value, Category.DATABASES.value]
            }
        )
        callback_data = FocusAreasCallback(action="toggle", value=Category.ALGORITHMS.value)

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        focus_areas = call_args[1]["focus_areas"]
        assert focus_areas == [Category.DATABASES.value]

    async def test_toggle_updates_keyboard(self, mock_callback, mock_state):
        """Test that toggling updates the keyboard with selection count."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = FocusAreasCallback(action="toggle", value=Category.ALGORITHMS.value)

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]
        assert "Выбрано: 1" in message_text

    async def test_toggle_answers_callback(self, mock_callback, mock_state):
        """Test that toggle answers the callback."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = FocusAreasCallback(action="toggle", value=Category.ALGORITHMS.value)

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()

    async def test_done_with_no_selection_shows_error(self, mock_callback, mock_state):
        """Test that done with no selection shows error."""
        mock_state.get_data = AsyncMock(return_value={})
        callback_data = FocusAreasCallback(action="done", value="")

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "хотя бы одну" in call_args[0][0].lower()
        assert call_args[1].get("show_alert") is True

    async def test_done_with_empty_list_shows_error(self, mock_callback, mock_state):
        """Test that done with empty list shows error."""
        mock_state.get_data = AsyncMock(return_value={"focus_areas": []})
        callback_data = FocusAreasCallback(action="done", value="")

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        mock_callback.answer.assert_called_once()
        call_args = mock_callback.answer.call_args
        assert "хотя бы одну" in call_args[0][0].lower()

    @patch("bot.handlers.onboarding._complete_onboarding")
    async def test_done_with_selection_calls_complete_onboarding(
        self, mock_complete, mock_callback, mock_state
    ):
        """Test that done with selection calls _complete_onboarding."""
        mock_state.get_data = AsyncMock(
            return_value={"focus_areas": [Category.ALGORITHMS.value]}
        )
        mock_complete.return_value = None
        callback_data = FocusAreasCallback(action="done", value="")

        await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        mock_complete.assert_called_once_with(mock_callback, mock_state)

    async def test_done_saves_final_selection(self, mock_callback, mock_state):
        """Test that done saves the final focus areas selection."""
        mock_state.get_data = AsyncMock(
            return_value={
                "focus_areas": [Category.ALGORITHMS.value, Category.DATABASES.value]
            }
        )
        callback_data = FocusAreasCallback(action="done", value="")

        with patch("bot.handlers.onboarding._complete_onboarding"):
            await process_focus_areas_selection(mock_callback, callback_data, mock_state)

        call_args = mock_state.update_data.call_args
        focus_areas = set(call_args[1]["focus_areas"])
        assert focus_areas == {Category.ALGORITHMS.value, Category.DATABASES.value}


class TestCompleteOnboarding:
    """Tests for _complete_onboarding function."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock User."""
        return User(
            id=uuid4(),
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
        )

    async def test_complete_onboarding_clears_state(self, mock_callback, mock_state, mock_user):
        """Test that complete onboarding clears FSM state."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.JUNIOR.value,
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        with (
            patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class,
            patch("bot.handlers.onboarding.ProfileRepository") as mock_profile_repo_class,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_user_repo_class.return_value = mock_user_repo

            mock_profile_repo = MagicMock()
            mock_profile_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
            mock_profile_repo_class.return_value = mock_profile_repo

            await _complete_onboarding(mock_callback, mock_state)

        mock_state.clear.assert_called_once()

    async def test_complete_onboarding_creates_profile(
        self, mock_callback, mock_state, mock_user
    ):
        """Test that complete onboarding creates a profile in database."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.MIDDLE.value,
                "tech_stack": ["Python", "Go"],
                "focus_areas": [Category.ALGORITHMS.value, Category.DATABASES.value],
            }
        )

        with (
            patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class,
            patch("bot.handlers.onboarding.ProfileRepository") as mock_profile_repo_class,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_user_repo_class.return_value = mock_user_repo

            mock_profile_repo = MagicMock()
            mock_profile_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
            mock_profile_repo_class.return_value = mock_profile_repo

            await _complete_onboarding(mock_callback, mock_state)

        mock_profile_repo.create.assert_called_once()
        created_profile = mock_profile_repo.create.call_args[0][0]
        assert created_profile.user_id == mock_user.id
        assert created_profile.specialty == Specialty.BACKEND
        assert created_profile.grade == Grade.MIDDLE
        assert set(created_profile.tech_stack) == {"Python", "Go"}
        assert set(created_profile.focus_areas) == {Category.ALGORITHMS, Category.DATABASES}

    async def test_complete_onboarding_sets_initial_difficulty_junior(
        self, mock_callback, mock_state, mock_user
    ):
        """Test that Junior grade gets initial difficulty of 2."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.JUNIOR.value,
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        with (
            patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class,
            patch("bot.handlers.onboarding.ProfileRepository") as mock_profile_repo_class,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_user_repo_class.return_value = mock_user_repo

            mock_profile_repo = MagicMock()
            mock_profile_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
            mock_profile_repo_class.return_value = mock_profile_repo

            await _complete_onboarding(mock_callback, mock_state)

        created_profile = mock_profile_repo.create.call_args[0][0]
        assert created_profile.current_difficulty == 2

    async def test_complete_onboarding_sets_initial_difficulty_senior(
        self, mock_callback, mock_state, mock_user
    ):
        """Test that Senior grade gets initial difficulty of 7."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.SENIOR.value,
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        with (
            patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class,
            patch("bot.handlers.onboarding.ProfileRepository") as mock_profile_repo_class,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_user_repo_class.return_value = mock_user_repo

            mock_profile_repo = MagicMock()
            mock_profile_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
            mock_profile_repo_class.return_value = mock_profile_repo

            await _complete_onboarding(mock_callback, mock_state)

        created_profile = mock_profile_repo.create.call_args[0][0]
        assert created_profile.current_difficulty == 7

    async def test_complete_onboarding_shows_confirmation_message(
        self, mock_callback, mock_state, mock_user
    ):
        """Test that complete onboarding shows confirmation message."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.JUNIOR.value,
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        with (
            patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class,
            patch("bot.handlers.onboarding.ProfileRepository") as mock_profile_repo_class,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_user_repo_class.return_value = mock_user_repo

            mock_profile_repo = MagicMock()
            mock_profile_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
            mock_profile_repo_class.return_value = mock_profile_repo

            await _complete_onboarding(mock_callback, mock_state)

        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]
        assert "Профиль создан" in message_text
        assert "/practice" in message_text

    async def test_complete_onboarding_answers_callback(
        self, mock_callback, mock_state, mock_user
    ):
        """Test that complete onboarding answers the callback."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.JUNIOR.value,
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        with (
            patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class,
            patch("bot.handlers.onboarding.ProfileRepository") as mock_profile_repo_class,
        ):
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=mock_user)
            mock_user_repo_class.return_value = mock_user_repo

            mock_profile_repo = MagicMock()
            mock_profile_repo.create = AsyncMock(return_value=MagicMock(id=uuid4()))
            mock_profile_repo_class.return_value = mock_profile_repo

            await _complete_onboarding(mock_callback, mock_state)

        mock_callback.answer.assert_called_once_with("Профиль сохранён!")

    async def test_complete_onboarding_user_not_found(self, mock_callback, mock_state):
        """Test that missing user is handled gracefully."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": Specialty.BACKEND.value,
                "grade": Grade.JUNIOR.value,
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        with patch("bot.handlers.onboarding.UserRepository") as mock_user_repo_class:
            mock_user_repo = MagicMock()
            mock_user_repo.get_by_telegram_id = AsyncMock(return_value=None)
            mock_user_repo_class.return_value = mock_user_repo

            await _complete_onboarding(mock_callback, mock_state)

        # State should be cleared
        mock_state.clear.assert_called_once()
        # Error message should be shown
        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]
        assert "не найден" in message_text.lower() or "❌" in message_text

    async def test_complete_onboarding_invalid_data(self, mock_callback, mock_state):
        """Test that invalid data is handled gracefully."""
        mock_state.get_data = AsyncMock(
            return_value={
                "specialty": "invalid",
                "grade": "invalid",
                "tech_stack": ["Python"],
                "focus_areas": [Category.ALGORITHMS.value],
            }
        )

        await _complete_onboarding(mock_callback, mock_state)

        # State should be cleared
        mock_state.clear.assert_called_once()
        # Error message should be shown
        mock_callback.message.edit_text.assert_called_once()
        call_args = mock_callback.message.edit_text.call_args
        message_text = call_args[0][0]
        assert "ошибка" in message_text.lower() or "❌" in message_text


class TestFormatProfileSummary:
    """Tests for _format_profile_summary function."""

    def test_format_profile_summary_basic(self):
        """Test basic profile summary formatting."""
        summary = _format_profile_summary(
            specialty=Specialty.BACKEND,
            grade=Grade.JUNIOR,
            tech_stack=["Python"],
            focus_areas=[Category.ALGORITHMS],
        )

        assert "Профиль создан" in summary
        assert "Backend" in summary
        assert "Junior" in summary
        assert "Python" in summary
        assert "Алгоритмы" in summary
        assert "/practice" in summary

    def test_format_profile_summary_multiple_tech(self):
        """Test profile summary with multiple technologies."""
        summary = _format_profile_summary(
            specialty=Specialty.BACKEND,
            grade=Grade.MIDDLE,
            tech_stack=["Python", "Go", "Rust"],
            focus_areas=[Category.DATABASES],
        )

        assert "Python" in summary
        assert "Go" in summary
        assert "Rust" in summary

    def test_format_profile_summary_multiple_focus_areas(self):
        """Test profile summary with multiple focus areas."""
        summary = _format_profile_summary(
            specialty=Specialty.BACKEND,
            grade=Grade.SENIOR,
            tech_stack=["Java"],
            focus_areas=[Category.SYSTEM_DESIGN, Category.ARCHITECTURE, Category.MICROSERVICES],
        )

        assert "System Design" in summary
        assert "Архитектура" in summary
        assert "Микросервисы" in summary

    def test_format_profile_summary_empty_lists(self):
        """Test profile summary with empty lists."""
        summary = _format_profile_summary(
            specialty=Specialty.BACKEND,
            grade=Grade.JUNIOR,
            tech_stack=[],
            focus_areas=[],
        )

        assert "—" in summary  # Placeholder for empty lists
