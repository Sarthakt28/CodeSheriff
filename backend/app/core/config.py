import os
from pydantic_settings import BaseSettings
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(BASE_DIR, ".env")


class Settings(BaseSettings):
    # GitHub App
    GITHUB_APP_ID: str = ""
    GITHUB_PRIVATE_KEY_PATH: str = "private-key.pem"
    GITHUB_WEBHOOK_SECRET: str = ""
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""

    # Database
    DATABASE_URL: str = "postgresql://sheriff:sheriff_pass@localhost:5432/codesheriff"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    JWT_SECRET: str = "change-this-to-a-long-random-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 1440

    # ML
    MODEL_PATH: str = "ml/model_output"
    USE_ML_REVIEWER: bool = False

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,https://codesheriff-frontend.onrender.com"

    class Config:
        env_file = ENV_FILE
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
