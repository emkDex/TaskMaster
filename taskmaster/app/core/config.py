"""
Core configuration module for TaskMaster Pro.
Uses pydantic-settings for environment variable management with full validation.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "TaskMaster Pro"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taskmaster"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = "change-this-secret-key-in-production-min-32-chars"
    REFRESH_SECRET_KEY: str = "change-this-refresh-secret-key-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    # ── File Upload ───────────────────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    UPLOAD_DIR: str = "uploads/"

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    RATE_LIMIT_LOGIN: str = "5/minute"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, v: Any) -> list[str]:
        """Accept JSON array string or Python list."""
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass
            # Comma-separated fallback
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_secret_keys(self) -> "Settings":
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        if len(self.REFRESH_SECRET_KEY) < 32:
            raise ValueError("REFRESH_SECRET_KEY must be at least 32 characters long")
        return self

    @property
    def access_token_expire_seconds(self) -> int:
        return self.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    @property
    def refresh_token_expire_seconds(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024


settings = Settings()
