"""Answer evaluation service using OpenAI."""

import json
import logging

from bot.domain.entities.enums import Grade
from bot.domain.entities.question import Evaluation
from bot.infrastructure.openai.client import chat_completion_with_retry

logger = logging.getLogger(__name__)


class EvaluationServiceError(Exception):
    """Base exception for evaluation service errors."""

    pass


class EvaluationError(EvaluationServiceError):
    """Raised when answer evaluation fails."""

    pass


class EvaluationParseError(EvaluationServiceError):
    """Raised when parsing OpenAI evaluation response fails."""

    pass


# Grade descriptions for evaluation context
GRADE_EVALUATION_CONTEXT = {
    Grade.JUNIOR: (
        "начинающего разработчика (Junior) с 0-2 годами опыта. "
        "Ожидается базовое понимание концепций, возможны небольшие пробелы в знаниях."
    ),
    Grade.MIDDLE: (
        "разработчика среднего уровня (Middle) с 2-4 годами опыта. "
        "Ожидается хорошее понимание темы, способность объяснить на практических примерах."
    ),
    Grade.SENIOR: (
        "опытного разработчика (Senior) с 5+ годами опыта. "
        "Ожидается глубокое понимание, знание edge cases, архитектурных решений и best practices."
    ),
}


def _build_evaluation_prompt(
    question: str,
    answer: str,
    grade: Grade,
) -> str:
    """Build a prompt for answer evaluation.

    Args:
        question: The interview question that was asked
        answer: User's answer to evaluate
        grade: User's grade level for context

    Returns:
        Formatted prompt string
    """
    grade_context = GRADE_EVALUATION_CONTEXT.get(grade, str(grade))

    prompt = f"""Ты — опытный технический интервьюер. Оцени ответ кандидата на вопрос собеседования.

ВОПРОС:
{question}

ОТВЕТ КАНДИДАТА:
{answer}

КОНТЕКСТ:
Оценивай ответ с позиции {grade_context}

ЗАДАЧА:
1. Оцени ответ по шкале от 1 до 10, где:
   - 1-3: Неверный или очень слабый ответ
   - 4-5: Частично верный, но с существенными пробелами
   - 6-7: Хороший ответ с небольшими недочётами
   - 8-9: Отличный ответ, почти полный
   - 10: Идеальный, исчерпывающий ответ

2. Выдели 1-3 сильные стороны ответа (если есть)

3. Выдели 1-3 области для улучшения (если есть)

4. Напиши эталонный ответ на этот вопрос (2-4 предложения)

Ответь ТОЛЬКО в формате JSON (без markdown блоков):
{{
    "score": <число от 1 до 10>,
    "strengths": ["сильная сторона 1", "сильная сторона 2"],
    "improvements": ["что улучшить 1", "что улучшить 2"],
    "reference_answer": "эталонный ответ на вопрос"
}}"""

    return prompt


def _parse_evaluation_response(response: str) -> Evaluation:
    """Parse OpenAI response into Evaluation model.

    Args:
        response: Raw response from OpenAI

    Returns:
        Parsed Evaluation object

    Raises:
        EvaluationParseError: If parsing fails
    """
    # Clean response - remove markdown code blocks if present
    cleaned = response.strip()
    if cleaned.startswith("```"):
        # Remove opening code block (```json or ```)
        first_newline = cleaned.find("\n")
        if first_newline != -1:
            cleaned = cleaned[first_newline + 1 :]
        # Remove closing code block
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.debug(f"Raw response: {response}")
        raise EvaluationParseError(f"Invalid JSON in response: {e}") from e

    # Validate required fields
    if "score" not in data:
        raise EvaluationParseError("Missing 'score' field in response")

    if "reference_answer" not in data:
        raise EvaluationParseError("Missing 'reference_answer' field in response")

    # Parse score
    score = data["score"]
    if not isinstance(score, int):
        try:
            score = int(score)
        except (TypeError, ValueError) as e:
            raise EvaluationParseError(f"Invalid score value: {data['score']}") from e

    if score < 1 or score > 10:
        logger.warning(f"Score {score} out of range, clamping to 1-10")
        score = max(1, min(10, score))

    # Parse strengths
    strengths = data.get("strengths", [])
    if not isinstance(strengths, list):
        logger.warning(f"Invalid strengths type: {type(strengths)}, using empty list")
        strengths = []
    strengths = [str(s) for s in strengths if s]

    # Parse improvements
    improvements = data.get("improvements", [])
    if not isinstance(improvements, list):
        logger.warning(f"Invalid improvements type: {type(improvements)}, using empty list")
        improvements = []
    improvements = [str(i) for i in improvements if i]

    # Parse reference answer
    reference_answer = data["reference_answer"]
    if not isinstance(reference_answer, str) or not reference_answer.strip():
        raise EvaluationParseError("Invalid or empty 'reference_answer' field")

    return Evaluation(
        score=score,
        strengths=strengths,
        improvements=improvements,
        reference_answer=reference_answer.strip(),
    )


async def evaluate_answer(
    question: str,
    answer: str,
    grade: Grade,
) -> Evaluation:
    """Evaluate a user's answer to an interview question.

    Args:
        question: The interview question that was asked
        answer: User's answer to evaluate
        grade: User's grade level for evaluation context

    Returns:
        Evaluation object with score, strengths, improvements, and reference_answer

    Raises:
        EvaluationError: If evaluation fails
        EvaluationParseError: If response parsing fails
    """
    logger.info(
        f"Evaluating answer: question_len={len(question)}, "
        f"answer_len={len(answer)}, grade={grade}"
    )

    prompt = _build_evaluation_prompt(question, answer, grade)

    messages = [
        {
            "role": "system",
            "content": (
                "Ты — опытный технический интервьюер, оценивающий ответы кандидатов. "
                "Отвечай только в формате JSON."
            ),
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = await chat_completion_with_retry(
            messages=messages,
            temperature=0.3,  # Lower temperature for more consistent evaluation
            max_tokens=800,
        )
    except Exception as e:
        logger.error(f"OpenAI request failed: {e}")
        raise EvaluationError(f"Failed to evaluate answer: {e}") from e

    try:
        evaluation = _parse_evaluation_response(response)
    except EvaluationParseError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing response: {e}")
        raise EvaluationParseError(f"Failed to parse evaluation: {e}") from e

    logger.info(
        f"Evaluation complete: score={evaluation.score}, "
        f"strengths={len(evaluation.strengths)}, improvements={len(evaluation.improvements)}"
    )

    return evaluation
