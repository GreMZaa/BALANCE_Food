"""Domain enums for the Interview Trainer Bot."""

from enum import StrEnum


class Grade(StrEnum):
    """User experience level/grade."""

    JUNIOR = "junior"
    MIDDLE = "middle"
    SENIOR = "senior"


class Specialty(StrEnum):
    """User specialty/role.

    Note: Only BACKEND is available in MVP.
    """

    BACKEND = "backend"
    FRONTEND = "frontend"
    QA = "qa"
    DEVOPS = "devops"
    DATA_SCIENCE = "data_science"


class Category(StrEnum):
    """Question category for interview topics."""

    LANGUAGE = "language"
    ALGORITHMS = "algorithms"
    DATABASES = "databases"
    API_DESIGN = "api_design"
    SYSTEM_DESIGN = "system_design"
    ARCHITECTURE = "architecture"
    MICROSERVICES = "microservices"
    DEVOPS = "devops"


class AnswerType(StrEnum):
    """Type of user answer."""

    TEXT = "text"
    VOICE = "voice"


class PlanType(StrEnum):
    """Subscription plan types."""

    WEEK = "week"
    MONTH = "month"
    THREE_MONTHS = "three_months"
