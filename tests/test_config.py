"""Tests for configuration module."""

from pydantic_settings import SettingsConfigDict

from polymarket_bot.config import Settings


class IsolatedSettings(Settings):
    """Settings class that doesn't load from .env file for testing."""
    model_config = SettingsConfigDict(
        env_file=None,
        extra="ignore"
    )


def test_settings_default_values():
    """Test that settings have sensible defaults."""
    # Create settings without loading from .env file
    settings = IsolatedSettings(
        polymarket_api_key="test_key",
        polymarket_secret="test_secret"
    )

    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.enable_trading is False
    assert settings.max_position_size == 100.0


def test_settings_celery_broker_fallback():
    """Test that celery_broker falls back to redis_url."""
    settings = IsolatedSettings(
        polymarket_api_key="test_key",
        polymarket_secret="test_secret",
        redis_url="redis://custom:6379/0"
    )

    assert settings.celery_broker == "redis://custom:6379/0"


def test_settings_trading_disabled_by_default():
    """Test that trading is disabled by default for safety."""
    settings = IsolatedSettings(
        polymarket_api_key="test_key",
        polymarket_secret="test_secret"
    )

    assert settings.enable_trading is False
