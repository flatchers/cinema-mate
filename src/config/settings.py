import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    MODE: str = "DEV"

    POSTGRES_HOST: str | None = None
    POSTGRES_PORT: int | None = None
    POSTGRES_USER: str | None = None
    POSTGRES_PASSWORD: str | None = None
    POSTGRES_DB: str | None = None

    SENDGRID_API_KEY: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_SECRET_KEY: str | None = None
    WEBHOOK_ENDPOINT_SECRET: str | None = None

    model_config = SettingsConfigDict(
        env_file=".test.env" if os.getenv("MODE") == "TEST"
        else ".env", extra="ignore"
    )


settings = Settings()
