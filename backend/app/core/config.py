"""Environment-based settings. No secrets in code; everything comes from env vars (or .env via docker compose)."""
import os
from dataclasses import dataclass, field


def _list(v: str) -> list[str]:
    return [x.strip() for x in v.split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "postgresql+psycopg://krishix:krishix@localhost:5432/krishix"))
    cors_origins: list[str] = field(default_factory=lambda: _list(os.getenv("CORS_ORIGINS", "http://localhost:3000")))
    data_gov_api_key: str | None = field(default_factory=lambda: os.getenv("DATA_GOV_API_KEY") or None)
    geocoder_url: str = field(default_factory=lambda: os.getenv("GEOCODER_URL", "https://nominatim.openstreetmap.org/search"))
    rate_limit_per_min: int = field(default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MIN", "60")))


settings = Settings()
