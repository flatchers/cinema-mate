import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SENDGRID_API_KEY: str

    STRIPE_PUBLISHABLE_KEY: str
    STRIPE_SECRET_KEY: str
    WEBHOOK_ENDPOINT_SECRET: str

    class Config:
        env_file = ".env"

settings = Settings()
