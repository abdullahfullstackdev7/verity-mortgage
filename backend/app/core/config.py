from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "local"
    database_url: str = (
        "postgresql+psycopg://verity:verity_dev_password@localhost:5434/verity_mortgage"
    )

    jwt_secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 20
    refresh_token_expire_days: int = 14

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    document_storage_dir: str = str(REPO_ROOT / "data" / "documents" / "uploaded")
    max_upload_size_bytes: int = 10 * 1024 * 1024  # 10 MB


settings = Settings()
