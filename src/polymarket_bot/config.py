"""Configuration management using Pydantic settings."""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = Field(default=False, description="Enable debug mode")

    # Polymarket API
    polymarket_api_key: str = Field(..., description="Polymarket API key")
    polymarket_secret: str = Field(..., description="Polymarket secret key")
    polymarket_chain_id: int = Field(default=137, description="Polygon chain ID (137 for mainnet)")
    polymarket_passphrase: str = Field(default="", description="Optional passphrase")

    # Trading Configuration
    max_position_size: float = Field(default=100.0, description="Maximum position size in USD")
    max_slippage: float = Field(default=0.01, description="Maximum acceptable slippage")
    enable_trading: bool = Field(default=False, description="Enable live trading (safety switch)")

    # Celery/Redis
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")
    celery_broker_url: str | None = Field(default=None, description="Celery broker URL")
    celery_result_backend: str | None = Field(default=None, description="Celery result backend")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="logs/bot.log", description="Log file path")

    # Monitoring
    enable_metrics: bool = Field(default=False, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=8000, description="Metrics server port")

    @property
    def celery_broker(self) -> str:
        """Get Celery broker URL, defaulting to Redis URL."""
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        """Get Celery result backend URL, defaulting to Redis URL."""
        return self.celery_result_backend or self.redis_url


# Global settings instance
settings = Settings()
