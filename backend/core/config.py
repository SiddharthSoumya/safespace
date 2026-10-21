from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SafeSpace Pro"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/safespace.db"
    admin_token: str = "dev-admin-token-change-me"
    fernet_key: str | None = None
    fernet_key_file: str = "data/fernet.key"
    model_path: str = "backend/model_artifacts/harassment_classifier.joblib"
    ticket_prefix: str = "SAFE"
    cors_origins: str = "http://localhost:8501,http://127.0.0.1:8501"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def normalized_database_url(self) -> str:
        url = self.database_url.strip()
        if url.startswith("postgres://"):
            return url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    def validate_runtime(self) -> None:
        if self.app_env.strip().lower() not in {"production", "prod"}:
            return

        if len(self.admin_token) < 32 or self.admin_token == "dev-admin-token-change-me":
            raise RuntimeError("Production requires an ADMIN_TOKEN with at least 32 characters.")

        if not self.fernet_key:
            raise RuntimeError("Production requires FERNET_KEY to be configured.")
        try:
            Fernet(self.fernet_key.encode("utf-8"))
        except (InvalidToken, TypeError, ValueError):
            raise RuntimeError("Production FERNET_KEY must be a valid Fernet key.") from None

        if not self.normalized_database_url.startswith("postgresql+psycopg://"):
            raise RuntimeError("Production requires DATABASE_URL to use PostgreSQL.")
        if "*" in self.cors_origins_list:
            raise RuntimeError("Production CORS_ORIGINS must use explicit origins, not a wildcard.")

    def ensure_data_dirs(self) -> None:
        Path("data").mkdir(parents=True, exist_ok=True)
        Path(self.model_path).parent.mkdir(parents=True, exist_ok=True)
        Path(self.fernet_key_file).parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.validate_runtime()
    settings.ensure_data_dirs()
    return settings
