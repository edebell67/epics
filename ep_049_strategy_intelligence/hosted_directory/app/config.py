"""Environment-only application settings.

Version history:
- 1.3.0 (2026-09-04): Vendored into EP049 (copy of EP051's app/config.py) so
  EP049 can deploy on its own Render rootDir without depending on EP051's
  filesystem path. These two copies are not auto-synced - a change here
  affecting settings both services read needs to be applied to EP051's
  app/config.py too, by hand.
- 1.2.0 (2026-08-25): Keeps the last verified local snapshot available across weekly refresh gaps.
- 1.1.0 (2026-08-24): Adds trusted identity boundary and intelligence feature settings.
- 1.0.0 (2026-08-23): Local SQL Server and hosted PostgreSQL modes.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    data_backend: str = "sqlserver"
    database_url: str | None = None
    maintenance_database_url: str | None = None
    db_server: str | None = None
    db_name: str = "tradedb"
    db_user: str | None = None
    db_pass: str | None = None
    sync_token: str | None = None
    allowed_origins: str = "http://127.0.0.1:8080,http://localhost:8080"
    max_snapshot_items: int = 2000
    max_snapshot_bytes: int = 50_000_000
    snapshot_max_age_hours: int = 48
    intelligence_user_token: str | None = None
    intelligence_min_regime_samples: int = 5
    intelligence_market_feature_max_age_seconds: int = 129_600
    intelligence_market_feature_weekend_max_age_seconds: int = 345_600
    intelligence_max_query_results: int = 100
    intelligence_catalog_limit: int = 500
    local_intelligence_cache_path: str = "runtime/intelligence_profiles.json"
    local_market_feature_cache_path: str = "runtime/market_features.json"
    # Local evidence is immutable and carries its own as-of timestamp. Keep the
    # last fully validated snapshot readable between scheduled source refreshes
    # instead of making the directory unavailable after a single day.
    local_intelligence_cache_max_age_seconds: int = 604_800
    allow_synchronous_local_fallback: bool = False
    intelligence_profile_cache_seconds: int = 60
    regime_price_capture_root: str | None = r"X:\EDS\TradeApps\breakout\fs\json\live\forex"
    regime_shape_index_dir: str = "runtime/regime_shape_index"
    regime_shape_min_periods: int = 6
    ep052_intelligence_token: str | None = None
    arena_deliveries_path: str = "runtime/arena_intelligence_deliveries.sqlite"
    arena_anomaly_threshold: int = 30
    arena_anomaly_window_seconds: int = 300

    @property
    def cors_origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
