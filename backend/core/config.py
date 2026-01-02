"""
Application configuration using Pydantic Settings
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API
    PROJECT_NAME: str = "AutoGen Dev Assistant API"
    API_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production-please-use-long-random-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database (SQLite for development - no Docker needed)
    DATABASE_URL: str = "sqlite+aiosqlite:///./autogen_dev.db"

    # Redis (optional - can skip for SQLite development)
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",  # Vite dev server
        "http://localhost:3000",  # Alternative frontend port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields from .env file


settings = Settings()
