from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    base = Path(__file__).resolve().parents[1] / "solution" / "transparency"
    schema = json.loads((base / "public_transparency_contract.schema.json").read_text())
    example = json.loads((base / "public_transparency_snapshot.example.json").read_text())
    rows = list(
        csv.DictReader((base / "public_transparency_field_catalog.csv").read_text().splitlines())
    )
    disclosure = (base / "public_transparency_disclosure_pack.md").read_text()

    required_fields = {
        "vault_capital",
        "long_short_imbalance",
        "open_interest",
        "current_leverage_band",
        "funding_rate",
        "volatility_metric",
        "risk_parameter_band",
        "market_status",
    }

    schema_fields = set(schema["properties"])
    missing_schema = sorted(required_fields - schema_fields)
    assert not missing_schema, f"missing schema fields: {missing_schema}"

    example_fields = set(example)
    missing_example = sorted(required_fields - example_fields)
    assert not missing_example, f"missing example fields: {missing_example}"

    catalog_top = {row["public_field"]: row for row in rows if row["field_scope"] == "top_level"}
    missing_catalog = sorted(required_fields - set(catalog_top))
    assert not missing_catalog, f"missing top-level catalog rows: {missing_catalog}"
    for field, row in catalog_top.items():
        assert row["upstream_owner"].strip(), f"missing owner for {field}"
        assert row["update_cadence"].strip(), f"missing cadence for {field}"

    for heading in [
        "### `vault_capital`",
        "### `long_short_imbalance`",
        "### `open_interest`",
        "### `current_leverage_band`",
        "### `funding_rate`",
        "### `volatility_metric`",
        "### `risk_parameter_band`",
        "### `market_status`",
        "## Formula Transparency Principle",
    ]:
        assert heading in disclosure, f"missing disclosure section: {heading}"

    assert "Redaction boundary:" in disclosure, "missing redaction boundary wording"
    assert "Formula disclosure:" in disclosure, "missing formula disclosure wording"
    print("validation_passed")


if __name__ == "__main__":
    main()
