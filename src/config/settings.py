import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "test_host")
    POSTGRES_PORT: int = os.getenv("POSTGRES_PORT", 5432)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "test_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "test_password")
    POSTGRES_DB:  str = os.getenv("POSTGRES_DB", "test_db")

    SENDGRID_API_KEY: str

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str
    WEBHOOK_ENDPOINT_SECRET: str

    class Config:
        env_file = ".env"


settings = Settings()
