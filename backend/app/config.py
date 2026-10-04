"""Application configuration, loaded from environment variables / .env."""
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BASE_DIR / ".env", BASE_DIR.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application -------------------------------------------------------
    app_name: str = "AI Virtual Office"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = True
    api_prefix: str = "/api"

    # --- Database ----------------------------------------------------------
    # Defaults to a local SQLite file so the project runs with zero setup.
    # Point at Postgres with e.g.
    #   postgresql+psycopg://postgres:postgres@localhost:5432/virtual_office
    database_url: str = f"sqlite:///{BASE_DIR / 'virtual_office.db'}"
    sql_echo: bool = False

    # --- Security ----------------------------------------------------------
    secret_key: str = "dev-secret-change-me-in-production"
    access_token_expire_minutes: int = 60 * 12
    algorithm: str = "HS256"

    # --- CORS --------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:4173,http://127.0.0.1:5173"

    # --- LLM ---------------------------------------------------------------
    # When no key is present the orchestrator transparently falls back to the
    # built-in heuristic engine, so the whole app still works offline.
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    llm_model: str = Field(default="gemini-3.1-flash-lite", alias="GEMINI_MODEL")
    llm_max_tokens: int = 8000
    llm_timeout_seconds: float = 180.0
    llm_enabled: bool = True
    rate_limit_delay_seconds: float = Field(default=2.0, alias="RATE_LIMIT_DELAY_SECONDS")

    # --- Storage / RAG -----------------------------------------------------
    storage_dir: Path = BASE_DIR / "storage"
    max_upload_bytes: int = 20 * 1024 * 1024  # 20 MB
    chunk_size: int = 1200
    chunk_overlap: int = 150
    retrieval_top_k: int = 6

    # --- Seeding -----------------------------------------------------------
    seed_on_startup: bool = True
    demo_email: str = "founder@northwind.io"
    demo_password: str = "demo1234"

    @field_validator("secret_key", mode="after")
    @classmethod
    def _validate_secret(cls, value: str, info) -> str:
        """A short or default key is fatal in production, a warning elsewhere."""
        environment = (info.data or {}).get("environment", "development")
        weak = len(value.encode()) < 32 or value.startswith("dev-secret") or value == "change-me"

        if weak and environment == "production":
            raise ValueError(
                "SECRET_KEY must be a unique value of at least 32 bytes in production. "
                'Generate one with: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if weak:
            import warnings

            warnings.warn(
                "SECRET_KEY is weak; acceptable for local development only.",
                stacklevel=2,
            )
        return value

    @field_validator("storage_dir", mode="after")
    @classmethod
    def _ensure_storage(cls, value: Path) -> Path:
        value.mkdir(parents=True, exist_ok=True)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_enabled and self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
