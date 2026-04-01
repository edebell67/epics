from pathlib import Path

from sync_engine.config import DEFAULT_CONFIG_PATH, load_sync_config


def test_load_sync_config_uses_publishable_schema_fields() -> None:
    config = load_sync_config()

    assert DEFAULT_CONFIG_PATH == Path.cwd() / "sync_config.json"
    assert config.config_version == 1
    assert config.default_interval_seconds == 300

    target_names = {target.name for target in config.targets}
    assert target_names == {"signals", "trade_results", "strategy_performance"}

    for target in config.targets:
        assert target.enabled is True
        assert target.interval_seconds > 0
        assert target.publishable_fields
        assert all(field not in target.excluded_internal_fields for field in target.publishable_fields)
