"""
Platform-layer settings, extending the backend app config.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class PlatformSettings(BaseSettings):
    # JWT
    JWT_SECRET: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Plan → Stripe price ID mapping (metered billing price IDs)
    STRIPE_PRICE_STARTER: str = ""   # $99/mo, 100k req
    STRIPE_PRICE_GROWTH: str = ""    # $499/mo, 1M req
    STRIPE_PRICE_ENTERPRISE: str = ""

    # Redis (reused from backend env vars)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # Postgres (reused from backend env vars)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "staxx"
    POSTGRES_PASSWORD: str = "staxx"
    POSTGRES_DB: str = "staxx"
    POSTGRES_PORT: str = "5432"

    @property
    def ASYNC_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # App base URL (used for invite links)
    APP_BASE_URL: str = "http://localhost:3000"

    # Invitation expiry in hours
    INVITATION_EXPIRE_HOURS: int = 72

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = PlatformSettings()
