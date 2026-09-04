"""SQL Server source adapter and PostgreSQL snapshot repository.

Version history:
- 1.11.0 (2026-09-04): Threads alt_net_return through current_equity_curve/current_equity_curves on both MemoryRepository and PostgresRepository, so return_basis="alt_net_return" queries work on those backends too.
- 1.10.0 (2026-08-31): Adds local_rank_journey() - a canonical strategy's
  exact rank among all active strategies at the instant right after each
  of its own trades closes, distinct from the periodic
  ep051_strategy_rank_history snapshots (which only capture at whatever
  interval the capture script runs, not exactly when a trade closes).
- 1.9.0 (2026-08-28): Adds begin_snapshot/add_snapshot_batch/finalize_snapshot to
  MemoryRepository and PostgresRepository - the staged, batched ingestion path
  (PUB-04) that replaces one large synchronous promote() call with several
  small ones. begin_snapshot creates a 'staged' row; add_snapshot_batch
  inserts chunks of items/profiles/return_series idempotently (ON CONFLICT DO
  NOTHING, safe against retries); finalize_snapshot verifies the received row
  count matches the declared item_count, reassembles the full Snapshot from
  the staged rows, runs the exact same verified() reconciliation promote()
  always ran, then does the identical staged->current/retained flip in one
  transaction. promote() itself is unchanged and still used directly by
  finalize_snapshot on MemoryRepository, and by anything still calling it.
- 1.7.3 (2026-08-28): Exposes nullable source alt_net_return in the closed-trade ledger.
- 1.8.0 (2026-08-28): Removes every product_forex reference from this file (AGGREGATE_SQL, local_products, local_period_strategies, local_strategy_summary), now that combined_trades_closed/open carry strategy_name and product directly (backfilled + trigger-populated on tradedb). Untraded strategies (product_forex-only, no closed trades) are no longer part of the directory population - a deliberate scope decision, not an oversight. Deleted local_constructed_strategy_count(), which was already dead code (defined, never called).
- 1.7.3 (2026-08-28): local_equity_curves() now returns the real trade guid (cast to a plain string) instead of dropping it, and every tie-break ORDER BY in that query uses the same cast guid consistently. Fixes Snapshot.verified() rejecting real exports on same-timestamp trades, where the missing guid forced a trade_number-based fallback ID that didn't match the order SQL actually used.
- 1.7.2 (2026-08-28): Reads exact-strategy evidence without SQL aggregates, with a 10s query timeout, to avoid broad historical detail work.
- 1.7.1 (2026-08-25): Filters combined_trades_closed on the indexed model_ix column instead of the
  unindexed varchar(max) model column, avoiding a 1M+ row scan on every evidence query.
- 1.7.0 (2026-08-25): Adds period execution counts across open and closed trades, deduplicated by guid.
- 1.6.1 (2026-08-25): Exposes the exact constructed-model count from product_forex for reference totals.
- 1.6.0 (2026-08-25): Defines the canonical directory population from product_forex and overlays closed-trade evidence.
- 1.5.2 (2026-08-25): Supports Windows trusted authentication for local SQL Server when explicit credentials are absent.
- 1.5.1 (2026-08-25): Adds streaming period aggregation so fresh day filters avoid SQL Server group-memory grants.
- 1.5.0 (2026-08-24): Resolves canonical strategy names from product_forex.strategy_name.
- 1.4.0 (2026-08-24): Adds one-query canonical equity-series loading for intelligence profiles.
- 1.3.0 (2026-08-24): Publishes distinct source product names with strategy aggregates.
- 1.2.0 (2026-08-24): Adds canonical, period-aware cumulative equity points for strategy charts.
- 1.1.0 (2026-08-24): Adds bounded closed-date filtering for day, week, month and custom evidence periods.
- 1.0.0 (2026-08-23): Read-only local aggregation and atomic hosted promotion.
"""
from __future__ import annotations

from bisect import bisect_right
from contextlib import closing
from typing import Any

from .contracts import Snapshot


def rebase_equity_rows(rows):
    equity=peak=0.0;output=[]
    for number,row in enumerate(rows,1):
        value=float(row["net_return"]);equity+=value;peak=max(peak,equity);output.append({**row,"trade_number":number,"equity":equity,"drawdown":equity-peak})
    return output

MAX_EQUITY_POINTS = 5000
MAX_PROFILE_POINTS = 1000

AGGREGATE_SQL = """
WITH universe AS (
 SELECT CASE WHEN RIGHT(model,2) IN ('_B','_S') THEN LEFT(model,LEN(model)-2) ELSE model END strategy_id,
        MAX(NULLIF(LTRIM(RTRIM(strategy_name)),'')) descriptive_name
 FROM dbo.combined_trades_closed WITH (NOLOCK)
 WHERE model_ix LIKE 'DNA[_]%'
 GROUP BY CASE WHEN RIGHT(model,2) IN ('_B','_S') THEN LEFT(model,LEN(model)-2) ELSE model END
), universe_products AS (
 SELECT strategy_id, STRING_AGG(product, ', ') product_name
 FROM (
   SELECT DISTINCT CASE WHEN RIGHT(model,2) IN ('_B','_S') THEN LEFT(model,LEN(model)-2) ELSE model END strategy_id, product
   FROM dbo.combined_trades_closed WITH (NOLOCK) WHERE model_ix LIKE 'DNA[_]%' AND product IS NOT NULL
 ) source_products
 GROUP BY strategy_id
), canonical AS (
 SELECT CASE WHEN RIGHT(model,2) IN ('_B','_S') THEN LEFT(model,LEN(model)-2) ELSE model END strategy_id,
        CAST(net_return AS float) net_return, product, created, COALESCE(g_close_time,last_update,created) closed_at, guid
 FROM dbo.combined_trades_closed
 WHERE model_ix LIKE 'DNA[_]%' AND net_return IS NOT NULL
   {date_filters}
), evidence AS (
 SELECT strategy_id, COUNT_BIG(*) total_trades,
 SUM(CASE WHEN net_return>0 THEN 1 ELSE 0 END) wins,
 SUM(CASE WHEN net_return<0 THEN 1 ELSE 0 END) losses,
 SUM(CASE WHEN net_return=0 THEN 1 ELSE 0 END) breakevens,
 SUM(net_return) total_net_return,
 SUM(CASE WHEN net_return>0 THEN net_return ELSE 0 END) gross_profit,
 ABS(SUM(CASE WHEN net_return<0 THEN net_return ELSE 0 END)) gross_loss,
 MIN(created) evidence_start, MAX(closed_at) evidence_end
 FROM canonical GROUP BY strategy_id
)
SELECT universe.strategy_id, universe.descriptive_name, universe_products.product_name,
 COALESCE(evidence.total_trades,0) total_trades, COALESCE(evidence.wins,0) wins,
 COALESCE(evidence.losses,0) losses, COALESCE(evidence.breakevens,0) breakevens,
 CAST(COALESCE(evidence.total_net_return,0) AS decimal(28,8)) total_net_return,
 CAST(COALESCE(CAST(evidence.wins AS decimal(28,10))/NULLIF(evidence.total_trades,0),0) AS decimal(18,10)) win_rate,
 CAST(evidence.gross_profit/NULLIF(evidence.gross_loss,0) AS decimal(18,10)) profit_factor,
 CAST(NULL AS decimal(28,8)) max_drawdown_money,
 evidence.evidence_start, evidence.evidence_end
FROM universe
LEFT JOIN universe_products ON universe_products.strategy_id=universe.strategy_id
LEFT JOIN evidence ON evidence.strategy_id=universe.strategy_id
{strategy_filter}
ORDER BY universe.strategy_id
"""


def sqlserver_connection(settings):
    import pyodbc
    if not settings.db_server:
        raise RuntimeError("Missing local SQL setting: db_server")
    value = ("DRIVER={ODBC Driver 17 for SQL Server};SERVER=" + settings.db_server +
             ";DATABASE=" + settings.db_name)
    if settings.db_user and settings.db_pass:
        value += ";UID=" + settings.db_user + ";PWD=" + settings.db_pass
    elif not settings.db_user and not settings.db_pass:
        value += ";Trusted_Connection=yes"
    else:
        raise RuntimeError("Set both db_user and db_pass, or neither for Windows trusted authentication")
    return pyodbc.connect(value, timeout=10)


def local_execution_summary(settings, date_from=None, date_to_exclusive=None) -> dict[str, int]:
    """Count distinct executed models and trades opened within a half-open period."""
    date_filters, date_params = [], []
    if date_from is not None:
        date_filters.append("created >= ?")
        date_params.append(date_from)
    if date_to_exclusive is not None:
        date_filters.append("created < ?")
        date_params.append(date_to_exclusive)
    date_where = "".join(f" AND {clause}" for clause in date_filters)
    # combined_trades_open has no model_ix column (table is small; scan cost is negligible).
    # combined_trades_closed carries 1M+ rows, so its DNA prefix filter must use the indexed
    # model_ix column instead of the unindexed varchar(max) model column.
    open_where = "model LIKE 'DNA[_]%'" + date_where
    closed_where = "model_ix LIKE 'DNA[_]%'" + date_where
    query = f"""
      WITH executed AS (
        SELECT guid,model FROM dbo.combined_trades_open WITH (NOLOCK) WHERE {open_where}
        UNION
        SELECT guid,model FROM dbo.combined_trades_closed WITH (NOLOCK) WHERE {closed_where}
      )
      SELECT COUNT_BIG(DISTINCT model),COUNT_BIG(DISTINCT guid) FROM executed
    """
    with closing(sqlserver_connection(settings)) as conn:
        row = conn.cursor().execute(query, *(date_params + date_params)).fetchone()
    return {"strategies": int(row[0]), "trades": int(row[1])}


def local_open_trade_summary(settings, canonical_strategy=None) -> dict[str, dict[str, Any]]:
    """Aggregate currently-open positions per canonical strategy: count and
    unrealized (mark-to-market) net_return. Open positions have no close
    date, so this has no period-filtering concept - it's always a
    current-moment snapshot, unlike the closed-trade evidence queries above.
    combined_trades_open has no model_ix column (small table; unindexed
    LIKE scan cost is negligible, unlike the 1M+ row combined_trades_closed)."""
    filters, params = [], []
    if canonical_strategy is not None:
        filters.append("AND model IN (?,?,?)")
        params.extend([canonical_strategy, canonical_strategy + "_B", canonical_strategy + "_S"])
    query = f"""
      SELECT model,product,NULLIF(LTRIM(RTRIM(strategy_name)),''),CAST(net_return AS float) net_return
      FROM dbo.combined_trades_open WITH (NOLOCK)
      WHERE model LIKE 'DNA[_]%' AND net_return IS NOT NULL {' '.join(filters)}
      OPTION (MAXDOP 1)
    """
    grouped: dict[str, dict[str, Any]] = {}
    with closing(sqlserver_connection(settings)) as conn:
        cur = conn.cursor()
        cur.execute(query, *params)
        for model, product, descriptive_name, net_return in cur:
            strategy_id = model[:-2] if model.endswith(("_B", "_S")) else model
            row = grouped.setdefault(strategy_id, {"open_trades": 0, "open_net_return": 0.0, "products": set(), "descriptive_name": None})
            row["open_trades"] += 1
            row["open_net_return"] += float(net_return)
            if product: row["products"].add(product)
            if descriptive_name: row["descriptive_name"] = descriptive_name
    for row in grouped.values():
        row["product_name"] = ", ".join(sorted(row.pop("products"))) or None
    return grouped


def local_rank_journey(settings, strategy_id, date_from, date_to_exclusive) -> list[dict[str, Any]]:
    """For one canonical strategy, its exact rank among every strategy
    active in [date_from, date_to_exclusive) at the instant right after
    each of its own trades closed - computed live in Python from a single
    plain scan of the day's closed trades, not read from a periodic
    snapshot.

    This was the original design, set aside earlier for a snapshot-table
    read (dbo.ep051_strategy_rank_history) after the full computation
    appeared to cost ~150s under SQL Server contention. That estimate was
    wrong about where the cost actually was: several SQL-side rewrites
    aimed at cutting that cost (an incremental running-totals table, a
    window-function "carry forward" cross join, a CROSS APPLY as-of join)
    were each either measurably slower or produced wrong results (see git
    history and the night's investigation), while a plain unindexed-scan
    SELECT of the day's trades - no joins, no window functions - measured
    at 0.30s fetch + 0.018s Python compute once contention eased. The
    query itself was never the expensive part; SQL Server's own
    contention was, and every SQL-side query paid that same queueing cost
    regardless of its own complexity, no more cheaply than this one.

    total_strategies here counts every strategy with at least one closed
    trade in the window (the population being ranked), not the open-trade
    count used in earlier iterations of this function - that was itself a
    stand-in adopted while the snapshot-table read couldn't state its own
    population size correctly; now that ranking is computed directly from
    this same trade set, its own size is the right denominator."""
    query = """
      SELECT CASE WHEN RIGHT(model,2) IN ('_B','_S') THEN LEFT(model,LEN(model)-2) ELSE model END strategy_id,
             CAST(net_return AS float) net_return, COALESCE(g_close_time,last_update,created) closed_at
      FROM dbo.combined_trades_closed WITH (NOLOCK)
      WHERE model_ix LIKE 'DNA[_]%' AND net_return IS NOT NULL AND created >= ? AND created < ?
      OPTION (MAXDOP 1)
    """
    with closing(sqlserver_connection(settings)) as conn:
        cur = conn.cursor()
        cur.execute(query, date_from, date_to_exclusive)
        rows = cur.fetchall()
    by_strategy: dict[str, list] = {}
    for sid, net_return, closed_at in rows:
        by_strategy.setdefault(sid, []).append((closed_at, net_return))
    cumulative: dict[str, tuple[list, list]] = {}
    for sid, points in by_strategy.items():
        points.sort(key=lambda p: p[0])
        times = [p[0] for p in points]
        running = 0.0
        cum = []
        for _, net_return in points:
            running += net_return
            cum.append(running)
        cumulative[sid] = (times, cum)
    target_times, target_cum = cumulative.get(strategy_id, ([], []))
    journey = []
    for index, closed_at in enumerate(target_times):
        target_value = target_cum[index]
        higher = 0
        for sid, (times, cum) in cumulative.items():
            position = bisect_right(times, closed_at) - 1
            if position >= 0 and cum[position] > target_value:
                higher += 1
        journey.append({
            "trade_number": index + 1, "closed_at": closed_at.isoformat(),
            "cumulative_net_return": target_value,
            "rank_position": higher + 1, "total_strategies": len(cumulative),
        })
    return journey


def local_strategies(settings, date_from=None, date_to_exclusive=None, canonical_strategy=None, signal=None) -> list[dict[str, Any]]:
    """Aggregate canonical strategies within an optional half-open closed-date range."""
    if canonical_strategy is not None:
        return local_strategy_summary(settings, canonical_strategy, date_from, date_to_exclusive, signal)
    filters, params = [], []
    if date_from is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) >= ?")
        params.append(date_from)
    if date_to_exclusive is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) < ?")
        params.append(date_to_exclusive)
    if signal is not None:
        filters.append("AND UPPER(LTRIM(RTRIM(signal))) = ?")
        params.append(signal)
    strategy_filter = ""
    if canonical_strategy is not None:
        strategy_filter = "WHERE universe.strategy_id = ?"
        params.append(canonical_strategy)
    query = AGGREGATE_SQL.format(date_filters=" ".join(filters), strategy_filter=strategy_filter)
    with closing(sqlserver_connection(settings)) as conn:
        cur = conn.cursor()
        cur.execute(query, *params)
        columns = [x[0] for x in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    for row in rows:
        for key in ("total_net_return", "win_rate", "profit_factor", "max_drawdown_money"):
            row[key] = float(row[key]) if row[key] is not None else None
        for key in ("evidence_start", "evidence_end"):
            row[key] = row[key].isoformat() if row.get(key) else None
        row.update(market="FX", status="active",
                   quality_state="VALID" if row["total_trades"] >= 30 else "COLLECTING")
    if date_from is None and date_to_exclusive is None:
        # Open positions have no close date - only attach them to the
        # unfiltered "current state" view, not a historical evidence window.
        open_summary = local_open_trade_summary(settings)
        seen = set()
        for row in rows:
            seen.add(row["strategy_id"])
            open_row = open_summary.get(row["strategy_id"])
            row["open_trades"] = open_row["open_trades"] if open_row else 0
            row["open_net_return"] = open_row["open_net_return"] if open_row else 0.0
        # A strategy can have open positions but zero closed trades ever -
        # it would otherwise be entirely absent, since `universe` above is
        # built exclusively from combined_trades_closed. Synthesize a
        # zero-closed-evidence row for it instead of silently dropping it.
        for strategy_id, open_row in open_summary.items():
            if strategy_id in seen:
                continue
            rows.append({
                "strategy_id": strategy_id, "descriptive_name": open_row.get("descriptive_name"),
                "product_name": open_row.get("product_name"), "market": "FX", "status": "active",
                "total_trades": 0, "wins": 0, "losses": 0, "breakevens": 0,
                "total_net_return": 0.0, "win_rate": 0.0, "profit_factor": None,
                "max_drawdown_money": None, "evidence_start": None, "evidence_end": None,
                "quality_state": "COLLECTING",
                "open_trades": open_row["open_trades"], "open_net_return": open_row["open_net_return"],
            })
    return rows


def local_strategy_summary(settings, strategy_id, date_from=None, date_to_exclusive=None, signal=None):
    """Read only one model's catalogue and evidence, without SQL aggregation grants."""
    models = [strategy_id, strategy_id + "_B", strategy_id + "_S"]
    placeholders = "CONVERT(varchar(200),?),CONVERT(varchar(200),?),CONVERT(varchar(200),?)"
    filters = []
    params = list(models)
    if date_from is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) >= ?")
        params.append(date_from)
    if date_to_exclusive is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) < ?")
        params.append(date_to_exclusive)
    if signal is not None:
        filters.append("AND UPPER(LTRIM(RTRIM(signal))) = ?")
        params.append(signal)
    with closing(sqlserver_connection(settings)) as conn:
        conn.timeout = 10
        cur = conn.cursor()
        cur.execute(f"""SELECT CAST(net_return AS float),created,COALESCE(g_close_time,last_update,created),strategy_name,product
            FROM dbo.combined_trades_closed WHERE model_ix IN ({placeholders})
            AND net_return IS NOT NULL {' '.join(filters)} OPTION (MAXDOP 1, RECOMPILE)""", *params)
        trades = cur.fetchall()
    if not trades:
        return []
    values = [float(row[0]) for row in trades]
    wins = sum(value > 0 for value in values)
    losses = sum(value < 0 for value in values)
    gross_profit = sum(value for value in values if value > 0)
    gross_loss = -sum(value for value in values if value < 0)
    names = [str(row[3]).strip() for row in trades if row[3] and str(row[3]).strip()]
    products = sorted({str(row[4]) for row in trades if row[4] is not None})
    starts = [row[1] for row in trades if row[1] is not None]
    ends = [row[2] for row in trades if row[2] is not None]
    return [dict(strategy_id=strategy_id, descriptive_name=max(names) if names else None,
                 product_name=", ".join(products) or None, total_trades=len(values),
                 wins=wins, losses=losses, breakevens=len(values)-wins-losses,
                 total_net_return=sum(values), win_rate=wins/len(values) if values else 0,
                 profit_factor=gross_profit/gross_loss if gross_loss else None,
                 max_drawdown_money=None, evidence_start=min(starts) if starts else None,
                 evidence_end=max(ends) if ends else None, market="FX", status="active",
                 quality_state="VALID" if len(values)>=30 else "COLLECTING")]


def local_products(settings) -> list[str]:
    """Return canonical DNA product filter values from actually-traded strategies."""
    query = """
      SELECT DISTINCT UPPER(LTRIM(RTRIM(product))) product
      FROM dbo.combined_trades_closed WITH (NOLOCK)
      WHERE model_ix LIKE 'DNA[_]%'
        AND NULLIF(LTRIM(RTRIM(product)),'') IS NOT NULL
      ORDER BY product
    """
    with closing(sqlserver_connection(settings)) as conn:
        return [str(row[0]) for row in conn.cursor().execute(query).fetchall()]


def local_period_strategies(settings, date_from, date_to_exclusive, canonical_strategy=None, signal=None) -> list[dict[str, Any]]:
    """Return the population with evidence for trades entered in the period."""
    # Directory periods are entry-date cohorts.  Using the close timestamp here
    # made the headline disagree with direct combined_trades_closed entry-date
    # counts and caused trades opened today but closed later to move periods.
    filters = ["created >= ?", "created < ?"]
    params = [date_from, date_to_exclusive]
    if signal is not None:
        filters.append("UPPER(LTRIM(RTRIM(signal))) = ?")
        params.append(signal)
    if canonical_strategy is not None:
        filters.append("model IN (?,?,?)")
        params.extend([canonical_strategy, canonical_strategy + "_B", canonical_strategy + "_S"])
    query = f"""
      SELECT model,product,CAST(net_return AS float) net_return,created,
             COALESCE(g_close_time,last_update,created) closed_at
      FROM dbo.combined_trades_closed WITH (NOLOCK)
      WHERE model_ix LIKE 'DNA[_]%' AND net_return IS NOT NULL AND {' AND '.join(filters)}
      OPTION (MAXDOP 1)
    """
    # Keep this as a grant-free row read. SQL Server can otherwise leave the
    # directory waiting on RESOURCE_SEMAPHORE while STRING_AGG sorts the model
    # catalogue alongside the live trade procedures.
    # No DISTINCT/GROUP BY here on purpose: this table has one row per trade
    # (up to ~123k), not one row per strategy like the old product_forex
    # source did. A SQL-side DISTINCT would ask the optimizer for a memory
    # grant sized off all matching rows before it knows the low real
    # cardinality - exactly the RESOURCE_SEMAPHORE risk the comment below
    # already warns about. Plain unaggregated rows keep this a pure
    # sequential read; the existing Python dict below already dedupes by
    # strategy_id for free as it groups.
    population_query = """
      SELECT model,NULLIF(LTRIM(RTRIM(strategy_name)),''),product
      FROM dbo.combined_trades_closed WITH (NOLOCK)
      WHERE model_ix LIKE 'DNA[_]%'
    """
    population_params = []
    if canonical_strategy is not None:
        population_query += " AND model IN (?,?,?)"
        population_params.extend([canonical_strategy, canonical_strategy + "_B", canonical_strategy + "_S"])
    grouped = {}
    with closing(sqlserver_connection(settings)) as conn:
        cur = conn.cursor(); cur.execute(population_query, *population_params)
        for model, descriptive_name, product in cur:
            strategy_id = model[:-2] if model.endswith(("_B", "_S")) else model
            row = grouped.setdefault(strategy_id, {
                "strategy_id": strategy_id, "descriptive_name": None,
                "products": set(), "total_trades": 0, "wins": 0,
                "losses": 0, "breakevens": 0, "total_net_return": 0.0,
                "gross_profit": 0.0, "gross_loss": 0.0,
                "evidence_start": None, "evidence_end": None,
            })
            if descriptive_name: row["descriptive_name"] = descriptive_name
            if product: row["products"].add(product)
        cur.execute(query, *params)
        for model, product, net_return, created, closed_at in cur:
            strategy_id = model[:-2] if model.endswith(("_B", "_S")) else model
            row = grouped.get(strategy_id)
            if row is None: continue
            value = float(net_return); row["total_trades"] += 1; row["total_net_return"] += value
            row["wins"] += value > 0; row["losses"] += value < 0; row["breakevens"] += value == 0
            row["gross_profit"] += max(value, 0); row["gross_loss"] += abs(min(value, 0))
            if product: row["products"].add(product)
            row["evidence_start"] = created if row["evidence_start"] is None else min(row["evidence_start"], created)
            row["evidence_end"] = closed_at if row["evidence_end"] is None else max(row["evidence_end"], closed_at)
    output = []
    for row in grouped.values():
        count = row["total_trades"]; gross_loss = row.pop("gross_loss"); gross_profit = row.pop("gross_profit")
        products = row.pop("products")
        row.update(product_name=", ".join(sorted(products)) or None, market="FX", status="active",
                   win_rate=row["wins"] / count if count else 0.0,
                   profit_factor=gross_profit / gross_loss if gross_loss else None,
                   max_drawdown_money=None, quality_state="VALID" if count >= 30 else "COLLECTING")
        output.append(row)
    return sorted(output, key=lambda row: row["strategy_id"])


def local_equity_curve(settings, strategy_id: str, date_from=None, date_to_exclusive=None) -> list[dict[str, Any]]:
    """Return ordered cumulative net-return and drawdown points for one canonical strategy."""
    filters, params = [], [MAX_EQUITY_POINTS, strategy_id, strategy_id + "_B", strategy_id + "_S"]
    if date_from is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) >= ?")
        params.append(date_from)
    if date_to_exclusive is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) < ?")
        params.append(date_to_exclusive)
    query = f"""
    WITH trades AS (
      SELECT TOP (?) COALESCE(g_close_time,last_update,created) closed_at, created opened_at, created, guid, CAST(net_return AS float) net_return,
        UPPER(LTRIM(RTRIM(signal))) signal
      FROM dbo.combined_trades_closed
      WHERE model_ix IN (?,?,?) AND net_return IS NOT NULL {' '.join(filters)}
      ORDER BY COALESCE(g_close_time,last_update,created) DESC, created DESC, guid DESC
    ), equity AS (
      SELECT closed_at, opened_at, guid, net_return, signal,
        SUM(net_return) OVER(ORDER BY closed_at,created,guid ROWS UNBOUNDED PRECEDING) equity
      FROM trades
    ), curve AS (
      SELECT closed_at,opened_at,guid,net_return,signal,equity,
        equity-CASE WHEN MAX(equity) OVER(ORDER BY closed_at,guid ROWS UNBOUNDED PRECEDING)>0 THEN MAX(equity) OVER(ORDER BY closed_at,guid ROWS UNBOUNDED PRECEDING) ELSE 0 END drawdown,
        ROW_NUMBER() OVER(ORDER BY closed_at,guid) trade_number
      FROM equity
    )
    SELECT trade_number,opened_at,closed_at,net_return,signal,equity,drawdown FROM curve ORDER BY trade_number
    """
    with closing(sqlserver_connection(settings)) as conn:
        cur = conn.cursor(); cur.execute(query, *params)
        columns = [x[0] for x in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    for row in rows:
        row["closed_at"] = row["closed_at"].isoformat() if row["closed_at"] else None
        row["opened_at"] = row["opened_at"].isoformat() if row["opened_at"] else None
        for key in ("net_return", "equity", "drawdown"):
            row[key] = float(row[key])
    return rows


def local_closed_trades(settings, strategy_id: str, date_from=None, date_to_exclusive=None, limit: int = 1000) -> list[dict[str, Any]]:
    """Return the closed-trade ledger ordered from earliest to latest entry."""
    filters, params = [], [limit, strategy_id, strategy_id + "_B", strategy_id + "_S"]
    if date_from is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) >= ?")
        params.append(date_from)
    if date_to_exclusive is not None:
        filters.append("AND COALESCE(g_close_time,last_update,created) < ?")
        params.append(date_to_exclusive)
    query = f"""
      SELECT TOP (?) guid,product,UPPER(signal) signal,created entry_time,
             CAST(entry_price AS float) entry_price,
             COALESCE(g_close_time,last_update,created) exit_time,
             CAST(latest_price AS float) exit_price,CAST(net_return AS float) net_return,
             CAST(alt_net_return AS float) alt_net_return
      FROM dbo.combined_trades_closed WITH (NOLOCK)
      WHERE model_ix IN (CONVERT(varchar(200),?),CONVERT(varchar(200),?),CONVERT(varchar(200),?))
        AND net_return IS NOT NULL {' '.join(filters)}
      ORDER BY created ASC,COALESCE(g_close_time,last_update,created) ASC,guid ASC
      OPTION (MAXDOP 1, RECOMPILE)
    """
    with closing(sqlserver_connection(settings)) as conn:
        cur = conn.cursor(); cur.execute(query, *params)
        columns = [item[0] for item in cur.description]
        rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    for row in rows:
        for key in ("entry_time", "exit_time"):
            row[key] = row[key].isoformat() if row[key] else None
        for key in ("entry_price", "exit_price", "net_return", "alt_net_return"):
            row[key] = float(row[key]) if row[key] is not None else None
    return rows


def local_equity_curves(settings,strategy_ids=None) -> dict[str,list[dict[str,Any]]]:
    """Load every canonical DNA return series in one query for bounded directory intelligence work."""
    strategy_ids=list(dict.fromkeys(strategy_ids or []));canonical="CASE WHEN RIGHT(model,2) IN ('_B','_S') THEN LEFT(model,LEN(model)-2) ELSE model END"
    strategy_filter="" if not strategy_ids else " AND "+canonical+" IN ("+",".join("?" for _ in strategy_ids)+")"
    # Tie-break on CAST(guid AS char(36)) everywhere a trade's relative order
    # matters, not the raw uniqueidentifier column. SQL Server sorts
    # uniqueidentifier by internal byte groups, not the hyphenated string a
    # consumer sees or would naturally re-sort by - relying on the raw
    # column let trade_number silently disagree with any later re-derivation
    # of order from the same guid values (e.g. Snapshot.verified()'s
    # reconciliation check), corrupting reconciliation for same-timestamp
    # trades. Casting first makes every ORDER BY here match a plain string
    # sort, and the trade_number-assigning window and the running-equity
    # window now use the exact same tie-break so they can't disagree with
    # each other either.
    query=f"""
    WITH ranked_trades AS (
      SELECT {canonical} strategy_id,
        COALESCE(g_close_time,last_update,created) closed_at,created opened_at,created,CAST(guid AS char(36)) guid,CAST(net_return AS float) net_return,
        product,UPPER(LTRIM(RTRIM(signal))) signal,CAST(entry_price AS float) entry_price,CAST(latest_price AS float) exit_price,
        CAST(alt_net_return AS float) alt_net_return,
        ROW_NUMBER() OVER(PARTITION BY {canonical}
          ORDER BY COALESCE(g_close_time,last_update,created) DESC,created DESC,CAST(guid AS char(36)) DESC) reverse_number
      FROM dbo.combined_trades_closed WHERE model_ix LIKE 'DNA[_]%' AND net_return IS NOT NULL {strategy_filter}
    ), trades AS (
      SELECT strategy_id,closed_at,opened_at,created,guid,net_return,product,signal,entry_price,exit_price,alt_net_return FROM ranked_trades WHERE reverse_number<={MAX_PROFILE_POINTS}
    ), equity AS (
      SELECT strategy_id,closed_at,opened_at,guid,net_return,product,signal,entry_price,exit_price,alt_net_return,
        SUM(net_return) OVER(PARTITION BY strategy_id ORDER BY closed_at,guid ROWS UNBOUNDED PRECEDING) equity
      FROM trades
    ), curve AS (
      SELECT strategy_id,closed_at,opened_at,guid,net_return,product,signal,entry_price,exit_price,alt_net_return,equity,
        equity-CASE WHEN MAX(equity) OVER(PARTITION BY strategy_id ORDER BY closed_at,guid ROWS UNBOUNDED PRECEDING)>0 THEN MAX(equity) OVER(PARTITION BY strategy_id ORDER BY closed_at,guid ROWS UNBOUNDED PRECEDING) ELSE 0 END drawdown,
        ROW_NUMBER() OVER(PARTITION BY strategy_id ORDER BY closed_at,guid) trade_number
      FROM equity
    ) SELECT strategy_id,trade_number,opened_at,closed_at,guid,net_return,equity,drawdown,product,signal,entry_price,exit_price,alt_net_return FROM curve ORDER BY strategy_id,trade_number
    """
    with closing(sqlserver_connection(settings)) as conn:
        cur=conn.cursor();cur.execute(query,*strategy_ids);columns=[item[0] for item in cur.description]
        rows=[dict(zip(columns,row)) for row in cur.fetchall()]
    grouped={}
    for row in rows:
        strategy_id=row.pop("strategy_id");row["closed_at"]=row["closed_at"].isoformat() if row["closed_at"] else None;row["opened_at"]=row["opened_at"].isoformat() if row["opened_at"] else None
        row["guid"]=str(row["guid"]).strip() if row.get("guid") else None
        for key in ("net_return","equity","drawdown"):row[key]=float(row[key])
        for key in ("entry_price","exit_price","alt_net_return"):row[key]=float(row[key]) if row.get(key) is not None else None
        grouped.setdefault(strategy_id,[]).append(row)
    return grouped


class MemoryRepository:
    def __init__(self): self.snapshots = {}; self.current_id = None; self._staged = {}
    def begin_snapshot(self, envelope):
        staged = self._staged.get(envelope.snapshot_id)
        if staged is not None:
            if staged["envelope"] != envelope: raise ValueError("snapshot ID already exists with different evidence")
            return
        if envelope.snapshot_id in self.snapshots: raise ValueError("snapshot ID already exists with different evidence")
        self._staged[envelope.snapshot_id] = {"envelope": envelope, "items": {}, "profiles": {}, "return_series": {}}
    def add_snapshot_batch(self, snapshot_id, items, profiles, return_series):
        staged = self._staged.get(snapshot_id)
        if staged is None: raise KeyError(snapshot_id)
        for item in items: staged["items"].setdefault(item.strategy_id, item)
        for profile in profiles: staged["profiles"].setdefault(profile.identity.strategy_id, profile)
        for point in return_series: staged["return_series"].setdefault((point.strategy_id, point.observed_at, point.trade_id), point)
    def finalize_snapshot(self, snapshot_id):
        staged = self._staged.get(snapshot_id)
        if staged is None: raise KeyError(snapshot_id)
        envelope = staged["envelope"]
        if len(staged["items"]) != envelope.item_count:
            raise ValueError(f"received {len(staged['items'])} of {envelope.item_count} declared items")
        snapshot = Snapshot(snapshot_id=snapshot_id, schema_version=envelope.schema_version, methodology_version=envelope.methodology_version,
            source_watermark=envelope.source_watermark, generated_at=envelope.generated_at, item_count=envelope.item_count, sha256=envelope.sha256,
            items=list(staged["items"].values()), intelligence_profiles=list(staged["profiles"].values()), return_series=list(staged["return_series"].values()))
        self.promote(snapshot)
        del self._staged[snapshot_id]
    def promote(self, snapshot: Snapshot):
        snapshot.verified()
        existing=self.snapshots.get(snapshot.snapshot_id)
        if existing is not None:
            envelope=(existing.sha256,existing.schema_version,existing.methodology_version,existing.source_watermark,existing.generated_at,existing.item_count)
            incoming=(snapshot.sha256,snapshot.schema_version,snapshot.methodology_version,snapshot.source_watermark,snapshot.generated_at,snapshot.item_count)
            if envelope!=incoming:raise ValueError("snapshot ID already exists with different evidence")
        else:self.snapshots[snapshot.snapshot_id]=snapshot
        self.current_id = snapshot.snapshot_id
    def current_items(self):
        return [] if self.current_id is None else self.snapshots[self.current_id].items
    def current_snapshot(self):
        return None if self.current_id is None else self.snapshots[self.current_id]
    def current_profiles(self):
        snap=self.current_snapshot();return [] if snap is None else [item.model_dump(mode="json") for item in snap.intelligence_profiles]
    def current_equity_curve(self,strategy_id,date_from=None,date_to_exclusive=None):
        snap=self.current_snapshot();rows=[] if snap is None else [item for item in snap.return_series if item.strategy_id==strategy_id and (date_from is None or item.observed_at>=date_from) and (date_to_exclusive is None or item.observed_at<date_to_exclusive)]
        return rebase_equity_rows([{"trade_number":item.trade_number,"opened_at":item.opened_at.isoformat() if item.opened_at else None,"closed_at":item.observed_at.isoformat(),"net_return":item.net_return,"alt_net_return":item.alt_net_return,"signal":item.signal,"equity":item.cumulative_net_return,"drawdown":item.drawdown} for item in rows])
    def current_equity_curves(self):
        return {item.strategy_id:self.current_equity_curve(item.strategy_id) for item in self.current_items()}
    def current_closed_trades(self,strategy_id,date_from=None,date_to_exclusive=None,limit=1000):
        snap=self.current_snapshot()
        if snap is None:return []
        rows=[p for p in snap.return_series if p.strategy_id==strategy_id and (date_from is None or p.observed_at>=date_from) and (date_to_exclusive is None or p.observed_at<date_to_exclusive)]
        rows.sort(key=lambda p:(p.observed_at,p.trade_id))
        return [{"guid":p.trade_id,"product":p.product,"signal":p.signal,
                 "entry_time":p.opened_at.isoformat() if p.opened_at else None,"entry_price":p.entry_price,
                 "exit_time":p.observed_at.isoformat(),"exit_price":p.exit_price,
                 "net_return":p.net_return,"alt_net_return":p.alt_net_return} for p in rows[:limit]]
    def current_rank_journey(self,strategy_id,date_from=None,date_to_exclusive=None):
        """Reads the rank_position/total_strategies stamped on each return-
        series point at export time (sync/export_snapshot.py) - an
        all-time ranking over the exported population, not local's live
        current-day-scoped /rank-journey computation. Points from
        snapshots published before these fields existed have
        rank_position=None and are skipped, same convention local's own
        basis-column-guarded snapshot lookups already use."""
        snap=self.current_snapshot()
        if snap is None:return []
        rows=[p for p in snap.return_series if p.strategy_id==strategy_id and p.rank_position is not None and (date_from is None or p.observed_at>=date_from) and (date_to_exclusive is None or p.observed_at<date_to_exclusive)]
        rows.sort(key=lambda p:(p.observed_at,p.trade_id))
        return [{"trade_number":p.trade_number,"closed_at":p.observed_at.isoformat(),
                 "cumulative_net_return":p.cumulative_net_return,
                 "rank_position":p.rank_position,"total_strategies":p.total_strategies} for p in rows]
    def period_items(self,date_from=None,date_to_exclusive=None,canonical_strategy=None):
        snap=self.current_snapshot()
        if snap is None:return []
        identity={item.strategy_id:item for item in snap.items}
        grouped={}
        for point in snap.return_series:
            if canonical_strategy is not None and point.strategy_id!=canonical_strategy:continue
            if date_from is not None and point.observed_at<date_from:continue
            if date_to_exclusive is not None and point.observed_at>=date_to_exclusive:continue
            grouped.setdefault(point.strategy_id,[]).append(point)
        results=[]
        for strategy_id,points in grouped.items():
            wins=losses=breakevens=0;gross_profit=gross_loss=0.0;equity=0.0
            for point in points:
                net=point.net_return;equity+=net
                if net>0:wins+=1;gross_profit+=net
                elif net<0:losses+=1;gross_loss+=abs(net)
                else:breakevens+=1
            base=identity.get(strategy_id);total=len(points)
            results.append({
                "strategy_id":strategy_id,"descriptive_name":base.descriptive_name if base else None,
                "product_name":base.product_name if base else None,"market":base.market if base else "FX",
                "status":base.status if base else "active","total_trades":total,
                "wins":wins,"losses":losses,"breakevens":breakevens,
                "total_net_return":equity,"win_rate":wins/total if total else 0.0,
                "profit_factor":(gross_profit/gross_loss) if gross_loss else None,
                "max_drawdown_money":None,
                "evidence_start":min(point.opened_at or point.observed_at for point in points),
                "evidence_end":max(point.observed_at for point in points),
                "quality_state":"VALID" if total>=30 else "COLLECTING",
            })
        return results
    def current_daily_returns(self,strategy_ids,max_days=2000):
        output={strategy_id:{} for strategy_id in strategy_ids};snap=self.current_snapshot()
        for point in ([] if snap is None else snap.return_series):
            if point.strategy_id in output:
                day=point.observed_at.date().isoformat();output[point.strategy_id][day]=output[point.strategy_id].get(day,0)+point.net_return
        return {strategy_id:[{"timestamp":day,"return":value} for day,value in sorted(days.items())[-max_days:]] for strategy_id,days in output.items()}
    def rollback(self, snapshot_id: str):
        if snapshot_id not in self.snapshots: raise KeyError(snapshot_id)
        self.current_id = snapshot_id


class PostgresRepository:
    def __init__(self, database_url: str): self.database_url = database_url
    def _connect(self):
        import psycopg
        return psycopg.connect(self.database_url)
    def promote(self, snapshot: Snapshot):
        snapshot.verified()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT source_watermark FROM directory_snapshot WHERE status='current' FOR UPDATE")
            current = cur.fetchone()
            if current and current[0].astimezone(snapshot.source_watermark.tzinfo) > snapshot.source_watermark: raise ValueError("stale source watermark")
            cur.execute("SELECT schema_version,methodology_version,source_watermark,generated_at,item_count,sha256 FROM directory_snapshot WHERE snapshot_id=%s FOR UPDATE",(snapshot.snapshot_id,));existing=cur.fetchone()
            incoming=(snapshot.schema_version,snapshot.methodology_version,snapshot.source_watermark,snapshot.generated_at,snapshot.item_count,snapshot.sha256)
            if existing and tuple(existing)!=incoming:raise ValueError("snapshot ID already exists with different evidence")
            if not existing:
                cur.execute("""INSERT INTO directory_snapshot(snapshot_id,schema_version,methodology_version,source_watermark,generated_at,item_count,sha256,status)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,'staged')""",(snapshot.snapshot_id,*incoming))
                for s in snapshot.items:cur.execute("INSERT INTO directory_strategy(snapshot_id,strategy_id,payload) VALUES(%s,%s,%s)",(snapshot.snapshot_id,s.strategy_id,s.model_dump_json()))
                for profile in snapshot.intelligence_profiles:cur.execute("INSERT INTO directory_intelligence_profile(snapshot_id,strategy_id,payload) VALUES(%s,%s,%s)",(snapshot.snapshot_id,profile.identity.strategy_id,profile.model_dump_json()))
                for point in snapshot.return_series:cur.execute("INSERT INTO directory_return_series(snapshot_id,strategy_id,observed_at,trade_id,payload) VALUES(%s,%s,%s,%s,%s)",(snapshot.snapshot_id,point.strategy_id,point.observed_at,point.trade_id,point.model_dump_json()))
            cur.execute("UPDATE directory_snapshot SET status='retained' WHERE status='current'")
            cur.execute("UPDATE directory_snapshot SET status='current',promoted_at=now() WHERE snapshot_id=%s", (snapshot.snapshot_id,))
            cur.execute("INSERT INTO directory_current(singleton,snapshot_id) VALUES(TRUE,%s) ON CONFLICT(singleton) DO UPDATE SET snapshot_id=excluded.snapshot_id", (snapshot.snapshot_id,))
    def begin_snapshot(self, envelope):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT schema_version,methodology_version,source_watermark,generated_at,item_count,sha256 FROM directory_snapshot WHERE snapshot_id=%s FOR UPDATE",(envelope.snapshot_id,))
            existing=cur.fetchone()
            incoming=(envelope.schema_version,envelope.methodology_version,envelope.source_watermark,envelope.generated_at,envelope.item_count,envelope.sha256)
            if existing:
                if tuple(existing)!=incoming: raise ValueError("snapshot ID already exists with different evidence")
                return
            cur.execute("""INSERT INTO directory_snapshot(snapshot_id,schema_version,methodology_version,source_watermark,generated_at,item_count,sha256,status)
              VALUES(%s,%s,%s,%s,%s,%s,%s,'staged')""",(envelope.snapshot_id,*incoming))
    def add_snapshot_batch(self, snapshot_id, items, profiles, return_series):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT status FROM directory_snapshot WHERE snapshot_id=%s FOR UPDATE",(snapshot_id,))
            row=cur.fetchone()
            if row is None: raise KeyError(snapshot_id)
            if row[0]!='staged': raise ValueError(f"snapshot cannot accept batches from status={row[0]}")
            for s in items:
                cur.execute("INSERT INTO directory_strategy(snapshot_id,strategy_id,payload) VALUES(%s,%s,%s) ON CONFLICT (snapshot_id,strategy_id) DO NOTHING",(snapshot_id,s.strategy_id,s.model_dump_json()))
            for profile in profiles:
                cur.execute("INSERT INTO directory_intelligence_profile(snapshot_id,strategy_id,payload) VALUES(%s,%s,%s) ON CONFLICT (snapshot_id,strategy_id) DO NOTHING",(snapshot_id,profile.identity.strategy_id,profile.model_dump_json()))
            for point in return_series:
                cur.execute("INSERT INTO directory_return_series(snapshot_id,strategy_id,observed_at,trade_id,payload) VALUES(%s,%s,%s,%s,%s) ON CONFLICT (snapshot_id,strategy_id,observed_at,trade_id) DO NOTHING",(snapshot_id,point.strategy_id,point.observed_at,point.trade_id,point.model_dump_json()))
    def finalize_snapshot(self, snapshot_id):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT schema_version,methodology_version,source_watermark,generated_at,item_count,sha256,status FROM directory_snapshot WHERE snapshot_id=%s FOR UPDATE",(snapshot_id,))
            row=cur.fetchone()
            if row is None: raise KeyError(snapshot_id)
            schema_version,methodology_version,source_watermark,generated_at,item_count,sha256,status=row
            if status=='current': return
            if status!='staged': raise ValueError(f"snapshot cannot be finalized from status={status}")
            cur.execute("SELECT payload FROM directory_strategy WHERE snapshot_id=%s ORDER BY strategy_id",(snapshot_id,))
            items=[r[0] for r in cur.fetchall()]
            if len(items)!=item_count: raise ValueError(f"received {len(items)} of {item_count} declared items")
            cur.execute("SELECT payload FROM directory_intelligence_profile WHERE snapshot_id=%s ORDER BY strategy_id",(snapshot_id,))
            profiles=[r[0] for r in cur.fetchall()]
            cur.execute("SELECT payload FROM directory_return_series WHERE snapshot_id=%s ORDER BY strategy_id,observed_at,trade_id",(snapshot_id,))
            return_series=[r[0] for r in cur.fetchall()]
            snapshot=Snapshot(snapshot_id=snapshot_id,schema_version=schema_version,methodology_version=methodology_version,
              source_watermark=source_watermark,generated_at=generated_at,item_count=item_count,sha256=sha256,
              items=items,intelligence_profiles=profiles,return_series=return_series)
            try:
                snapshot.verified()
            except ValueError:
                cur.execute("UPDATE directory_snapshot SET status='rejected' WHERE snapshot_id=%s",(snapshot_id,))
                raise
            cur.execute("SELECT source_watermark FROM directory_snapshot WHERE status='current' FOR UPDATE")
            current=cur.fetchone()
            if current and current[0].astimezone(snapshot.source_watermark.tzinfo)>snapshot.source_watermark:
                cur.execute("UPDATE directory_snapshot SET status='rejected' WHERE snapshot_id=%s",(snapshot_id,))
                raise ValueError("stale source watermark")
            cur.execute("UPDATE directory_snapshot SET status='retained' WHERE status='current'")
            cur.execute("UPDATE directory_snapshot SET status='current',promoted_at=now() WHERE snapshot_id=%s",(snapshot_id,))
            cur.execute("INSERT INTO directory_current(singleton,snapshot_id) VALUES(TRUE,%s) ON CONFLICT(singleton) DO UPDATE SET snapshot_id=excluded.snapshot_id",(snapshot_id,))
    def current_snapshot(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""SELECT s.snapshot_id,s.schema_version,s.methodology_version,s.source_watermark,s.generated_at,s.item_count,s.sha256,
              COALESCE(jsonb_agg(d.payload ORDER BY d.strategy_id) FILTER (WHERE d.strategy_id IS NOT NULL),'[]')
              FROM directory_current c JOIN directory_snapshot s ON s.snapshot_id=c.snapshot_id
              LEFT JOIN directory_strategy d ON d.snapshot_id=s.snapshot_id GROUP BY s.snapshot_id""")
            row = cur.fetchone()
        if not row: return None
        return Snapshot(snapshot_id=row[0],schema_version=row[1],methodology_version=row[2],source_watermark=row[3],generated_at=row[4],item_count=row[5],sha256=row[6],items=row[7])
    def current_items(self):
        snap = self.current_snapshot(); return [] if snap is None else snap.items
    def current_profiles(self):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("""SELECT p.payload FROM directory_current c JOIN directory_intelligence_profile p ON p.snapshot_id=c.snapshot_id ORDER BY p.strategy_id""");return [row[0] for row in cur.fetchall()]
    def current_equity_curve(self,strategy_id,date_from=None,date_to_exclusive=None):
        clauses=["p.strategy_id=%s"];params=[strategy_id]
        if date_from is not None:clauses.append("p.observed_at>=%s");params.append(date_from)
        if date_to_exclusive is not None:clauses.append("p.observed_at<%s");params.append(date_to_exclusive)
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT p.payload FROM directory_current c JOIN directory_return_series p ON p.snapshot_id=c.snapshot_id WHERE "+" AND ".join(clauses)+" ORDER BY p.observed_at,p.trade_id",params);rows=[row[0] for row in cur.fetchall()]
        return rebase_equity_rows([{"trade_number":row["trade_number"],"opened_at":row.get("opened_at"),"closed_at":row["observed_at"],"net_return":row["net_return"],"alt_net_return":row.get("alt_net_return"),"signal":row.get("signal"),"equity":row["cumulative_net_return"],"drawdown":row["drawdown"]} for row in rows])
    def current_equity_curves(self):
        grouped={}
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT p.strategy_id,p.payload FROM directory_current c JOIN directory_return_series p ON p.snapshot_id=c.snapshot_id ORDER BY p.strategy_id,p.observed_at,p.trade_id")
            for strategy_id,payload in cur.fetchall():grouped.setdefault(strategy_id,[]).append({"trade_number":payload["trade_number"],"opened_at":payload.get("opened_at"),"closed_at":payload["observed_at"],"net_return":payload["net_return"],"alt_net_return":payload.get("alt_net_return"),"signal":payload.get("signal"),"equity":payload["cumulative_net_return"],"drawdown":payload["drawdown"]})
        return grouped
    def period_items(self,date_from=None,date_to_exclusive=None,canonical_strategy=None):
        """Per-strategy summaries recomputed from directory_return_series
        closed within [date_from, date_to_exclusive), close-time filtered -
        the same convention current_equity_curve() already uses for the
        hosted backend. Lets period-scoped directory queries (Current
        day/week/month, and any custom range) work on Postgres instead of
        unconditionally 501ing, which they did until this was added."""
        clauses=["1=1"];params=[]
        if date_from is not None:clauses.append("p.observed_at>=%s");params.append(date_from)
        if date_to_exclusive is not None:clauses.append("p.observed_at<%s");params.append(date_to_exclusive)
        if canonical_strategy is not None:clauses.append("p.strategy_id=%s");params.append(canonical_strategy)
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT p.strategy_id,p.payload FROM directory_current c JOIN directory_return_series p ON p.snapshot_id=c.snapshot_id WHERE "+" AND ".join(clauses)+" ORDER BY p.strategy_id",params)
            grouped={}
            for strategy_id,payload in cur.fetchall():grouped.setdefault(strategy_id,[]).append(payload)
            if not grouped:return []
            cur.execute("SELECT d.strategy_id,d.payload FROM directory_current c JOIN directory_strategy d ON d.snapshot_id=c.snapshot_id WHERE d.strategy_id = ANY(%s)",(list(grouped),))
            identity={strategy_id:payload for strategy_id,payload in cur.fetchall()}
        results=[]
        for strategy_id,points in grouped.items():
            wins=losses=breakevens=0;gross_profit=gross_loss=0.0;equity=0.0
            for point in points:
                net=point["net_return"];equity+=net
                if net>0:wins+=1;gross_profit+=net
                elif net<0:losses+=1;gross_loss+=abs(net)
                else:breakevens+=1
            base=identity.get(strategy_id,{});total=len(points)
            results.append({
                "strategy_id":strategy_id,"descriptive_name":base.get("descriptive_name"),
                "product_name":base.get("product_name"),"market":base.get("market","FX"),
                "status":base.get("status","active"),"total_trades":total,
                "wins":wins,"losses":losses,"breakevens":breakevens,
                "total_net_return":equity,"win_rate":wins/total if total else 0.0,
                "profit_factor":(gross_profit/gross_loss) if gross_loss else None,
                "max_drawdown_money":None,
                "evidence_start":min(point.get("opened_at") or point["observed_at"] for point in points),
                "evidence_end":max(point["observed_at"] for point in points),
                "quality_state":"VALID" if total>=30 else "COLLECTING",
            })
        return results
    def current_closed_trades(self,strategy_id,date_from=None,date_to_exclusive=None,limit=1000):
        clauses=["p.strategy_id=%s"];params=[strategy_id]
        if date_from is not None:clauses.append("p.observed_at>=%s");params.append(date_from)
        if date_to_exclusive is not None:clauses.append("p.observed_at<%s");params.append(date_to_exclusive)
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT p.payload FROM directory_current c JOIN directory_return_series p ON p.snapshot_id=c.snapshot_id WHERE "+" AND ".join(clauses)+" ORDER BY p.observed_at,p.trade_id LIMIT %s",params+[limit])
            rows=[row[0] for row in cur.fetchall()]
        return [{"guid":row["trade_id"],"product":row.get("product"),"signal":row.get("signal"),
                 "entry_time":row.get("opened_at"),"entry_price":row.get("entry_price"),
                 "exit_time":row["observed_at"],"exit_price":row.get("exit_price"),
                 "net_return":row["net_return"],"alt_net_return":row.get("alt_net_return")} for row in rows]
    def current_rank_journey(self,strategy_id,date_from=None,date_to_exclusive=None):
        """See MemoryRepository.current_rank_journey() - same all-time,
        export-time-precomputed semantics, read from the stored jsonb
        payload instead of an in-memory Pydantic object."""
        clauses=["p.strategy_id=%s","(p.payload->>'rank_position') IS NOT NULL"];params=[strategy_id]
        if date_from is not None:clauses.append("p.observed_at>=%s");params.append(date_from)
        if date_to_exclusive is not None:clauses.append("p.observed_at<%s");params.append(date_to_exclusive)
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("SELECT p.payload FROM directory_current c JOIN directory_return_series p ON p.snapshot_id=c.snapshot_id WHERE "+" AND ".join(clauses)+" ORDER BY p.observed_at,p.trade_id",params)
            rows=[row[0] for row in cur.fetchall()]
        return [{"trade_number":row["trade_number"],"closed_at":row["observed_at"],
                 "cumulative_net_return":row["cumulative_net_return"],
                 "rank_position":row.get("rank_position"),"total_strategies":row.get("total_strategies")} for row in rows]
    def current_daily_returns(self,strategy_ids,max_days=2000):
        with self._connect() as conn,conn.cursor() as cur:
            cur.execute("""WITH daily AS (
              SELECT p.strategy_id,date_trunc('day',p.observed_at) observed_day,SUM((p.payload->>'net_return')::numeric) net_return
              FROM directory_current c JOIN directory_return_series p ON p.snapshot_id=c.snapshot_id
              WHERE p.strategy_id=ANY(%s) GROUP BY p.strategy_id,date_trunc('day',p.observed_at)
            ), ranked AS (SELECT *,row_number() OVER(PARTITION BY strategy_id ORDER BY observed_day DESC) ordinal FROM daily)
            SELECT strategy_id,observed_day,net_return FROM ranked WHERE ordinal<=%s ORDER BY strategy_id,observed_day""",(strategy_ids,max_days));rows=cur.fetchall()
        output={strategy_id:[] for strategy_id in strategy_ids}
        for strategy_id,day,value in rows:output[strategy_id].append({"timestamp":day.date().isoformat(),"return":float(value)})
        return output
    def rollback(self, snapshot_id: str):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("SELECT 1 FROM directory_snapshot WHERE snapshot_id=%s", (snapshot_id,))
            if not cur.fetchone(): raise KeyError(snapshot_id)
            cur.execute("UPDATE directory_snapshot SET status='retained' WHERE status='current'")
            cur.execute("UPDATE directory_snapshot SET status='current',promoted_at=now() WHERE snapshot_id=%s", (snapshot_id,))
            cur.execute("UPDATE directory_current SET snapshot_id=%s WHERE singleton=TRUE", (snapshot_id,))
