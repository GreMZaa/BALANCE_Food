"""Tests for answer evaluation service."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from bot.domain.entities.enums import Grade
from bot.domain.entities.question import Evaluation
from bot.services.evaluation_service import (
    GRADE_EVALUATION_CONTEXT,
    EvaluationError,
    EvaluationParseError,
    _build_evaluation_prompt,
    _parse_evaluation_response,
    evaluate_answer,
)


@pytest.fixture
def sample_question() -> str:
    """Sample interview question for testing."""
    return "Объясните разницу между процессом и потоком."


@pytest.fixture
def sample_answer() -> str:
    """Sample user answer for testing."""
    return (
        "Процесс - это независимый экземпляр программы с собственной памятью. "
        "Поток - это единица выполнения внутри процесса, которая разделяет память с другими потоками."
    )


@pytest.fixture
def empty_answer() -> str:
    """Empty answer for testing."""
    return ""


@pytest.fixture
def short_answer() -> str:
    """Very short answer for testing."""
    return "Не знаю"


class TestBuildEvaluationPrompt:
    """Tests for _build_evaluation_prompt function."""

    def test_prompt_contains_question(self, sample_question: str, sample_answer: str) -> None:
        """Prompt should include the question."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.MIDDLE)
        assert sample_question in prompt

    def test_prompt_contains_answer(self, sample_question: str, sample_answer: str) -> None:
        """Prompt should include the user's answer."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.MIDDLE)
        assert sample_answer in prompt

    def test_prompt_contains_grade_context_junior(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Prompt should include junior grade context."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.JUNIOR)
        assert GRADE_EVALUATION_CONTEXT[Grade.JUNIOR] in prompt

    def test_prompt_contains_grade_context_middle(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Prompt should include middle grade context."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.MIDDLE)
        assert GRADE_EVALUATION_CONTEXT[Grade.MIDDLE] in prompt

    def test_prompt_contains_grade_context_senior(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Prompt should include senior grade context."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.SENIOR)
        assert GRADE_EVALUATION_CONTEXT[Grade.SENIOR] in prompt

    def test_prompt_requests_json_format(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Prompt should request JSON format."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.MIDDLE)
        assert "JSON" in prompt
        assert '"score"' in prompt
        assert '"strengths"' in prompt
        assert '"improvements"' in prompt
        assert '"reference_answer"' in prompt

    def test_prompt_contains_scoring_guidelines(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Prompt should contain scoring guidelines."""
        prompt = _build_evaluation_prompt(sample_question, sample_answer, Grade.MIDDLE)
        assert "1-3" in prompt
        assert "4-5" in prompt
        assert "6-7" in prompt
        assert "8-9" in prompt
        assert "10" in prompt


class TestParseEvaluationResponse:
    """Tests for _parse_evaluation_response function."""

    def test_parse_valid_json(self) -> None:
        """Should parse valid JSON response."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": ["Good explanation", "Clear examples"],
                "improvements": ["Could mention more details"],
                "reference_answer": "A complete answer would include...",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.score == 7
        assert evaluation.strengths == ["Good explanation", "Clear examples"]
        assert evaluation.improvements == ["Could mention more details"]
        assert evaluation.reference_answer == "A complete answer would include..."

    def test_parse_json_with_markdown_code_block(self) -> None:
        """Should parse JSON wrapped in markdown code blocks."""
        response = """```json
{
    "score": 8,
    "strengths": ["Strong point"],
    "improvements": [],
    "reference_answer": "Reference answer text"
}
```"""
        evaluation = _parse_evaluation_response(response)
        assert evaluation.score == 8
        assert evaluation.strengths == ["Strong point"]
        assert evaluation.improvements == []

    def test_parse_json_with_plain_code_block(self) -> None:
        """Should parse JSON wrapped in plain code blocks."""
        response = """```
{"score": 6, "strengths": [], "improvements": ["Needs work"], "reference_answer": "Answer"}
```"""
        evaluation = _parse_evaluation_response(response)
        assert evaluation.score == 6

    def test_parse_missing_score_raises_error(self) -> None:
        """Should raise EvaluationParseError when score is missing."""
        response = json.dumps(
            {
                "strengths": [],
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        with pytest.raises(EvaluationParseError, match="Missing 'score' field"):
            _parse_evaluation_response(response)

    def test_parse_missing_reference_answer_raises_error(self) -> None:
        """Should raise EvaluationParseError when reference_answer is missing."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": [],
            }
        )
        with pytest.raises(EvaluationParseError, match="Missing 'reference_answer' field"):
            _parse_evaluation_response(response)

    def test_parse_empty_reference_answer_raises_error(self) -> None:
        """Should raise EvaluationParseError when reference_answer is empty."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": [],
                "reference_answer": "",
            }
        )
        with pytest.raises(EvaluationParseError, match="Invalid or empty 'reference_answer'"):
            _parse_evaluation_response(response)

    def test_parse_whitespace_reference_answer_raises_error(self) -> None:
        """Should raise EvaluationParseError when reference_answer is whitespace."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": [],
                "reference_answer": "   ",
            }
        )
        with pytest.raises(EvaluationParseError, match="Invalid or empty 'reference_answer'"):
            _parse_evaluation_response(response)

    def test_parse_invalid_json_raises_error(self) -> None:
        """Should raise EvaluationParseError for invalid JSON."""
        with pytest.raises(EvaluationParseError, match="Invalid JSON"):
            _parse_evaluation_response("not valid json")

    def test_parse_score_as_string_converts(self) -> None:
        """Should convert string score to int."""
        response = json.dumps(
            {
                "score": "7",
                "strengths": [],
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.score == 7

    def test_parse_score_out_of_range_clamps(self) -> None:
        """Should clamp score to 1-10 range."""
        # Test score > 10
        response = json.dumps(
            {
                "score": 15,
                "strengths": [],
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.score == 10

        # Test score < 1
        response = json.dumps(
            {
                "score": 0,
                "strengths": [],
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.score == 1

    def test_parse_invalid_score_type_raises_error(self) -> None:
        """Should raise error for non-convertible score."""
        response = json.dumps(
            {
                "score": "not a number",
                "strengths": [],
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        with pytest.raises(EvaluationParseError, match="Invalid score value"):
            _parse_evaluation_response(response)

    def test_parse_missing_strengths_defaults_to_empty(self) -> None:
        """Should default to empty list when strengths is missing."""
        response = json.dumps(
            {
                "score": 7,
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.strengths == []

    def test_parse_missing_improvements_defaults_to_empty(self) -> None:
        """Should default to empty list when improvements is missing."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": ["Good"],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.improvements == []

    def test_parse_invalid_strengths_type_defaults_to_empty(self) -> None:
        """Should default to empty list for invalid strengths type."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": "not a list",
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.strengths == []

    def test_parse_invalid_improvements_type_defaults_to_empty(self) -> None:
        """Should default to empty list for invalid improvements type."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": "not a list",
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.improvements == []

    def test_parse_filters_empty_strengths(self) -> None:
        """Should filter out empty strings from strengths."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": ["Good", "", "Also good", None],
                "improvements": [],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.strengths == ["Good", "Also good"]

    def test_parse_filters_empty_improvements(self) -> None:
        """Should filter out empty strings from improvements."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": ["Needs work", "", None, "Also this"],
                "reference_answer": "Answer",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.improvements == ["Needs work", "Also this"]

    def test_parse_strips_reference_answer_whitespace(self) -> None:
        """Should strip whitespace from reference_answer."""
        response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": [],
                "reference_answer": "  Answer with spaces  ",
            }
        )
        evaluation = _parse_evaluation_response(response)
        assert evaluation.reference_answer == "Answer with spaces"

    def test_parse_all_valid_scores(self) -> None:
        """Should parse all valid scores 1-10."""
        for score in range(1, 11):
            response = json.dumps(
                {
                    "score": score,
                    "strengths": [],
                    "improvements": [],
                    "reference_answer": "Answer",
                }
            )
            evaluation = _parse_evaluation_response(response)
            assert evaluation.score == score


class TestEvaluateAnswer:
    """Tests for evaluate_answer function."""

    @pytest.mark.asyncio
    async def test_evaluate_answer_success(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should evaluate answer successfully."""
        mock_response = json.dumps(
            {
                "score": 8,
                "strengths": ["Clear explanation", "Good structure"],
                "improvements": ["Could add more examples"],
                "reference_answer": "A process is an independent program instance...",
            }
        )

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            evaluation = await evaluate_answer(sample_question, sample_answer, Grade.MIDDLE)

        assert isinstance(evaluation, Evaluation)
        assert evaluation.score == 8
        assert evaluation.strengths == ["Clear explanation", "Good structure"]
        assert evaluation.improvements == ["Could add more examples"]

    @pytest.mark.asyncio
    async def test_evaluate_answer_calls_openai_with_correct_params(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should call OpenAI API with correct parameters."""
        mock_response = json.dumps(
            {
                "score": 7,
                "strengths": [],
                "improvements": [],
                "reference_answer": "Reference answer",
            }
        )

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_chat:
            await evaluate_answer(sample_question, sample_answer, Grade.MIDDLE)

        mock_chat.assert_called_once()
        call_kwargs = mock_chat.call_args.kwargs
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 800
        assert len(call_kwargs["messages"]) == 2
        assert call_kwargs["messages"][0]["role"] == "system"
        assert call_kwargs["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_evaluate_answer_openai_error(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should raise EvaluationError on OpenAI failure."""
        with (
            patch(
                "bot.services.evaluation_service.chat_completion_with_retry",
                new_callable=AsyncMock,
                side_effect=Exception("OpenAI API error"),
            ),
            pytest.raises(EvaluationError, match="Failed to evaluate answer"),
        ):
            await evaluate_answer(sample_question, sample_answer, Grade.MIDDLE)

    @pytest.mark.asyncio
    async def test_evaluate_answer_parse_error(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should raise EvaluationParseError on invalid response."""
        with (
            patch(
                "bot.services.evaluation_service.chat_completion_with_retry",
                new_callable=AsyncMock,
                return_value="invalid json",
            ),
            pytest.raises(EvaluationParseError),
        ):
            await evaluate_answer(sample_question, sample_answer, Grade.MIDDLE)

    @pytest.mark.asyncio
    async def test_evaluate_answer_with_markdown_response(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should handle markdown-wrapped JSON response."""
        mock_response = """```json
{
    "score": 9,
    "strengths": ["Excellent"],
    "improvements": [],
    "reference_answer": "Perfect answer"
}
```"""

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            evaluation = await evaluate_answer(sample_question, sample_answer, Grade.MIDDLE)

        assert evaluation.score == 9
        assert evaluation.strengths == ["Excellent"]

    @pytest.mark.asyncio
    async def test_evaluate_answer_for_junior(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should evaluate with junior context."""
        mock_response = json.dumps(
            {
                "score": 7,
                "strengths": ["Good for junior"],
                "improvements": [],
                "reference_answer": "Reference",
            }
        )

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_chat:
            await evaluate_answer(sample_question, sample_answer, Grade.JUNIOR)

        # Check that the prompt contains junior context
        call_kwargs = mock_chat.call_args.kwargs
        user_message = call_kwargs["messages"][1]["content"]
        assert GRADE_EVALUATION_CONTEXT[Grade.JUNIOR] in user_message

    @pytest.mark.asyncio
    async def test_evaluate_answer_for_senior(
        self, sample_question: str, sample_answer: str
    ) -> None:
        """Should evaluate with senior context."""
        mock_response = json.dumps(
            {
                "score": 5,
                "strengths": [],
                "improvements": ["Expected more from senior"],
                "reference_answer": "Reference",
            }
        )

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ) as mock_chat:
            await evaluate_answer(sample_question, sample_answer, Grade.SENIOR)

        # Check that the prompt contains senior context
        call_kwargs = mock_chat.call_args.kwargs
        user_message = call_kwargs["messages"][1]["content"]
        assert GRADE_EVALUATION_CONTEXT[Grade.SENIOR] in user_message

    @pytest.mark.asyncio
    async def test_evaluate_empty_answer(self, sample_question: str, empty_answer: str) -> None:
        """Should be able to evaluate empty answer."""
        mock_response = json.dumps(
            {
                "score": 1,
                "strengths": [],
                "improvements": ["Answer is missing"],
                "reference_answer": "A good answer would be...",
            }
        )

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            evaluation = await evaluate_answer(sample_question, empty_answer, Grade.MIDDLE)

        assert evaluation.score == 1

    @pytest.mark.asyncio
    async def test_evaluate_short_answer(self, sample_question: str, short_answer: str) -> None:
        """Should be able to evaluate very short answer."""
        mock_response = json.dumps(
            {
                "score": 2,
                "strengths": [],
                "improvements": ["Too brief", "No explanation"],
                "reference_answer": "A complete answer would include...",
            }
        )

        with patch(
            "bot.services.evaluation_service.chat_completion_with_retry",
            new_callable=AsyncMock,
            return_value=mock_response,
        ):
            evaluation = await evaluate_answer(sample_question, short_answer, Grade.MIDDLE)

        assert evaluation.score == 2
        assert len(evaluation.improvements) == 2


class TestGradeEvaluationContextConstants:
    """Tests for module constants."""

    def test_all_grades_have_evaluation_context(self) -> None:
        """All grades should have evaluation context."""
        for grade in Grade:
            assert grade in GRADE_EVALUATION_CONTEXT
            assert isinstance(GRADE_EVALUATION_CONTEXT[grade], str)
            assert len(GRADE_EVALUATION_CONTEXT[grade]) > 0

    def test_junior_context_mentions_experience(self) -> None:
        """Junior context should mention limited experience."""
        context = GRADE_EVALUATION_CONTEXT[Grade.JUNIOR]
        assert "0-2" in context or "Junior" in context

    def test_middle_context_mentions_experience(self) -> None:
        """Middle context should mention moderate experience."""
        context = GRADE_EVALUATION_CONTEXT[Grade.MIDDLE]
        assert "2-4" in context or "Middle" in context

    def test_senior_context_mentions_experience(self) -> None:
        """Senior context should mention significant experience."""
        context = GRADE_EVALUATION_CONTEXT[Grade.SENIOR]
        assert "5+" in context or "Senior" in context
