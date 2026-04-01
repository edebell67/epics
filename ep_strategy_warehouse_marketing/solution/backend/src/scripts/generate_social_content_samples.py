from __future__ import annotations

import json
from pathlib import Path
import sys


CURRENT_FILE = Path(__file__).resolve()
BACKEND_ROOT = CURRENT_FILE.parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.schemas.content_schema import PublishableContent
from src.services.contentGeneratorService import ContentGeneratorService, StrategyWarehouseDataLoader


def main() -> None:
    project_root = Path(__file__).resolve().parents[4]
    data_root = project_root.parent / "TradeApps" / "breakout" / "fs" / "json" / "live" / "forex"
    verification_dir = project_root / "verification"
    schema_dir = project_root / "solution" / "backend" / "src" / "schemas"
    verification_dir.mkdir(parents=True, exist_ok=True)

    loader = StrategyWarehouseDataLoader(data_root)
    warehouse_data = loader.load_snapshot_bundle()
    service = ContentGeneratorService()
    bundle = service.generate_campaign_bundle(warehouse_data)

    output_path = verification_dir / "generated_social_content_samples.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(bundle, handle, indent=2)

    schema_path = schema_dir / "publishable_content_schema.json"
    with schema_path.open("w", encoding="utf-8") as handle:
        json.dump(PublishableContent.model_json_schema(), handle, indent=2)

    print(f"Wrote {output_path}")
    print(f"Wrote {schema_path}")


if __name__ == "__main__":
    main()
