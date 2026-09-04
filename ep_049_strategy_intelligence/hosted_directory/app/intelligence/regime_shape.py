"""Intraday price-shape regime vectors, built from raw tick captures.

VERSION HISTORY
v1.0.1 (2026-09-04) - Relocated from epics/ep_051_strategy_directory/hosted_directory/ to
epics/ep_049_strategy_intelligence/hosted_directory/ per Ed's EP049 ownership decision. No code changes.
v1.0.0 - Replaces the coarse bull/bear/sideways x volatility label with a
continuous per-instrument shape: 24 hourly [open%,high%,low%] triples
relative to the day's opening mid price. A "regime" is this 72-number
vector, not a category - so two days can be compared by distance, and
"similar regimes" found by nearest-neighbour search, including against a
partial (in-progress) day.
"""
from __future__ import annotations
import json, statistics
from datetime import datetime, date, time, timezone
from pathlib import Path

PERIOD_MINUTES = 60
PERIODS_PER_DAY = 24
MAX_TICK_DEVIATION = 0.02  # a tick more than 2% from its hour's running median is treated as a bad capture, not a real move


def _mid(quote: dict) -> float | None:
    bid = quote.get("bid")
    ask = quote.get("ask")
    if bid is None or ask is None:
        return None
    return (float(bid) + float(ask)) / 2.0


def read_ticks(path: Path, instrument: str) -> list[tuple[datetime, float]]:
    """Read one day's _price_capture.jsonl and extract (timestamp, mid) for
    one instrument key (e.g. "GBPAUD_C"), skipping ticks that don't quote it."""
    key = instrument.upper()
    ticks = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except ValueError:
                continue
            quote = row.get(key)
            if quote is None:
                continue
            mid = _mid(quote)
            if mid is None:
                continue
            ts = row.get("ts")
            if not ts:
                continue
            try:
                stamp = datetime.fromisoformat(ts)
            except ValueError:
                continue
            ticks.append((stamp, mid))
    ticks.sort(key=lambda item: item[0])
    return ticks


def build_day_vector(ticks: list[tuple[datetime, float]], through_hour: int | None = None) -> list[list[float]] | None:
    """Build the 24x[open%,high%,low%] vector (or a prefix p0..p<through_hour>
    for an in-progress day) from one day's (timestamp, mid) ticks, all
    already restricted to a single UTC calendar day. Returns None if there
    are no ticks to anchor the day's opening price to."""
    if not ticks:
        return None
    day_open = ticks[0][1]
    if day_open == 0:
        return None
    limit = PERIODS_PER_DAY if through_hour is None else min(PERIODS_PER_DAY, through_hour + 1)
    buckets: list[list[float]] = [[] for _ in range(limit)]
    for stamp, mid in ticks:
        hour = stamp.hour
        if hour >= limit:
            continue
        buckets[hour].append(mid)
    vector = []
    for hour, prices in enumerate(buckets):
        clean = _drop_outliers(prices)
        if not clean:
            vector.append(None)
            continue
        open_price = clean[0] if hour > 0 else day_open
        open_pct = (open_price - day_open) / day_open * 100.0
        high_pct = (max(clean) - day_open) / day_open * 100.0
        low_pct = (min(clean) - day_open) / day_open * 100.0
        vector.append([round(open_pct, 4), round(high_pct, 4), round(low_pct, 4)])
    return vector


def _drop_outliers(prices: list[float]) -> list[float]:
    """A single bad tick (a capture glitch, not a real price move) can blow
    the hour's high/low out by orders of magnitude. Filter any price more
    than MAX_TICK_DEVIATION from the hour's median before taking high/low/open."""
    if len(prices) < 3:
        return prices
    median = statistics.median(prices)
    if median <= 0:
        return prices
    return [p for p in prices if abs(p - median) / median <= MAX_TICK_DEVIATION] or prices


def build_day_vector_for_date(root: Path, instrument: str, day: date, through_hour: int | None = None) -> list[list[float]] | None:
    folder = root / day.isoformat()
    path = folder / "_price_capture.jsonl"
    if not path.exists():
        return None
    ticks = [(stamp, mid) for stamp, mid in read_ticks(path, instrument) if stamp.date() == day]
    return build_day_vector(ticks, through_hour)


def vector_distance(a: list, b: list) -> float | None:
    """Euclidean distance over whichever hourly periods both vectors have
    (missing/None hours on either side are skipped), so a partial in-progress
    day can be compared against full historical days over just the shared
    prefix. Returns None if there is no overlap."""
    total = 0.0
    count = 0
    for left, right in zip(a, b):
        if left is None or right is None:
            continue
        for lv, rv in zip(left, right):
            total += (lv - rv) ** 2
            count += 1
    if count == 0:
        return None
    return (total / count) ** 0.5


def list_available_days(root: Path) -> list[str]:
    """Every YYYY-MM-DD day-folder under the price-capture root that has a
    _price_capture.jsonl file, sorted."""
    if not root.exists():
        return []
    days = []
    for entry in root.iterdir():
        if entry.is_dir() and len(entry.name) == 10 and entry.name[4] == "-" and (entry / "_price_capture.jsonl").exists():
            days.append(entry.name)
    return sorted(days)


def load_index(cache_path: Path) -> dict[str, list]:
    if not cache_path.exists():
        return {}
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return {}


def save_index(cache_path: Path, index: dict[str, list]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")
    temporary.replace(cache_path)


def build_instrument_index(root: Path, instrument: str, cache_path: Path, refresh_last_n_days: int = 2) -> dict[str, list]:
    """Build/update the on-disk day-vector index for one instrument. Historical
    days already in the cache are immutable and skipped (their price capture
    is complete and won't change); the most recent `refresh_last_n_days` are
    always recomputed, since "today" is still in progress and "yesterday"
    may have finished writing after it was last cached. Persists after every
    change so a long first build can be interrupted and resumed."""
    index = load_index(cache_path)
    available = list_available_days(root)
    stale = set(available[-refresh_last_n_days:]) if refresh_last_n_days > 0 else set()
    changed = False
    for day_str in available:
        if day_str in index and day_str not in stale:
            continue
        vector = build_day_vector_for_date(root, instrument, date.fromisoformat(day_str))
        if vector is not None:
            index[day_str] = vector
            changed = True
    if changed:
        save_index(cache_path, index)
    return index


def find_similar_days(target: list, indexed: dict[str, list], min_periods: int = 6) -> list[dict]:
    """Rank every indexed day (date-string -> vector) by distance to `target`.
    `target` may be a full or partial-day vector; indexed days are always
    matched over their overlapping prefix with `target`. A day matched on
    only a handful of overlapping hours is noise, not a real shape match, so
    `min_periods` (default 6 - a quarter of a day) excludes those rather than
    letting a 1-hour coincidence rank above a genuine multi-hour match."""
    results = []
    for day_key, vector in indexed.items():
        distance = vector_distance(target, vector)
        if distance is None:
            continue
        periods_compared = sum(1 for l, r in zip(target, vector) if l is not None and r is not None)
        if periods_compared < min_periods:
            continue
        results.append({"date": day_key, "distance": round(distance, 4), "periods_compared": periods_compared})
    results.sort(key=lambda row: row["distance"])
    return results
