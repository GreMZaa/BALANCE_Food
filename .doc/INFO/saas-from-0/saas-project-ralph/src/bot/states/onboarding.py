"""FSM states for user onboarding flow."""

from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """States for the onboarding conversation flow.

    The onboarding flow consists of the following steps:
    1. waiting_specialty - User selects their specialty (Backend only in MVP)
    2. waiting_grade - User selects their experience level (Junior/Middle/Senior)
    3. waiting_tech_stack - User selects technologies they work with (multi-select)
    4. waiting_focus_areas - User selects interview focus areas (multi-select)

    After completing all steps, the user profile is created and FSM is cleared.
    """

    waiting_specialty = State()
    waiting_grade = State()
    waiting_tech_stack = State()
    waiting_focus_areas = State()
