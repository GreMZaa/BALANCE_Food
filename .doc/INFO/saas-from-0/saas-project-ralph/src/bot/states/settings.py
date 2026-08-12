"""FSM states for user settings editing flow."""

from aiogram.fsm.state import State, StatesGroup


class SettingsStates(StatesGroup):
    """States for the settings conversation flow.

    The settings flow allows users to edit their profile:
    1. editing_grade - User is changing their experience level
    2. editing_tech_stack - User is changing their tech stack (multi-select)
    3. editing_focus_areas - User is changing their focus areas (multi-select)
    """

    editing_grade = State()
    editing_tech_stack = State()
    editing_focus_areas = State()
