"""Tests for question generation service."""

import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from bot.domain.entities.enums import Category, Grade, Specialty
from bot.domain.entities.profile import UserProfile
from bot.domain.entities.question import Question
from bot.services.question_service import (
    CATEGORY_NAMES,
    GRADE_DESCRIPTIONS,
    QuestionGenerationError,
    QuestionParseError,
    _build_question_prompt,
    _parse_question_response,
    generate_question,
)


@pytest.fixture
def sample_profile() -> UserProfile:
    """Create a sample user profile for testing."""
    return UserProfile(
        id=uuid4(),
        user_id=uuid4(),
        specialty=Specialty.BACKEND,
        grade=Grade.MIDDLE,
        tech_stack=["Python", "PostgreSQL"],
        focus_areas=[Category.DATABASES, Category.ALGORITHMS],
        current_difficulty=5,
    )


@pytest.fixture
def junior_profile() -> UserProfile:
    """Create a junior profile for testing."""
    return UserProfile(
        id=uuid4(),
        user_id=uuid4(),
        specialty=Specialty.BACKEND,
        grade=Grade.JUNIOR,
        tech_stack=["Python"],
        focus_areas=[Category.LANGUAGE],
        current_difficulty=2,
    )


@pytest.fixture
def senior_profile() -> UserProfile:
    """Create a senior profile for testing."""
    return UserProfile(
        id=uuid4(),
        user_id=uuid4(),
        specialty=Specialty.BACKEND,
        grade=Grade.SENIOR,
        tech_stack=["Go", "Kubernetes"],
        focus_areas=[Category.SYSTEM_DESIGN, Category.MICROSERVICES],
        current_difficulty=8,
    )


@pytest.fixture
def empty_profile() -> UserProfile:
    """Create a profile with minimal data."""
    return UserProfile(
        id=uuid4(),
        user_id=uuid4(),
        specialty=Specialty.BACKEND,
        grade=Grade.MIDDLE,
        tech_stack=[],
        focus_areas=[],
        current_difficulty=5,
    )


class TestBuildQuestionPrompt:
    """Tests for _build_question_prompt function."""

    def test_prompt_contains_grade_description(self, sample_profile: UserProfile) -> None:
        """Prompt should include grade description."""
        prompt = _build_question_prompt(sample_profile)
        grade_desc = GRADE_DESCRIPTIONS[Grade.MIDDLE]
        assert grade_desc in prompt

    def test_prompt_contains_tech_stack(self, sample_profile: UserProfile) -> None:
        """Prompt should include tech stack."""
        prompt = _build_question_prompt(sample_profile)
        assert "Python" in prompt
        assert "PostgreSQL" in prompt

    def test_prompt_contains_difficulty(self, sample_profile: UserProfile) -> None:
        """Prompt should include difficulty level."""
        prompt = _build_question_prompt(sample_profile)
        assert "5/10" in prompt

    def test_prompt_for_empty_tech_stack(self, empty_profile: UserProfile) -> None:
        """Prompt should handle empty tech stack."""
        prompt = _build_question_prompt(empty_profile)
        assert "общие технологии" in prompt

    def test_prompt_requests_json_format(self, sample_profile: UserProfile) -> None:
        """Prompt should request JSON format."""
        prompt = _build_question_prompt(sample_profile)
        assert "JSON" in prompt
        assert '"text"' in prompt
        assert '"category"' in prompt
        assert '"difficulty"' in prompt

    def test_prompt_for_junior(self, junior_profile: UserProfile) -> None:
        """Prompt should have correct content for junior."""
        prompt = _build_question_prompt(junior_profile)
        assert GRADE_DESCRIPTIONS[Grade.JUNIOR] in prompt
        assert "2/10" in prompt

    def test_prompt_for_senior(self, senior_profile: UserProfile) -> None:
        """Prompt should have correct content for senior."""
        prompt = _build_question_prompt(senior_profile)
        assert GRADE_DESCRIPTIONS[Grade.SENIOR] in prompt
        assert "8/10" in prompt

    @patch("bot.services.question_service.random.choice")
    def test_prompt_uses_random_focus_area(
        self, mock_choice: AsyncMock, sample_profile: UserProfile
    ) -> None:
        """Prompt should use random category from focus_areas."""
        mock_choice.return_value = Category.DATABASES
        prompt = _build_question_prompt(sample_profile)
        assert CATEGORY_NAMES[Category.DATABASES] in prompt

    @patch("bot.services.question_service.random.choice")
    def test_prompt_uses_random_category_when_no_focus_areas(
        self, mock_choice: AsyncMock, empty_profile: UserProfile
    ) -> None:
        """Prompt should use random category when focus_areas is empty."""
        mock_choice.return_value = Category.LANGUAGE
        prompt = _build_question_prompt(empty_profile)
        assert CATEGORY_NAMES[Category.LANGUAGE] in prompt


class TestParseQuestionResponse:
    """Tests for _parse_question_response function."""

    def test_parse_valid_json(self) -> None:
        """Should parse valid JSON response."""
        response = json.dumps(
            {"text": "What is polymorphism?", "category": "language", "difficulty": 5}
        )
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.text == "What is polymorphism?"
        assert question.category == Category.LANGUAGE
        assert question.difficulty == 5

    def test_parse_json_with_markdown_code_block(self) -> None:
        """Should parse JSON wrapped in markdown code blocks."""
        response = """```json
{"text": "What is polymorphism?", "category": "language", "difficulty": 5}
```"""
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.text == "What is polymorphism?"

    def test_parse_json_with_plain_code_block(self) -> None:
        """Should parse JSON wrapped in plain code blocks."""
        response = """```
{"text": "What is polymorphism?", "category": "language", "difficulty": 5}
```"""
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.text == "What is polymorphism?"

    def test_parse_missing_category_defaults_to_language(self) -> None:
        """Should default to LANGUAGE when category is missing."""
        response = json.dumps({"text": "Question text", "difficulty": 5})
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.category == Category.LANGUAGE

    def test_parse_unknown_category_defaults_to_language(self) -> None:
        """Should default to LANGUAGE for unknown category."""
        response = json.dumps(
            {"text": "Question text", "category": "unknown_category", "difficulty": 5}
        )
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.category == Category.LANGUAGE

    def test_parse_missing_difficulty_uses_expected(self) -> None:
        """Should use expected difficulty when missing."""
        response = json.dumps({"text": "Question text", "category": "language"})
        question = _parse_question_response(response, expected_difficulty=7)
        assert question.difficulty == 7

    def test_parse_invalid_difficulty_uses_expected(self) -> None:
        """Should use expected difficulty when invalid."""
        response = json.dumps(
            {"text": "Question text", "category": "language", "difficulty": 15}
        )
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.difficulty == 5

    def test_parse_invalid_json_raises_error(self) -> None:
        """Should raise QuestionParseError for invalid JSON."""
        with pytest.raises(QuestionParseError, match="Invalid JSON"):
            _parse_question_response("not valid json", expected_difficulty=5)

    def test_parse_missing_text_raises_error(self) -> None:
        """Should raise QuestionParseError when text is missing."""
        response = json.dumps({"category": "language", "difficulty": 5})
        with pytest.raises(QuestionParseError, match="Missing 'text' field"):
            _parse_question_response(response, expected_difficulty=5)

    def test_parse_empty_text_raises_error(self) -> None:
        """Should raise QuestionParseError when text is empty."""
        response = json.dumps({"text": "", "category": "language", "difficulty": 5})
        with pytest.raises(QuestionParseError, match="Invalid or empty 'text' field"):
            _parse_question_response(response, expected_difficulty=5)

    def test_parse_whitespace_text_raises_error(self) -> None:
        """Should raise QuestionParseError when text is whitespace only."""
        response = json.dumps({"text": "   ", "category": "language", "difficulty": 5})
        with pytest.raises(QuestionParseError, match="Invalid or empty 'text' field"):
            _parse_question_response(response, expected_difficulty=5)

    def test_parse_strips_text_whitespace(self) -> None:
        """Should strip whitespace from text."""
        response = json.dumps(
            {"text": "  Question text  ", "category": "language", "difficulty": 5}
        )
        question = _parse_question_response(response, expected_difficulty=5)
        assert question.text == "Question text"

    def test_parse_all_valid_categories(self) -> None:
        """Should parse all valid categories correctly."""
        for category in Category:
            response = json.dumps(
                {"text": "Question", "category": category.value, "difficulty": 5}
            )
            question = _parse_question_response(response, expected_difficulty=5)
            assert question.category == category


class TestGenerateQuestion:
    """Tests for generate_question function."""

    @pytest.mark.asyncio
    async def test_generate_question_success(self, sample_profile: UserProfile) -> None:
        """Should generate question successfully."""
        mock_response = json.dumps(
            {
                "text": "Объясните, как работает индексирование в PostgreSQL?",
                "category": "databases",
                "difficulty": 5,
            }
        )

        with patch(
            "bot.services.question_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            question = await generate_question(sample_profile)

        assert isinstance(question, Question)
        assert question.text == "Объясните, как работает индексирование в PostgreSQL?"
        assert question.category == Category.DATABASES
        assert question.difficulty == 5

    @pytest.mark.asyncio
    async def test_generate_question_calls_openai_with_correct_params(
        self, sample_profile: UserProfile
    ) -> None:
        """Should call OpenAI API with correct parameters."""
        mock_response = json.dumps(
            {"text": "Test question", "category": "language", "difficulty": 5}
        )

        with patch(
            "bot.services.question_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_chat:
            await generate_question(sample_profile)

        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args.kwargs
        assert call_kwargs["temperature"] == 0.8
        assert call_kwargs["max_tokens"] == 500
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_generate_question_openai_error(self, sample_profile: UserProfile) -> None:
        """Should raise QuestionGenerationError on OpenAI failure."""
        with (
            patch(
                "bot.services.question_service.chat_completion_with_retry",
                new_callable=AsyncMock,
                side_effect=Exception("OpenAI API error"),
            ),
            pytest.raises(QuestionGenerationError, match="Failed to generate question"),
        ):
            await generate_question(sample_profile)

    @pytest.mark.asyncio
    async def test_generate_question_parse_error(self, sample_profile: UserProfile) -> None:
        """Should raise QuestionParseError on invalid response."""
        with (
            patch(
                "bot.services.question_service.chat_completion_with_retry",
                new_callable=AsyncMock,
                return_value="invalid json",
            ),
            pytest.raises(QuestionParseError),
        ):
            await generate_question(sample_profile)

    @pytest.mark.asyncio
    async def test_generate_question_with_markdown_response(
        self, sample_profile: UserProfile
    ) -> None:
        """Should handle markdown-wrapped JSON response."""
        mock_response = """```json
{
    "text": "Question with markdown",
    "category": "algorithms",
    "difficulty": 5
}
```"""

        with patch(
            "bot.services.question_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            question = await generate_question(sample_profile)

        assert question.text == "Question with markdown"
        assert question.category == Category.ALGORITHMS

    @pytest.mark.asyncio
    async def test_generate_question_for_junior(self, junior_profile: UserProfile) -> None:
        """Should generate appropriate question for junior."""
        mock_response = json.dumps(
            {"text": "Junior question", "category": "language", "difficulty": 2}
        )

        with patch(
            "bot.services.question_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            question = await generate_question(junior_profile)

        assert question.difficulty == 2

    @pytest.mark.asyncio
    async def test_generate_question_for_senior(self, senior_profile: UserProfile) -> None:
        """Should generate appropriate question for senior."""
        mock_response = json.dumps(
            {"text": "Senior question", "category": "system_design", "difficulty": 8}
        )

        with patch(
            "bot.services.question_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            question = await generate_question(senior_profile)

        assert question.difficulty == 8
        assert question.category == Category.SYSTEM_DESIGN


class TestCategoryAndGradeConstants:
    """Tests for module constants."""

    def test_all_categories_have_names(self) -> None:
        """All categories should have human-readable names."""
        for category in Category:
            assert category in CATEGORY_NAMES
            assert isinstance(CATEGORY_NAMES[category], str)
            assert len(CATEGORY_NAMES[category]) > 0

    def test_all_grades_have_descriptions(self) -> None:
        """All grades should have descriptions."""
        for grade in Grade:
            assert grade in GRADE_DESCRIPTIONS
            assert isinstance(GRADE_DESCRIPTIONS[grade], str)
            assert len(GRADE_DESCRIPTIONS[grade]) > 0
