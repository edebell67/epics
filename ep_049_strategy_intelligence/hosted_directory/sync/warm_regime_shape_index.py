"""Operator-run regime-shape index warm-up.

Builds/updates the on-disk day-vector index (runtime/regime_shape_index/<INSTRUMENT>.json)
for every instrument actually traded by strategies in the local intelligence
cache, from the raw tick captures under regime_price_capture_root. Public
requests never trigger this - main.py's /regime/similar-days endpoint only
ever reads the cache these files produce, the same warm-up/read split
warm_local_intelligence.py already uses for the main profile cache.

Version history:
- 1.0.1 (2026-09-04): Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
  epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
- 1.0.0: Original warm-up script.
"""
import argparse, json, time
from pathlib import Path
from app.config import get_settings
from app.intelligence.regime_shape import build_instrument_index


def instruments_from_catalog(settings) -> list[str]:
    cache_path = Path(settings.local_intelligence_cache_path)
    cache_path = cache_path if cache_path.is_absolute() else Path(__file__).resolve().parents[1] / cache_path
    if not cache_path.exists():
        return []
    payload = json.loads(cache_path.read_text(encoding="utf-8"))
    instruments = set()
    for profile in payload.get("profiles", []):
        for name in profile.get("classification", {}).get("instruments", []) or []:
            instruments.add(str(name).upper())
    return sorted(instruments)


def refresh(instruments: list[str] | None = None):
    settings = get_settings()
    root = settings.regime_price_capture_root
    if not root:
        print("regime_price_capture_root is not configured; nothing to do", flush=True)
        return
    root_path = Path(root)
    if not root_path.exists():
        print(f"price capture root not reachable: {root_path}", flush=True)
        return
    targets = instruments or instruments_from_catalog(settings)
    if not targets:
        print("no instruments to index (empty catalog and none passed explicitly)", flush=True)
        return
    index_dir = Path(settings.regime_shape_index_dir)
    index_dir = index_dir if index_dir.is_absolute() else Path(__file__).resolve().parents[1] / index_dir
    for instrument in targets:
        cache_path = index_dir / f"{instrument}.json"
        start = time.time()
        index = build_instrument_index(root_path, instrument, cache_path)
        print(json.dumps({"instrument": instrument, "days_indexed": len(index), "cache": str(cache_path), "seconds": round(time.time() - start, 1)}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instrument", action="append", help="Index only this instrument (repeatable). Default: every instrument in the local intelligence catalog.")
    args = parser.parse_args()
    refresh(args.instrument)


if __name__ == "__main__":
    main()
