"""Tests for practice command handler."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.domain.entities.question import Evaluation, Question
from bot.domain.entities.user import User
from bot.handlers.practice import (
    CATEGORY_DISPLAY_LABELS,
    _format_feedback_message,
    _format_question_message,
    _get_difficulty_label,
    cmd_practice,
    process_next_question_callback,
    process_text_answer,
    router,
)
from bot.keyboards.practice import NextQuestionCallback, get_next_question_keyboard
from bot.states.practice import PracticeStates


@pytest.fixture
def mock_telegram_user():
    """Create a mock Telegram user."""
    user = MagicMock()
    user.id = 123456789
    user.username = "testuser"
    user.first_name = "Test"
    user.last_name = "User"
    return user


@pytest.fixture
def mock_message(mock_telegram_user):
    """Create a mock Telegram message."""
    message = AsyncMock()
    message.from_user = mock_telegram_user
    message.chat = MagicMock()
    message.chat.id = 123456789
    message.answer = AsyncMock()
    message.bot = AsyncMock()
    message.bot.send_chat_action = AsyncMock()
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
def sample_user():
    """Create a sample User domain model."""
    return User(
        id=uuid4(),
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
    )


@pytest.fixture
def sample_profile(sample_user):
    """Create a sample UserProfile domain model."""
    return UserProfile(
        id=uuid4(),
        user_id=sample_user.id,
        specialty=Specialty.BACKEND,
        grade=Grade.MIDDLE,
        tech_stack=["Python", "Go"],
        focus_areas=[Category.ALGORITHMS, Category.DATABASES],
        current_difficulty=5,
    )


@pytest.fixture
def sample_question():
    """Create a sample Question."""
    return Question(
        text="Объясните разницу между процессом и потоком в операционных системах.",
        category=Category.ALGORITHMS,
        difficulty=5,
    )


class TestPracticeRouter:
    """Tests for practice router configuration."""

    def test_router_has_correct_name(self):
        """Test that router has correct name."""
        assert router.name == "practice"

    def test_router_has_message_handler(self):
        """Test that router has registered message handler."""
        assert len(router.message.handlers) > 0


class TestGetDifficultyLabel:
    """Tests for _get_difficulty_label function."""

    def test_easy_difficulty(self):
        """Test label for easy difficulty (1-3)."""
        assert "🟢" in _get_difficulty_label(1)
        assert "легко" in _get_difficulty_label(1)
        assert "🟢" in _get_difficulty_label(3)
        assert "легко" in _get_difficulty_label(3)

    def test_medium_difficulty(self):
        """Test label for medium difficulty (4-6)."""
        assert "🟡" in _get_difficulty_label(4)
        assert "средне" in _get_difficulty_label(4)
        assert "🟡" in _get_difficulty_label(6)
        assert "средне" in _get_difficulty_label(6)

    def test_hard_difficulty(self):
        """Test label for hard difficulty (7-10)."""
        assert "🔴" in _get_difficulty_label(7)
        assert "сложно" in _get_difficulty_label(7)
        assert "🔴" in _get_difficulty_label(10)
        assert "сложно" in _get_difficulty_label(10)

    def test_difficulty_number_included(self):
        """Test that difficulty number is included in label."""
        assert "5/10" in _get_difficulty_label(5)
        assert "8/10" in _get_difficulty_label(8)


class TestFormatQuestionMessage:
    """Tests for _format_question_message function."""

    def test_format_includes_category(self, sample_question):
        """Test that formatted message includes category."""
        result = _format_question_message(sample_question)
        expected_category = CATEGORY_DISPLAY_LABELS[sample_question.category]
        assert expected_category in result

    def test_format_includes_difficulty(self, sample_question):
        """Test that formatted message includes difficulty."""
        result = _format_question_message(sample_question)
        assert "5/10" in result

    def test_format_includes_question_text(self, sample_question):
        """Test that formatted message includes question text."""
        result = _format_question_message(sample_question)
        assert sample_question.text in result

    def test_format_includes_instructions(self, sample_question):
        """Test that formatted message includes answer instructions."""
        result = _format_question_message(sample_question)
        assert "текст" in result.lower() or "голосов" in result.lower()

    def test_format_includes_html_tags(self, sample_question):
        """Test that formatted message uses HTML formatting."""
        result = _format_question_message(sample_question)
        assert "<b>" in result
        assert "</b>" in result


class TestCategoryDisplayLabels:
    """Tests for CATEGORY_DISPLAY_LABELS constant."""

    def test_all_categories_have_labels(self):
        """Test that all Category enum values have display labels."""
        for category in Category:
            assert category in CATEGORY_DISPLAY_LABELS

    def test_labels_have_emoji(self):
        """Test that labels have emoji prefixes."""
        for label in CATEGORY_DISPLAY_LABELS.values():
            # Check if label starts with an emoji (non-ASCII)
            assert any(ord(c) > 127 for c in label[:2])


class TestCmdPractice:
    """Tests for cmd_practice handler."""

    async def test_cmd_practice_no_from_user(self, mock_state):
        """Test that handler returns early when from_user is None."""
        message = AsyncMock()
        message.from_user = None
        message.answer = AsyncMock()

        await cmd_practice(message, mock_state)

        message.answer.assert_not_called()

    async def test_cmd_practice_user_not_found(self, mock_message, mock_state):
        """Test that handler prompts /start when user not available."""
        await cmd_practice(mock_message, mock_state, user=None)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "/start" in call_args

    async def test_cmd_practice_no_profile(
        self, mock_message, mock_state, sample_user
    ):
        """Test that handler prompts onboarding when user has no profile."""
        with patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls:
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "/start" in call_args or "профил" in call_args.lower()

    async def test_cmd_practice_generates_question(
        self, mock_message, mock_state, sample_user, sample_profile, sample_question
    ):
        """Test that handler generates and sends question for user with profile."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_last_n_by_user = AsyncMock(return_value=[])
            mock_session_repo_cls.return_value = mock_session_repo

            mock_generate.return_value = sample_question

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_generate.assert_called_once_with(sample_profile, None)
            mock_message.answer.assert_called_once()

            # Check that question text is in the response
            call_args = mock_message.answer.call_args[0][0]
            assert sample_question.text in call_args

    async def test_cmd_practice_shows_typing(
        self, mock_message, mock_state, sample_user, sample_profile, sample_question
    ):
        """Test that handler shows typing indicator while generating."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.return_value = sample_question

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_message.bot.send_chat_action.assert_called_once_with(
                chat_id=mock_message.chat.id, action="typing"
            )

    async def test_cmd_practice_sets_fsm_state(
        self, mock_message, mock_state, sample_user, sample_profile, sample_question
    ):
        """Test that handler sets FSM state to waiting_answer."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.return_value = sample_question

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_state.set_state.assert_called_once_with(PracticeStates.waiting_answer)

    async def test_cmd_practice_stores_question_in_state(
        self, mock_message, mock_state, sample_user, sample_profile, sample_question
    ):
        """Test that handler stores question data in FSM state."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.return_value = sample_question

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_state.update_data.assert_called_once()
            call_kwargs = mock_state.update_data.call_args[1]
            assert call_kwargs["question_text"] == sample_question.text
            assert call_kwargs["question_category"] == sample_question.category.value
            assert call_kwargs["question_difficulty"] == sample_question.difficulty

    async def test_cmd_practice_handles_generation_error(
        self, mock_message, mock_state, sample_user, sample_profile
    ):
        """Test that handler handles question generation errors gracefully."""
        from bot.services.question_service import QuestionGenerationError

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.side_effect = QuestionGenerationError("API error")

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower()
            assert "/practice" in call_args

    async def test_cmd_practice_handles_parse_error(
        self, mock_message, mock_state, sample_user, sample_profile
    ):
        """Test that handler handles question parse errors gracefully."""
        from bot.services.question_service import QuestionParseError

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.side_effect = QuestionParseError("Parse error")

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower()

    async def test_cmd_practice_handles_unexpected_error(
        self, mock_message, mock_state, sample_user, sample_profile
    ):
        """Test that handler handles unexpected errors gracefully."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.side_effect = RuntimeError("Unexpected error")

            await cmd_practice(mock_message, mock_state, user=sample_user)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower()


@pytest.fixture
def sample_evaluation():
    """Create a sample Evaluation for testing."""
    return Evaluation(
        score=7,
        strengths=["Хорошее понимание основ", "Правильная структура ответа"],
        improvements=["Стоит добавить примеры", "Упомянуть edge cases"],
        reference_answer="Процесс — это изолированная единица выполнения с собственным адресным пространством.",
    )


class TestFormatFeedbackMessage:
    """Tests for _format_feedback_message function."""

    def test_format_includes_score(self, sample_evaluation):
        """Test that feedback includes score."""
        result = _format_feedback_message(sample_evaluation, questions_today=1)
        assert "7/10" in result

    def test_format_includes_strengths(self, sample_evaluation):
        """Test that feedback includes strengths."""
        result = _format_feedback_message(sample_evaluation, questions_today=1)
        assert "Хорошее понимание основ" in result
        assert "Правильная структура ответа" in result

    def test_format_includes_improvements(self, sample_evaluation):
        """Test that feedback includes improvements."""
        result = _format_feedback_message(sample_evaluation, questions_today=1)
        assert "Стоит добавить примеры" in result
        assert "Упомянуть edge cases" in result

    def test_format_includes_reference_answer(self, sample_evaluation):
        """Test that feedback includes reference answer."""
        result = _format_feedback_message(sample_evaluation, questions_today=1)
        assert "Процесс — это изолированная единица" in result

    def test_format_includes_daily_progress(self, sample_evaluation):
        """Test that feedback includes daily progress."""
        result = _format_feedback_message(sample_evaluation, questions_today=3)
        assert "3/5" in result
        assert "ещё 2" in result

    def test_format_includes_daily_goal_completed(self, sample_evaluation):
        """Test that feedback shows completed daily goal."""
        result = _format_feedback_message(sample_evaluation, questions_today=5)
        assert "5/5" in result
        assert "выполнена" in result.lower()

    def test_format_uses_html_tags(self, sample_evaluation):
        """Test that feedback uses HTML formatting."""
        result = _format_feedback_message(sample_evaluation, questions_today=1)
        assert "<b>" in result
        assert "</b>" in result

    def test_format_low_score_indicator(self):
        """Test that low score has red indicator."""
        evaluation = Evaluation(
            score=2,
            strengths=[],
            improvements=["Need more work"],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        assert "🔴" in result
        assert "Нужно поработать" in result

    def test_format_medium_score_indicator(self):
        """Test that medium score has orange indicator."""
        evaluation = Evaluation(
            score=5,
            strengths=["Good"],
            improvements=["Better"],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        assert "🟠" in result
        assert "есть куда расти" in result

    def test_format_good_score_indicator(self):
        """Test that good score has yellow indicator."""
        evaluation = Evaluation(
            score=7,
            strengths=["Great"],
            improvements=[],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        assert "🟡" in result
        assert "Хорошо!" in result

    def test_format_excellent_score_indicator(self):
        """Test that excellent score has green indicator."""
        evaluation = Evaluation(
            score=9,
            strengths=["Excellent"],
            improvements=[],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        assert "🟢" in result
        assert "Отлично!" in result

    def test_format_perfect_score_indicator(self):
        """Test that perfect score has star indicator."""
        evaluation = Evaluation(
            score=10,
            strengths=["Perfect"],
            improvements=[],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        assert "⭐" in result
        assert "Превосходно!" in result

    def test_format_empty_strengths(self):
        """Test formatting when strengths are empty."""
        evaluation = Evaluation(
            score=3,
            strengths=[],
            improvements=["Need more practice"],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        # Should not crash, strengths section should be omitted
        assert "Сильные стороны" not in result

    def test_format_empty_improvements(self):
        """Test formatting when improvements are empty."""
        evaluation = Evaluation(
            score=9,
            strengths=["Great answer"],
            improvements=[],
            reference_answer="Better answer here",
        )
        result = _format_feedback_message(evaluation, questions_today=1)
        # Should not crash, improvements section should be omitted
        assert "Что можно улучшить" not in result

    def test_format_custom_daily_goal(self, sample_evaluation):
        """Test that custom daily goal is respected."""
        result = _format_feedback_message(
            sample_evaluation, questions_today=8, daily_goal=10
        )
        assert "8/10" in result
        assert "ещё 2" in result


class TestPracticeKeyboards:
    """Tests for practice keyboards."""

    def test_next_question_keyboard_has_button(self):
        """Test that keyboard has the next question button."""
        keyboard = get_next_question_keyboard()
        assert keyboard.inline_keyboard
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 1

    def test_next_question_keyboard_button_text(self):
        """Test that button has correct text."""
        keyboard = get_next_question_keyboard()
        button = keyboard.inline_keyboard[0][0]
        assert "Следующий вопрос" in button.text

    def test_next_question_callback_data(self):
        """Test that callback data is correct."""
        callback = NextQuestionCallback(action="next")
        assert callback.action == "next"
        assert callback.pack().startswith("practice:")


class TestProcessTextAnswer:
    """Tests for process_text_answer handler."""

    async def test_process_answer_no_from_user(self, mock_state):
        """Test handler returns early when from_user is None."""
        message = AsyncMock()
        message.from_user = None
        message.text = "Some answer"
        message.answer = AsyncMock()

        await process_text_answer(message, mock_state)

        message.answer.assert_not_called()

    async def test_process_answer_no_text(self, mock_telegram_user, mock_state):
        """Test handler returns early when text is None."""
        message = AsyncMock()
        message.from_user = mock_telegram_user
        message.text = None
        message.answer = AsyncMock()

        await process_text_answer(message, mock_state)

        message.answer.assert_not_called()

    async def test_process_answer_missing_state_data(
        self, mock_message, mock_state
    ):
        """Test handler prompts new session when state data is missing."""
        mock_message.text = "My answer"
        mock_state.get_data.return_value = {}

        await process_text_answer(mock_message, mock_state)

        mock_message.answer.assert_called_once()
        call_args = mock_message.answer.call_args[0][0]
        assert "/practice" in call_args
        mock_state.clear.assert_called_once()

    async def test_process_answer_profile_not_found(
        self, mock_message, mock_state, sample_user
    ):
        """Test handler prompts setup when profile not found."""
        mock_message.text = "My answer"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_user.id),
        }

        with patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls:
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await process_text_answer(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "/start" in call_args
            mock_state.clear.assert_called_once()

    async def test_process_answer_shows_typing(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler shows typing indicator during evaluation."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_message.bot.send_chat_action.assert_called_once_with(
                chat_id=mock_message.chat.id, action="typing"
            )

    async def test_process_answer_sets_processing_state(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler sets FSM state to processing_answer."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_state.set_state.assert_called_once_with(PracticeStates.processing_answer)

    async def test_process_answer_evaluates_answer(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler calls evaluate_answer with correct arguments."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_evaluate.assert_called_once_with(
                question="Test question",
                answer="My answer about processes",
                grade=sample_profile.grade,
            )

    async def test_process_answer_sends_feedback(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler sends formatted feedback to user."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            # Check that feedback contains score
            assert "7/10" in call_args
            # Check that feedback contains reference answer
            assert sample_evaluation.reference_answer in call_args
            # Check that reply_markup is provided (next question button)
            assert mock_message.answer.call_args[1].get("reply_markup") is not None

    async def test_process_answer_clears_state(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler clears FSM state after evaluation."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_state.clear.assert_called_once()

    async def test_process_answer_handles_evaluation_error(
        self, mock_message, mock_state, sample_profile
    ):
        """Test handler handles evaluation errors gracefully."""
        from bot.services.evaluation_service import EvaluationError

        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_evaluate.side_effect = EvaluationError("API error")

            await process_text_answer(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_answer_handles_parse_error(
        self, mock_message, mock_state, sample_profile
    ):
        """Test handler handles evaluation parse errors gracefully."""
        from bot.services.evaluation_service import EvaluationParseError

        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_evaluate.side_effect = EvaluationParseError("Parse error")

            await process_text_answer(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_answer_handles_unexpected_error(
        self, mock_message, mock_state, sample_profile
    ):
        """Test handler handles unexpected errors gracefully."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_evaluate.side_effect = RuntimeError("Unexpected error")

            await process_text_answer(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_answer_strips_whitespace(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler strips whitespace from answer."""
        mock_message.text = "  My answer with spaces  "
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_evaluate.assert_called_once()
            call_args = mock_evaluate.call_args
            assert call_args[1]["answer"] == "My answer with spaces"

    async def test_process_answer_includes_daily_progress(
        self, mock_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler includes daily progress in feedback."""
        mock_message.text = "My answer about processes"
        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            # Session is saved first, then count is retrieved (already includes current)
            mock_session_repo.create = AsyncMock(return_value=MagicMock())
            mock_session_repo.get_today_count = AsyncMock(return_value=3)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_evaluate.return_value = sample_evaluation

            await process_text_answer(mock_message, mock_state)

            mock_message.answer.assert_called_once()
            call_args = mock_message.answer.call_args[0][0]
            # Should show progress 3/5 (count already includes current session)
            assert "3/5" in call_args


class TestProcessNextQuestionCallback:
    """Tests for process_next_question_callback handler."""

    @pytest.fixture
    def mock_callback(self, mock_telegram_user):
        """Create a mock callback query."""
        callback = AsyncMock()
        callback.from_user = mock_telegram_user
        callback.message = AsyncMock()
        callback.message.chat = MagicMock()
        callback.message.chat.id = 123456789
        callback.message.answer = AsyncMock()
        callback.message.bot = AsyncMock()
        callback.message.bot.send_chat_action = AsyncMock()
        callback.answer = AsyncMock()
        return callback

    async def test_callback_no_message(self, mock_state):
        """Test that handler handles missing message gracefully."""
        callback = AsyncMock()
        callback.message = None
        callback.answer = AsyncMock()

        await process_next_question_callback(callback, mock_state)

        callback.answer.assert_called_once()

    async def test_callback_no_from_user(self, mock_state):
        """Test that handler handles missing from_user gracefully."""
        callback = AsyncMock()
        callback.message = AsyncMock()
        callback.from_user = None
        callback.answer = AsyncMock()

        await process_next_question_callback(callback, mock_state)

        callback.answer.assert_called_once()
        callback.message.answer.assert_not_called()

    async def test_callback_user_not_found(self, mock_callback, mock_state):
        """Test that handler prompts /start when user not available."""
        await process_next_question_callback(mock_callback, mock_state, user=None)

        mock_callback.answer.assert_called_once()
        mock_callback.message.answer.assert_called_once()
        call_args = mock_callback.message.answer.call_args[0][0]
        assert "/start" in call_args

    async def test_callback_no_profile(self, mock_callback, mock_state, sample_user):
        """Test that handler prompts setup when user has no profile."""
        with patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls:
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await process_next_question_callback(mock_callback, mock_state, user=sample_user)

            mock_callback.answer.assert_called_once()
            mock_callback.message.answer.assert_called_once()
            call_args = mock_callback.message.answer.call_args[0][0]
            assert "/start" in call_args or "профил" in call_args.lower()

    async def test_callback_generates_question(
        self, mock_callback, mock_state, sample_user, sample_profile, sample_question
    ):
        """Test that callback generates and sends new question."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.get_last_n_by_user = AsyncMock(return_value=[])
            mock_session_repo_cls.return_value = mock_session_repo

            mock_generate.return_value = sample_question

            await process_next_question_callback(mock_callback, mock_state, user=sample_user)

            mock_generate.assert_called_once_with(sample_profile, None)
            mock_callback.message.answer.assert_called_once()
            call_args = mock_callback.message.answer.call_args[0][0]
            assert sample_question.text in call_args

    async def test_callback_sets_fsm_state(
        self, mock_callback, mock_state, sample_user, sample_profile, sample_question
    ):
        """Test that callback sets FSM state to waiting_answer."""
        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.generate_question") as mock_generate,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_generate.return_value = sample_question

            await process_next_question_callback(mock_callback, mock_state, user=sample_user)

            mock_state.set_state.assert_called_once_with(PracticeStates.waiting_answer)


class TestProcessVoiceAnswer:
    """Tests for process_voice_answer handler."""

    @pytest.fixture
    def mock_voice_message(self, mock_telegram_user):
        """Create a mock Telegram message with voice."""
        message = AsyncMock()
        message.from_user = mock_telegram_user
        message.chat = MagicMock()
        message.chat.id = 123456789
        message.answer = AsyncMock()
        message.bot = AsyncMock()
        message.bot.send_chat_action = AsyncMock()
        message.bot.get_file = AsyncMock()
        message.bot.download_file = AsyncMock()

        # Voice attributes
        message.voice = MagicMock()
        message.voice.file_id = "test_file_id_123"
        message.voice.duration = 15
        message.voice.file_size = 25000

        return message

    async def test_process_voice_no_from_user(self, mock_state):
        """Test handler returns early when from_user is None."""
        from bot.handlers.practice import process_voice_answer

        message = AsyncMock()
        message.from_user = None
        message.voice = MagicMock()
        message.answer = AsyncMock()

        await process_voice_answer(message, mock_state)

        message.answer.assert_not_called()

    async def test_process_voice_no_voice(self, mock_telegram_user, mock_state):
        """Test handler returns early when voice is None."""
        from bot.handlers.practice import process_voice_answer

        message = AsyncMock()
        message.from_user = mock_telegram_user
        message.voice = None
        message.answer = AsyncMock()

        await process_voice_answer(message, mock_state)

        message.answer.assert_not_called()

    async def test_process_voice_missing_state_data(
        self, mock_voice_message, mock_state
    ):
        """Test handler prompts new session when state data is missing."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {}

        await process_voice_answer(mock_voice_message, mock_state)

        mock_voice_message.answer.assert_called_once()
        call_args = mock_voice_message.answer.call_args[0][0]
        assert "/practice" in call_args
        mock_state.clear.assert_called_once()

    async def test_process_voice_profile_not_found(
        self, mock_voice_message, mock_state, sample_user
    ):
        """Test handler prompts setup when profile not found."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_user.id),
        }

        with patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls:
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=None)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await process_voice_answer(mock_voice_message, mock_state)

            mock_voice_message.answer.assert_called_once()
            call_args = mock_voice_message.answer.call_args[0][0]
            assert "/start" in call_args
            mock_state.clear.assert_called_once()

    async def test_process_voice_download_and_transcribe(
        self, mock_voice_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler downloads voice file and transcribes it."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        # Mock file download
        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.create = AsyncMock(return_value=MagicMock())
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            # Setup temp file mock
            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.return_value = "Транскрибированный ответ пользователя"
            mock_evaluate.return_value = sample_evaluation

            await process_voice_answer(mock_voice_message, mock_state)

            # Verify file was downloaded
            mock_voice_message.bot.get_file.assert_called_once_with("test_file_id_123")
            mock_voice_message.bot.download_file.assert_called_once()

            # Verify transcription was called
            mock_transcribe.assert_called_once()

            # Verify evaluation was called with transcribed text
            mock_evaluate.assert_called_once()
            call_kwargs = mock_evaluate.call_args[1]
            assert call_kwargs["answer"] == "Транскрибированный ответ пользователя"

    async def test_process_voice_shows_transcription(
        self, mock_voice_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler shows transcribed text to user."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        # Mock file download
        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.create = AsyncMock(return_value=MagicMock())
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.return_value = "Мой голосовой ответ"
            mock_evaluate.return_value = sample_evaluation

            await process_voice_answer(mock_voice_message, mock_state)

            # Should have 2 calls: transcription message and feedback message
            assert mock_voice_message.answer.call_count == 2
            first_call = mock_voice_message.answer.call_args_list[0][0][0]
            assert "Мой голосовой ответ" in first_call
            assert "Распознанный текст" in first_call

    async def test_process_voice_handles_transcription_error(
        self, mock_voice_message, mock_state, sample_profile
    ):
        """Test handler handles transcription errors gracefully."""
        from bot.handlers.practice import process_voice_answer
        from bot.services.transcription_service import TranscriptionError

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.side_effect = TranscriptionError("API error")

            await process_voice_answer(mock_voice_message, mock_state)

            mock_voice_message.answer.assert_called_once()
            call_args = mock_voice_message.answer.call_args[0][0]
            assert "ошибка" in call_args.lower() or "распознав" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_voice_handles_invalid_audio(
        self, mock_voice_message, mock_state, sample_profile
    ):
        """Test handler handles invalid audio errors gracefully."""
        from bot.handlers.practice import process_voice_answer
        from bot.services.transcription_service import InvalidAudioError

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.side_effect = InvalidAudioError("Invalid audio")

            await process_voice_answer(mock_voice_message, mock_state)

            mock_voice_message.answer.assert_called_once()
            call_args = mock_voice_message.answer.call_args[0][0]
            assert "распознать" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_voice_handles_empty_transcription(
        self, mock_voice_message, mock_state, sample_profile
    ):
        """Test handler handles empty transcription result."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.return_value = "   "  # Empty/whitespace

            await process_voice_answer(mock_voice_message, mock_state)

            mock_voice_message.answer.assert_called_once()
            call_args = mock_voice_message.answer.call_args[0][0]
            assert "распознать" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_voice_handles_file_download_error(
        self, mock_voice_message, mock_state, sample_profile
    ):
        """Test handler handles file download errors gracefully."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        # File path is None - download failed
        mock_file = MagicMock()
        mock_file.file_path = None
        mock_voice_message.bot.get_file.return_value = mock_file

        with patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls:
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            await process_voice_answer(mock_voice_message, mock_state)

            mock_voice_message.answer.assert_called_once()
            call_args = mock_voice_message.answer.call_args[0][0]
            assert "загрузить" in call_args.lower() or "голосовое" in call_args.lower()
            mock_state.clear.assert_called_once()

    async def test_process_voice_saves_session_with_voice_type(
        self, mock_voice_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler saves session with VOICE answer type."""
        from bot.domain.entities.enums import AnswerType
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.create = AsyncMock(return_value=MagicMock())
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.return_value = "Голосовой ответ"
            mock_evaluate.return_value = sample_evaluation

            await process_voice_answer(mock_voice_message, mock_state)

            # Verify session was created
            mock_session_repo.create.assert_called_once()
            session_arg = mock_session_repo.create.call_args[0][0]
            assert session_arg.answer_type == AnswerType.VOICE

    async def test_process_voice_cleans_up_temp_file(
        self, mock_voice_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler cleans up temporary file after processing."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink") as mock_unlink,
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.create = AsyncMock(return_value=MagicMock())
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.return_value = "Голосовой ответ"
            mock_evaluate.return_value = sample_evaluation

            await process_voice_answer(mock_voice_message, mock_state)

            # Verify temp file was deleted
            mock_unlink.assert_called_once()

    async def test_process_voice_clears_state_on_success(
        self, mock_voice_message, mock_state, sample_profile, sample_evaluation
    ):
        """Test handler clears FSM state after successful processing."""
        from bot.handlers.practice import process_voice_answer

        mock_state.get_data.return_value = {
            "question_text": "Test question",
            "user_id": str(sample_profile.user_id),
        }

        mock_file = MagicMock()
        mock_file.file_path = "voice/file_123.ogg"
        mock_voice_message.bot.get_file.return_value = mock_file

        with (
            patch("bot.handlers.practice.ProfileRepository") as mock_profile_repo_cls,
            patch("bot.handlers.practice.SessionRepository") as mock_session_repo_cls,
            patch("bot.handlers.practice.transcribe") as mock_transcribe,
            patch("bot.handlers.practice.evaluate_answer") as mock_evaluate,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink"),
            patch("pathlib.Path.exists") as mock_exists,
            patch("pathlib.Path.stat") as mock_stat,
        ):
            mock_profile_repo = MagicMock()
            mock_profile_repo.get_by_user_id = AsyncMock(return_value=sample_profile)
            mock_profile_repo_cls.return_value = mock_profile_repo

            mock_session_repo = MagicMock()
            mock_session_repo.create = AsyncMock(return_value=MagicMock())
            mock_session_repo.get_today_count = AsyncMock(return_value=2)
            mock_session_repo_cls.return_value = mock_session_repo

            mock_temp = MagicMock()
            mock_temp.name = "/tmp/voice_123.ogg"
            mock_tempfile.return_value.__enter__ = MagicMock(return_value=mock_temp)
            mock_tempfile.return_value.__exit__ = MagicMock(return_value=False)

            mock_exists.return_value = True
            mock_stat.return_value.st_size = 25000

            mock_transcribe.return_value = "Голосовой ответ"
            mock_evaluate.return_value = sample_evaluation

            await process_voice_answer(mock_voice_message, mock_state)

            mock_state.clear.assert_called_once()
