# VERSION HISTORY v1.3.0 · 2026-09-02 · Configure display-only Arena refresh independently of external agent polling.
# v1.2.0 · 2026-09-02 · Configurable credential lifetime, body/rate limits and activity pagination.
# v1.1.0 · 2026-09-02 · Bound directory pagination and validate configured HTTP locations.
# v1.0.0 · 2026-09-02 · Strict configurable economics; no exchange bank integration.
from decimal import Decimal
import os
from pathlib import Path
import tomllib

from pydantic import BaseModel, ConfigDict, Field, field_validator
from urllib.parse import urlsplit
from typing import Literal

APP_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    environment: Literal['simulation'] = 'simulation'
    currency: Literal['USD'] = 'USD'
    seed_funds: Decimal = Field(default=Decimal('1000'), ge=0)
    trade_fee: Decimal = Field(default=Decimal('.01'), ge=0)
    intelligence_fee: Decimal = Field(default=Decimal('.01'), ge=0)
    minimum_units: int = Field(default=1, ge=1, strict=True)
    maximum_positions: int = Field(default=10, ge=1, strict=True)
    initial_units: int = Field(default=1000, ge=1, strict=True)
    initial_nav: Decimal = Field(default=Decimal('1000'), ge=0)
    price_decimal_places: int = Field(default=10, ge=0, le=18, strict=True)
    directory_url: str
    directory_page_size: int = Field(default=100, ge=1, le=100, strict=True)
    directory_max_pages: int = Field(default=100, ge=1, strict=True)
    provider_timeout_seconds: float = Field(default=15, gt=0)
    connection_expiry_seconds: int = Field(default=300, gt=0, strict=True)
    credential_ttl_seconds: int = Field(default=86400, gt=0, strict=True)
    rate_window_seconds: int = Field(default=60, gt=0, strict=True)
    requests_per_window: int = Field(default=240, gt=0, strict=True)
    max_body_bytes: int = Field(default=32768, gt=0, strict=True)
    activity_page_size: int = Field(default=100, gt=0, strict=True)
    view_poll_seconds: int = Field(default=5, gt=0, le=3600, strict=True)
    max_query_results: int = Field(default=20, gt=0, strict=True)
    intelligence_url: str
    intelligence_mode: Literal['simulated_random', 'external'] = 'simulated_random'

    @field_validator('directory_url', 'intelligence_url')
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        parsed = urlsplit(value)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query:
            raise ValueError('Use an HTTP(S) endpoint without credentials, fragment or query')
        return value


def load_settings(path: Path | None = None) -> Settings:
    source = path or Path(os.environ.get('EP052_CONFIG', APP_ROOT / 'config.toml'))
    return Settings.model_validate(tomllib.loads(source.read_text(encoding='utf-8')))
