"""Tests for configuration module."""

import pytest
from pydantic import SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def test_settings_loads_from_env():
    """Test that settings loads correctly from .env file."""
    from bot.core.config import settings

    # Verify required fields are loaded (non-empty)
    assert len(settings.telegram_bot_token.get_secret_value()) > 0
    assert len(settings.supabase_url) > 0
    assert len(settings.supabase_key.get_secret_value()) > 0
    assert len(settings.openai_api_key.get_secret_value()) > 0
    assert settings.log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    assert len(settings.timezone) > 0


def test_settings_missing_required_raises_validation_error(monkeypatch):
    """Test that missing required variables raise ValidationError."""
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    class TestSettings(BaseSettings):
        model_config = SettingsConfigDict(
            env_file=None,
            case_sensitive=False,
            extra="ignore",
        )
        telegram_bot_token: SecretStr
        supabase_url: str
        supabase_key: SecretStr
        openai_api_key: SecretStr

    with pytest.raises(ValidationError) as exc_info:
        TestSettings()

    errors = exc_info.value.errors()
    missing_fields = {err["loc"][0] for err in errors}
    assert "telegram_bot_token" in missing_fields
    assert "supabase_url" in missing_fields
    assert "supabase_key" in missing_fields
    assert "openai_api_key" in missing_fields


def test_settings_secretstr_masks_value():
    """Test that SecretStr masks sensitive values when printed."""
    from bot.core.config import settings

    token_str = str(settings.telegram_bot_token)
    secret_value = settings.telegram_bot_token.get_secret_value()
    assert secret_value not in token_str
    assert "**********" in token_str


def test_settings_default_values():
    """Test that optional settings have correct defaults."""
    from bot.core.config import settings

    assert settings.free_questions_per_day == 5
    assert settings.daily_goal == 5
