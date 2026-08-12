"""Tests for domain entities."""

from datetime import datetime
from uuid import UUID

from bot.domain.entities import (
    AnswerType,
    Category,
    Grade,
    PlanType,
    Progress,
    Specialty,
    User,
    UserProfile,
)


class TestEnums:
    """Tests for domain enums."""

    def test_grade_values(self) -> None:
        """Test Grade enum has correct values."""
        assert Grade.JUNIOR == "junior"
        assert Grade.MIDDLE == "middle"
        assert Grade.SENIOR == "senior"

    def test_specialty_values(self) -> None:
        """Test Specialty enum has correct values."""
        assert Specialty.BACKEND == "backend"
        assert Specialty.FRONTEND == "frontend"
        assert Specialty.QA == "qa"
        assert Specialty.DEVOPS == "devops"
        assert Specialty.DATA_SCIENCE == "data_science"

    def test_category_values(self) -> None:
        """Test Category enum has correct values."""
        assert Category.LANGUAGE == "language"
        assert Category.ALGORITHMS == "algorithms"
        assert Category.DATABASES == "databases"
        assert Category.API_DESIGN == "api_design"
        assert Category.SYSTEM_DESIGN == "system_design"
        assert Category.ARCHITECTURE == "architecture"
        assert Category.MICROSERVICES == "microservices"
        assert Category.DEVOPS == "devops"

    def test_answer_type_values(self) -> None:
        """Test AnswerType enum has correct values."""
        assert AnswerType.TEXT == "text"
        assert AnswerType.VOICE == "voice"

    def test_plan_type_values(self) -> None:
        """Test PlanType enum has correct values."""
        assert PlanType.WEEK == "week"
        assert PlanType.MONTH == "month"
        assert PlanType.THREE_MONTHS == "three_months"


class TestUser:
    """Tests for User entity."""

    def test_create_user_with_telegram_id(self) -> None:
        """Test creating a User with only telegram_id."""
        user = User(telegram_id=123456789)

        assert user.telegram_id == 123456789
        assert isinstance(user.id, UUID)
        assert user.username is None
        assert user.first_name is None
        assert user.timezone == "Europe/Moscow"
        assert user.language_code == "ru"
        assert isinstance(user.created_at, datetime)

    def test_create_user_with_all_fields(self) -> None:
        """Test creating a User with all fields."""
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="John",
            last_name="Doe",
            language_code="en",
            timezone="America/New_York",
        )

        assert user.telegram_id == 123456789
        assert user.username == "testuser"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.language_code == "en"
        assert user.timezone == "America/New_York"

    def test_user_serialization_json(self) -> None:
        """Test User model_dump_json works correctly."""
        user = User(telegram_id=123456789)
        json_str = user.model_dump_json()

        assert "123456789" in json_str
        assert "telegram_id" in json_str


class TestUserProfile:
    """Tests for UserProfile entity."""

    def test_create_profile_with_required_fields(self) -> None:
        """Test creating a UserProfile with required fields."""
        from uuid import uuid4

        user_id = uuid4()
        profile = UserProfile(user_id=user_id, grade=Grade.JUNIOR)

        assert profile.user_id == user_id
        assert profile.grade == Grade.JUNIOR
        assert profile.specialty == Specialty.BACKEND  # default
        assert profile.tech_stack == []
        assert profile.focus_areas == []
        assert profile.current_difficulty == 5  # default

    def test_create_profile_with_all_fields(self) -> None:
        """Test creating a UserProfile with all fields."""
        from uuid import uuid4

        user_id = uuid4()
        profile = UserProfile(
            user_id=user_id,
            specialty=Specialty.BACKEND,
            grade=Grade.MIDDLE,
            tech_stack=["python", "postgresql", "redis"],
            focus_areas=[Category.ALGORITHMS, Category.DATABASES],
            current_difficulty=6,
        )

        assert profile.grade == Grade.MIDDLE
        assert "python" in profile.tech_stack
        assert Category.ALGORITHMS in profile.focus_areas
        assert profile.current_difficulty == 6

    def test_difficulty_range_junior(self) -> None:
        """Test difficulty range for Junior grade."""
        from uuid import uuid4

        profile = UserProfile(user_id=uuid4(), grade=Grade.JUNIOR)
        min_diff, max_diff = profile.get_difficulty_range()

        assert min_diff == 1
        assert max_diff == 4

    def test_difficulty_range_middle(self) -> None:
        """Test difficulty range for Middle grade."""
        from uuid import uuid4

        profile = UserProfile(user_id=uuid4(), grade=Grade.MIDDLE)
        min_diff, max_diff = profile.get_difficulty_range()

        assert min_diff == 3
        assert max_diff == 7

    def test_difficulty_range_senior(self) -> None:
        """Test difficulty range for Senior grade."""
        from uuid import uuid4

        profile = UserProfile(user_id=uuid4(), grade=Grade.SENIOR)
        min_diff, max_diff = profile.get_difficulty_range()

        assert min_diff == 5
        assert max_diff == 10

    def test_adjust_difficulty_within_range(self) -> None:
        """Test adjusting difficulty within allowed range."""
        from uuid import uuid4

        profile = UserProfile(
            user_id=uuid4(), grade=Grade.JUNIOR, current_difficulty=2
        )

        # Increase within range
        new_diff = profile.adjust_difficulty(+1)
        assert new_diff == 3

        # Decrease within range
        new_diff = profile.adjust_difficulty(-1)
        assert new_diff == 1

    def test_adjust_difficulty_clamped_at_max(self) -> None:
        """Test difficulty is clamped at grade maximum."""
        from uuid import uuid4

        profile = UserProfile(
            user_id=uuid4(), grade=Grade.JUNIOR, current_difficulty=4
        )

        # Try to exceed max (4 for Junior)
        new_diff = profile.adjust_difficulty(+5)
        assert new_diff == 4  # Clamped at max

    def test_adjust_difficulty_clamped_at_min(self) -> None:
        """Test difficulty is clamped at grade minimum."""
        from uuid import uuid4

        profile = UserProfile(
            user_id=uuid4(), grade=Grade.SENIOR, current_difficulty=6
        )

        # Try to go below min (5 for Senior)
        new_diff = profile.adjust_difficulty(-5)
        assert new_diff == 5  # Clamped at min

    def test_profile_serialization_json(self) -> None:
        """Test UserProfile model_dump_json works correctly."""
        from uuid import uuid4

        profile = UserProfile(user_id=uuid4(), grade=Grade.MIDDLE)
        json_str = profile.model_dump_json()

        assert "middle" in json_str
        assert "grade" in json_str


class TestProgress:
    """Tests for Progress entity."""

    def test_create_progress_with_required_fields(self) -> None:
        """Test creating Progress with required fields."""
        from uuid import uuid4

        user_id = uuid4()
        progress = Progress(user_id=user_id)

        assert progress.user_id == user_id
        assert progress.current_streak == 0
        assert progress.longest_streak == 0
        assert progress.total_questions_answered == 0
        assert progress.questions_today == 0
        assert progress.last_activity_date is None

    def test_has_reached_daily_goal_false(self) -> None:
        """Test daily goal not reached."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), questions_today=3)

        assert progress.has_reached_daily_goal(5) is False

    def test_has_reached_daily_goal_true(self) -> None:
        """Test daily goal reached."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), questions_today=5)

        assert progress.has_reached_daily_goal(5) is True

    def test_has_reached_daily_goal_exceeded(self) -> None:
        """Test daily goal exceeded."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), questions_today=7)

        assert progress.has_reached_daily_goal(5) is True

    def test_update_longest_streak(self) -> None:
        """Test updating longest streak."""
        from uuid import uuid4

        progress = Progress(
            user_id=uuid4(),
            current_streak=10,
            longest_streak=5,
        )

        progress.update_longest_streak()

        assert progress.longest_streak == 10

    def test_update_longest_streak_no_change(self) -> None:
        """Test longest streak not updated when current is lower."""
        from uuid import uuid4

        progress = Progress(
            user_id=uuid4(),
            current_streak=3,
            longest_streak=10,
        )

        progress.update_longest_streak()

        assert progress.longest_streak == 10  # Unchanged

    def test_is_milestone_streak_7_days(self) -> None:
        """Test 7-day milestone detection."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), current_streak=7)

        assert progress.is_milestone_streak() == 7

    def test_is_milestone_streak_30_days(self) -> None:
        """Test 30-day milestone detection."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), current_streak=30)

        assert progress.is_milestone_streak() == 30

    def test_is_milestone_streak_100_days(self) -> None:
        """Test 100-day milestone detection."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), current_streak=100)

        assert progress.is_milestone_streak() == 100

    def test_is_milestone_streak_not_milestone(self) -> None:
        """Test non-milestone streak returns None."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), current_streak=15)

        assert progress.is_milestone_streak() is None

    def test_progress_serialization_json(self) -> None:
        """Test Progress model_dump_json works correctly."""
        from uuid import uuid4

        progress = Progress(user_id=uuid4(), current_streak=5)
        json_str = progress.model_dump_json()

        assert "current_streak" in json_str
        assert "5" in json_str
