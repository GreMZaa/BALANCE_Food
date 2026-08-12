"""Application configuration using Pydantic Settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram Bot Configuration
    telegram_bot_token: SecretStr

    # Supabase Configuration
    supabase_url: str
    supabase_key: SecretStr

    # OpenAI Configuration
    openai_api_key: SecretStr

    # Application Settings
    log_level: str = "INFO"
    log_json: bool = False
    timezone: str = "Europe/Moscow"

    # Daily limits
    free_questions_per_day: int = 5
    daily_goal: int = 5


settings = Settings()
