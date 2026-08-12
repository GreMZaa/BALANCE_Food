"""Tests for PracticeStates FSM."""

from aiogram.fsm.state import StatesGroup

from bot.states.practice import PracticeStates


class TestPracticeStates:
    """Test suite for PracticeStates."""

    def test_practice_states_is_states_group(self) -> None:
        """Test that PracticeStates inherits from StatesGroup."""
        assert issubclass(PracticeStates, StatesGroup)

    def test_waiting_answer_state_exists(self) -> None:
        """Test that waiting_answer state exists."""
        assert hasattr(PracticeStates, "waiting_answer")
        assert PracticeStates.waiting_answer is not None

    def test_processing_answer_state_exists(self) -> None:
        """Test that processing_answer state exists."""
        assert hasattr(PracticeStates, "processing_answer")
        assert PracticeStates.processing_answer is not None

    def test_waiting_answer_state_name(self) -> None:
        """Test that waiting_answer state has correct state name."""
        # State name format: GroupName:state_name
        assert "waiting_answer" in PracticeStates.waiting_answer.state

    def test_processing_answer_state_name(self) -> None:
        """Test that processing_answer state has correct state name."""
        assert "processing_answer" in PracticeStates.processing_answer.state

    def test_states_have_correct_group(self) -> None:
        """Test that all states belong to PracticeStates group."""
        assert "PracticeStates" in PracticeStates.waiting_answer.state
        assert "PracticeStates" in PracticeStates.processing_answer.state

    def test_all_states_count(self) -> None:
        """Test that there are exactly 2 states in PracticeStates."""
        # Get all states from the group
        states = PracticeStates.__states__
        assert len(states) == 2

    def test_import_from_states_package(self) -> None:
        """Test that PracticeStates can be imported from states package."""
        from bot.states import PracticeStates as ImportedStates

        assert ImportedStates is PracticeStates
