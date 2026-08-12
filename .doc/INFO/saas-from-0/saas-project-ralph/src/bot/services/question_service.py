"""Question generation service using OpenAI."""

import json
import logging
import random

from bot.domain.entities.enums import Category, Grade
from bot.domain.entities.profile import UserProfile
from bot.domain.entities.question import Question
from bot.infrastructure.openai.client import chat_completion_with_retry

logger = logging.getLogger(__name__)


class QuestionServiceError(Exception):
    """Base exception for question service errors."""

    pass


class QuestionGenerationError(QuestionServiceError):
    """Raised when question generation fails."""

    pass


class QuestionParseError(QuestionServiceError):
    """Raised when parsing OpenAI response fails."""

    pass


# Human-readable category names for prompts
CATEGORY_NAMES = {
    Category.LANGUAGE: "особенности языка программирования",
    Category.ALGORITHMS: "алгоритмы и структуры данных",
    Category.DATABASES: "базы данных и SQL",
    Category.API_DESIGN: "проектирование API",
    Category.SYSTEM_DESIGN: "проектирование систем",
    Category.ARCHITECTURE: "архитектура приложений",
    Category.MICROSERVICES: "микросервисная архитектура",
    Category.DEVOPS: "DevOps и инфраструктура",
}

# Grade descriptions for context
GRADE_DESCRIPTIONS = {
    Grade.JUNIOR: "начинающий разработчик (Junior) с 0-2 годами опыта",
    Grade.MIDDLE: "разработчик среднего уровня (Middle) с 2-4 годами опыта",
    Grade.SENIOR: "опытный разработчик (Senior) с 5+ годами опыта",
}


def _build_question_prompt(
    profile: UserProfile, recent_questions: list[str] | None = None
) -> str:
    """Build a prompt for question generation based on user profile.

    Args:
        profile: User profile with specialty, grade, tech_stack, focus_areas
        recent_questions: List of recently asked question texts to avoid repeating

    Returns:
        Formatted prompt string
    """
    grade_desc = GRADE_DESCRIPTIONS.get(profile.grade, str(profile.grade))

    # Format tech stack
    tech_stack_str = ", ".join(profile.tech_stack) if profile.tech_stack else "общие технологии"

    # Select a random category from focus_areas for this question
    if profile.focus_areas:
        category = random.choice(profile.focus_areas)
    else:
        category = random.choice(list(Category))

    category_name = CATEGORY_NAMES.get(category, str(category))

    prompt = f"""Ты — опытный технический интервьюер для собеседований Backend разработчиков.

Сгенерируй ОДИН вопрос для собеседования со следующими параметрами:
- Уровень кандидата: {grade_desc}
- Технологии: {tech_stack_str}
- Тема вопроса: {category_name}
- Сложность: {profile.current_difficulty}/10

Требования к вопросу:
1. Вопрос должен быть открытым, требующим развёрнутого ответа
2. Сложность должна соответствовать указанному уровню ({profile.current_difficulty}/10)
3. Вопрос должен проверять практические знания, а не теорию из учебника
4. Формулировка должна быть чёткой и однозначной
5. Вопрос должен быть на русском языке

Ответь ТОЛЬКО в формате JSON (без markdown блоков):
{{
    "text": "текст вопроса",
    "category": "{category.value}",
    "difficulty": {profile.current_difficulty}
}}"""

    if recent_questions:
        numbered = "\n".join(f"{i + 1}. {q}" for i, q in enumerate(recent_questions))
        prompt += (
            "\n\nНе повторяй следующие вопросы, которые уже были заданы. "
            "Сгенерируй вопрос на другую тему или с другой формулировкой:\n"
            + numbered
        )

    return prompt


def _parse_question_response(response: str, expected_difficulty: int) -> Question:
    """Parse OpenAI response into Question model.

    Args:
        response: Raw response from OpenAI
        expected_difficulty: Expected difficulty level for validation

    Returns:
        Parsed Question object

    Raises:
        QuestionParseError: If parsing fails
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
        raise QuestionParseError(f"Invalid JSON in response: {e}") from e

    # Validate required fields
    if "text" not in data:
        raise QuestionParseError("Missing 'text' field in response")

    text = data["text"]
    if not isinstance(text, str) or not text.strip():
        raise QuestionParseError("Invalid or empty 'text' field")

    # Parse category
    category_str = data.get("category", "language")
    try:
        category = Category(category_str)
    except ValueError:
        logger.warning(f"Unknown category '{category_str}', defaulting to LANGUAGE")
        category = Category.LANGUAGE

    # Parse difficulty - use expected if not provided or invalid
    difficulty = data.get("difficulty", expected_difficulty)
    if not isinstance(difficulty, int) or difficulty < 1 or difficulty > 10:
        logger.warning(f"Invalid difficulty '{difficulty}', using expected: {expected_difficulty}")
        difficulty = expected_difficulty

    return Question(
        text=text.strip(),
        category=category,
        difficulty=difficulty,
    )


async def generate_question(
    profile: UserProfile, recent_questions: list[str] | None = None
) -> Question:
    """Generate an interview question based on user profile.

    Args:
        profile: User profile containing grade, tech_stack, focus_areas, difficulty
        recent_questions: List of recently asked question texts to avoid repeating

    Returns:
        Generated Question object

    Raises:
        QuestionGenerationError: If generation fails
        QuestionParseError: If response parsing fails
    """
    logger.info(
        f"Generating question for user profile: "
        f"grade={profile.grade}, tech_stack={profile.tech_stack}, "
        f"focus_areas={profile.focus_areas}, difficulty={profile.current_difficulty}"
    )

    prompt = _build_question_prompt(profile, recent_questions)

    messages = [
        {
            "role": "system",
            "content": "Ты — технический интервьюер. Отвечай только в формате JSON.",
        },
        {"role": "user", "content": prompt},
    ]

    try:
        response = await chat_completion_with_retry(
            messages=messages,
            temperature=0.8,  # Higher temperature for more variety
            max_tokens=500,
        )
    except Exception as e:
        logger.error(f"OpenAI request failed: {e}")
        raise QuestionGenerationError(f"Failed to generate question: {e}") from e

    try:
        question = _parse_question_response(response, profile.current_difficulty)
    except QuestionParseError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error parsing response: {e}")
        raise QuestionParseError(f"Failed to parse question: {e}") from e

    logger.info(
        f"Generated question: category={question.category}, "
        f"difficulty={question.difficulty}, text_len={len(question.text)}"
    )

    return question
