"""
Staxx Proxy Gateway — Configuration

All settings are loaded from environment variables with sensible defaults.
Uses pydantic-settings for automatic env var binding and validation.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Env vars are prefixed with ``STAXX_PROXY_`` by default.
    Example: ``STAXX_PROXY_REDIS_URL=redis://localhost:6379/0``
    """

    model_config = SettingsConfigDict(
        env_prefix="STAXX_PROXY_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Server ──────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = False
    log_level: str = "INFO"

    # ── Provider Base URLs ──────────────────────────────────────────────
    openai_base_url: str = "https://api.openai.com"
    anthropic_base_url: str = "https://api.anthropic.com"

    # ── Redis ───────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    telemetry_stream: str = "staxx:telemetry"
    telemetry_maxlen: int = 100_000  # Cap stream length

    # ── Postgres (for API-key validation) ───────────────────────────────
    database_url: str = "postgresql://staxx:staxx@localhost:5432/staxx"
    db_pool_min: int = 2
    db_pool_max: int = 10

    # ── Telemetry Fallback ──────────────────────────────────────────────
    telemetry_fallback_path: str = "/tmp/staxx_telemetry_fallback.jsonl"

    # ── Timeouts (seconds) ──────────────────────────────────────────────
    forward_timeout: float = 120.0  # Max wait for provider response
    forward_connect_timeout: float = 10.0

    # ── CORS ────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]


settings = Settings()
