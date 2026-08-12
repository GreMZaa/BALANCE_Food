"""Tests for onboarding keyboards."""

from aiogram.types import InlineKeyboardMarkup

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.keyboards.onboarding import (
    FOCUS_AREAS_LABELS,
    GRADE_LABELS,
    SPECIALTY_LABELS,
    TECH_STACK_OPTIONS,
    FocusAreasCallback,
    GradeCallback,
    SpecialtyCallback,
    TechStackCallback,
    get_focus_areas_keyboard,
    get_grade_keyboard,
    get_specialty_keyboard,
    get_tech_stack_keyboard,
)


class TestCallbackDataFactories:
    """Tests for callback data factories."""

    def test_specialty_callback_pack_unpack(self) -> None:
        """Test SpecialtyCallback serialization."""
        callback = SpecialtyCallback(value="backend")
        packed = callback.pack()
        assert packed == "specialty:backend"

        unpacked = SpecialtyCallback.unpack(packed)
        assert unpacked.value == "backend"

    def test_grade_callback_pack_unpack(self) -> None:
        """Test GradeCallback serialization."""
        callback = GradeCallback(value="junior")
        packed = callback.pack()
        assert packed == "grade:junior"

        unpacked = GradeCallback.unpack(packed)
        assert unpacked.value == "junior"

    def test_tech_stack_callback_toggle(self) -> None:
        """Test TechStackCallback for toggle action."""
        callback = TechStackCallback(action="toggle", value="Python")
        packed = callback.pack()
        assert "tech:" in packed
        assert "toggle" in packed
        assert "Python" in packed

        unpacked = TechStackCallback.unpack(packed)
        assert unpacked.action == "toggle"
        assert unpacked.value == "Python"

    def test_tech_stack_callback_done(self) -> None:
        """Test TechStackCallback for done action."""
        callback = TechStackCallback(action="done", value="")
        packed = callback.pack()

        unpacked = TechStackCallback.unpack(packed)
        assert unpacked.action == "done"
        assert unpacked.value == ""

    def test_focus_areas_callback_toggle(self) -> None:
        """Test FocusAreasCallback for toggle action."""
        callback = FocusAreasCallback(action="toggle", value="algorithms")
        packed = callback.pack()

        unpacked = FocusAreasCallback.unpack(packed)
        assert unpacked.action == "toggle"
        assert unpacked.value == "algorithms"

    def test_focus_areas_callback_done(self) -> None:
        """Test FocusAreasCallback for done action."""
        callback = FocusAreasCallback(action="done", value="")
        packed = callback.pack()

        unpacked = FocusAreasCallback.unpack(packed)
        assert unpacked.action == "done"
        assert unpacked.value == ""


class TestLabelsAndOptions:
    """Tests for labels and options dictionaries."""

    def test_specialty_labels_only_backend_in_mvp(self) -> None:
        """Test that only Backend is available in MVP."""
        assert len(SPECIALTY_LABELS) == 1
        assert Specialty.BACKEND in SPECIALTY_LABELS
        assert "Backend" in SPECIALTY_LABELS[Specialty.BACKEND]

    def test_grade_labels_has_all_grades(self) -> None:
        """Test that all grades are present."""
        assert len(GRADE_LABELS) == 3
        assert Grade.JUNIOR in GRADE_LABELS
        assert Grade.MIDDLE in GRADE_LABELS
        assert Grade.SENIOR in GRADE_LABELS

    def test_tech_stack_options_not_empty(self) -> None:
        """Test that tech stack options are defined."""
        assert len(TECH_STACK_OPTIONS) > 0
        assert "Python" in TECH_STACK_OPTIONS
        assert "Java" in TECH_STACK_OPTIONS
        assert "Go" in TECH_STACK_OPTIONS
        assert "Node.js" in TECH_STACK_OPTIONS

    def test_focus_areas_labels_has_all_categories(self) -> None:
        """Test that all categories are present in focus areas."""
        assert len(FOCUS_AREAS_LABELS) == len(Category)
        for category in Category:
            assert category in FOCUS_AREAS_LABELS


class TestSpecialtyKeyboard:
    """Tests for specialty selection keyboard."""

    def test_returns_inline_keyboard(self) -> None:
        """Test that function returns InlineKeyboardMarkup."""
        keyboard = get_specialty_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_correct_number_of_buttons(self) -> None:
        """Test that keyboard has correct number of buttons (1 in MVP)."""
        keyboard = get_specialty_keyboard()
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == 1  # Only Backend in MVP

    def test_button_has_correct_callback_data(self) -> None:
        """Test that button has valid callback data."""
        keyboard = get_specialty_keyboard()
        button = keyboard.inline_keyboard[0][0]

        assert button.callback_data is not None
        callback = SpecialtyCallback.unpack(button.callback_data)
        assert callback.value == Specialty.BACKEND.value


class TestGradeKeyboard:
    """Tests for grade selection keyboard."""

    def test_returns_inline_keyboard(self) -> None:
        """Test that function returns InlineKeyboardMarkup."""
        keyboard = get_grade_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_3_buttons(self) -> None:
        """Test that keyboard has exactly 3 buttons."""
        keyboard = get_grade_keyboard()
        total_buttons = sum(len(row) for row in keyboard.inline_keyboard)
        assert total_buttons == 3

    def test_buttons_have_correct_order(self) -> None:
        """Test that buttons are in correct order: Junior, Middle, Senior."""
        keyboard = get_grade_keyboard()

        # Assuming 1 button per row
        callbacks = []
        for row in keyboard.inline_keyboard:
            for button in row:
                assert button.callback_data is not None
                callback = GradeCallback.unpack(button.callback_data)
                callbacks.append(callback.value)

        assert callbacks == [Grade.JUNIOR.value, Grade.MIDDLE.value, Grade.SENIOR.value]

    def test_buttons_contain_grade_labels(self) -> None:
        """Test that buttons contain appropriate labels."""
        keyboard = get_grade_keyboard()
        texts = [button.text for row in keyboard.inline_keyboard for button in row]

        assert any("Junior" in text for text in texts)
        assert any("Middle" in text for text in texts)
        assert any("Senior" in text for text in texts)


class TestTechStackKeyboard:
    """Tests for tech stack multi-selection keyboard."""

    def test_returns_inline_keyboard(self) -> None:
        """Test that function returns InlineKeyboardMarkup."""
        keyboard = get_tech_stack_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_done_button(self) -> None:
        """Test that keyboard has a Done button."""
        keyboard = get_tech_stack_keyboard()
        last_row = keyboard.inline_keyboard[-1]
        assert len(last_row) == 1
        assert "Готово" in last_row[0].text

    def test_done_button_has_correct_callback(self) -> None:
        """Test that Done button has correct callback data."""
        keyboard = get_tech_stack_keyboard()
        done_button = keyboard.inline_keyboard[-1][0]

        assert done_button.callback_data is not None
        callback = TechStackCallback.unpack(done_button.callback_data)
        assert callback.action == "done"
        assert callback.value == ""

    def test_no_selection_shows_plain_text(self) -> None:
        """Test that unselected items show plain text."""
        keyboard = get_tech_stack_keyboard(selected=set())

        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                assert not button.text.startswith("✅")

    def test_selected_items_show_checkmark(self) -> None:
        """Test that selected items show checkmark."""
        selected = {"Python", "Go"}
        keyboard = get_tech_stack_keyboard(selected=selected)

        checked_texts = []
        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                if button.text.startswith("✅"):
                    checked_texts.append(button.text)

        assert len(checked_texts) == 2
        assert any("Python" in text for text in checked_texts)
        assert any("Go" in text for text in checked_texts)

    def test_toggle_callback_for_tech_options(self) -> None:
        """Test that tech options have toggle callback."""
        keyboard = get_tech_stack_keyboard()

        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                assert button.callback_data is not None
                callback = TechStackCallback.unpack(button.callback_data)
                assert callback.action == "toggle"
                assert callback.value in TECH_STACK_OPTIONS


class TestFocusAreasKeyboard:
    """Tests for focus areas multi-selection keyboard."""

    def test_returns_inline_keyboard(self) -> None:
        """Test that function returns InlineKeyboardMarkup."""
        keyboard = get_focus_areas_keyboard()
        assert isinstance(keyboard, InlineKeyboardMarkup)

    def test_has_done_button(self) -> None:
        """Test that keyboard has a Done button."""
        keyboard = get_focus_areas_keyboard()
        last_row = keyboard.inline_keyboard[-1]
        assert len(last_row) == 1
        assert "Готово" in last_row[0].text

    def test_done_button_has_correct_callback(self) -> None:
        """Test that Done button has correct callback data."""
        keyboard = get_focus_areas_keyboard()
        done_button = keyboard.inline_keyboard[-1][0]

        assert done_button.callback_data is not None
        callback = FocusAreasCallback.unpack(done_button.callback_data)
        assert callback.action == "done"
        assert callback.value == ""

    def test_no_selection_shows_plain_labels(self) -> None:
        """Test that unselected items show plain labels."""
        keyboard = get_focus_areas_keyboard(selected=set())

        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                assert not button.text.startswith("✅")

    def test_selected_items_show_checkmark(self) -> None:
        """Test that selected items show checkmark."""
        selected = {Category.ALGORITHMS, Category.DATABASES}
        keyboard = get_focus_areas_keyboard(selected=selected)

        checked_count = 0
        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                if button.text.startswith("✅"):
                    checked_count += 1

        assert checked_count == 2

    def test_toggle_callback_for_focus_options(self) -> None:
        """Test that focus options have toggle callback."""
        keyboard = get_focus_areas_keyboard()

        category_values = {c.value for c in Category}

        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                assert button.callback_data is not None
                callback = FocusAreasCallback.unpack(button.callback_data)
                assert callback.action == "toggle"
                assert callback.value in category_values

    def test_has_all_categories(self) -> None:
        """Test that keyboard has all category options."""
        keyboard = get_focus_areas_keyboard()

        found_values = set()
        for row in keyboard.inline_keyboard[:-1]:  # Exclude Done button
            for button in row:
                assert button.callback_data is not None
                callback = FocusAreasCallback.unpack(button.callback_data)
                found_values.add(callback.value)

        expected_values = {c.value for c in Category}
        assert found_values == expected_values
