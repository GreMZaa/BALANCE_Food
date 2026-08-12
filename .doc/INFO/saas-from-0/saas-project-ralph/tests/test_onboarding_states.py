"""Tests for OnboardingStates FSM."""

from aiogram.fsm.state import StatesGroup

from bot.states.onboarding import OnboardingStates


class TestOnboardingStates:
    """Test suite for OnboardingStates."""

    def test_onboarding_states_is_states_group(self) -> None:
        """Test that OnboardingStates inherits from StatesGroup."""
        assert issubclass(OnboardingStates, StatesGroup)

    def test_waiting_specialty_state_exists(self) -> None:
        """Test that waiting_specialty state exists."""
        assert hasattr(OnboardingStates, "waiting_specialty")
        assert OnboardingStates.waiting_specialty is not None

    def test_waiting_grade_state_exists(self) -> None:
        """Test that waiting_grade state exists."""
        assert hasattr(OnboardingStates, "waiting_grade")
        assert OnboardingStates.waiting_grade is not None

    def test_waiting_tech_stack_state_exists(self) -> None:
        """Test that waiting_tech_stack state exists."""
        assert hasattr(OnboardingStates, "waiting_tech_stack")
        assert OnboardingStates.waiting_tech_stack is not None

    def test_waiting_focus_areas_state_exists(self) -> None:
        """Test that waiting_focus_areas state exists."""
        assert hasattr(OnboardingStates, "waiting_focus_areas")
        assert OnboardingStates.waiting_focus_areas is not None

    def test_waiting_specialty_state_name(self) -> None:
        """Test that waiting_specialty state has correct state name."""
        # State name format: GroupName:state_name
        assert "waiting_specialty" in OnboardingStates.waiting_specialty.state

    def test_waiting_grade_state_name(self) -> None:
        """Test that waiting_grade state has correct state name."""
        assert "waiting_grade" in OnboardingStates.waiting_grade.state

    def test_waiting_tech_stack_state_name(self) -> None:
        """Test that waiting_tech_stack state has correct state name."""
        assert "waiting_tech_stack" in OnboardingStates.waiting_tech_stack.state

    def test_waiting_focus_areas_state_name(self) -> None:
        """Test that waiting_focus_areas state has correct state name."""
        assert "waiting_focus_areas" in OnboardingStates.waiting_focus_areas.state

    def test_states_have_correct_group(self) -> None:
        """Test that all states belong to OnboardingStates group."""
        assert "OnboardingStates" in OnboardingStates.waiting_specialty.state
        assert "OnboardingStates" in OnboardingStates.waiting_grade.state
        assert "OnboardingStates" in OnboardingStates.waiting_tech_stack.state
        assert "OnboardingStates" in OnboardingStates.waiting_focus_areas.state

    def test_all_states_count(self) -> None:
        """Test that there are exactly 4 states in OnboardingStates."""
        # Get all states from the group
        states = OnboardingStates.__states__
        assert len(states) == 4

    def test_import_from_states_package(self) -> None:
        """Test that OnboardingStates can be imported from states package."""
        from bot.states import OnboardingStates as ImportedStates

        assert ImportedStates is OnboardingStates
