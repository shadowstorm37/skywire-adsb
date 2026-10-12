"""Runtime configuration, read from environment variables (and .env in development)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # A missing .env is fine: in containers everything arrives as real env vars.
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://skywire:skywire@localhost:5432/skywire"


@lru_cache
def get_settings() -> Settings:
    return Settings()
