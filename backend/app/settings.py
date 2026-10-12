"""Runtime configuration, read from environment variables (and .env in development)."""

from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # A missing .env is fine: in containers everything arrives as real env vars.
    model_config = SettingsConfigDict(env_file=REPO_ROOT / ".env", extra="ignore")

    database_url: str = "postgresql+psycopg://skywire:skywire@localhost:5432/skywire"

    # OAuth2 client credentials from the OpenSky account page. Both unset means
    # anonymous access, which has a much smaller daily quota.
    opensky_client_id: str | None = None
    opensky_client_secret: SecretStr | None = None

    # Area to monitor, in decimal degrees (WGS84). Default: Florida.
    bbox_lamin: float = 24.3
    bbox_lamax: float = 31.1
    bbox_lomin: float = -87.7
    bbox_lomax: float = -79.8

    @field_validator("opensky_client_id", "opensky_client_secret", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: object) -> object:
        # .env.example ships these as empty strings, which must mean "not configured".
        return None if value == "" else value

    @model_validator(mode="after")
    def _check(self) -> Self:
        if (self.opensky_client_id is None) != (self.opensky_client_secret is None):
            raise ValueError("set both OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET, or neither")
        if not (-90 <= self.bbox_lamin < self.bbox_lamax <= 90):
            raise ValueError("bounding box needs -90 <= BBOX_LAMIN < BBOX_LAMAX <= 90")
        if not (-180 <= self.bbox_lomin < self.bbox_lomax <= 180):
            raise ValueError("bounding box needs -180 <= BBOX_LOMIN < BBOX_LOMAX <= 180")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
