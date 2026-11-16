import os
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    PROJECT_NAME: str = "SRIVANI BOOKING MANAGER Cloud SaaS"
    VERSION: str = "8.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development")

    # Security & JWT
    SECRET_KEY: str = Field(
        default="srivani-saas-secure-jwt-secret-key-change-in-production-2026-phase8"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Rate limiting
    RATE_LIMIT_LOGIN_ATTEMPTS_PER_MIN: int = 5

    # Database
    # Async DB URL: postgresql+asyncpg://... or sqlite+aiosqlite://...
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/srivani_saas.db"
    )
    SYNC_DATABASE_URL: str = Field(
        default="sqlite:///./data/srivani_saas.db"
    )

    # Private File Storage
    STORAGE_DIR: str = Field(default="./storage/tenants")
    MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Default Super Admin Seed Credentials
    SUPER_ADMIN_EMAIL: str = "superadmin@srivanimanager.com"
    SUPER_ADMIN_PASSWORD: str = "SrivaniAdmin@2026!Secure"
    SUPER_ADMIN_NAME: str = "Platform Super Administrator"


settings = Settings()

# Ensure storage directory exists
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs("./data", exist_ok=True)
