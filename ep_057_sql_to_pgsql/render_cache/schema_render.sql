-- epics/ep_057_sql_to_pgsql/render_cache/schema_render.sql — Trimmed cache tables for the Render Postgres (idempotent).
-- v1.0.0 · 2026-09-23 · Same table names as local tradedb; only the columns top10_live_server.py reads.
CREATE TABLE IF NOT EXISTS tbl_dna_model_summary_snapshots_5min (
    snapshot_id bigint PRIMARY KEY, snapshot_timestamp timestamp NOT NULL, model text NOT NULL,
    product varchar, strategy_name varchar, strategy_family varchar,
    cum_net double precision, cum_alt_net double precision, cum_buy_net double precision,
    cum_buy_alt_net double precision, cum_sell_net double precision, cum_sell_alt_net double precision,
    open_trade_count integer, closed_trade_count integer, buy_closed_count integer, sell_closed_count integer);
CREATE INDEX IF NOT EXISTS ix_dna_summary_5min_ts ON tbl_dna_model_summary_snapshots_5min (snapshot_timestamp DESC);
CREATE INDEX IF NOT EXISTS ix_dna_summary_5min_model_ts ON tbl_dna_model_summary_snapshots_5min (model, snapshot_timestamp DESC);

CREATE TABLE IF NOT EXISTS combined_trades_closed (
    guid varchar PRIMARY KEY, model text, product varchar, product_type varchar, created timestamp, last_update timestamp,
    signal varchar, entry_price double precision, latest_price double precision, trade_quantity double precision,
    net_return double precision, alt_net_return double precision, min_net_return numeric, max_net_return numeric,
    close_type varchar, trade_reason varchar, strategy_name varchar, target_profit double precision, target_loss double precision);
CREATE INDEX IF NOT EXISTS ix_ctc_created_model ON combined_trades_closed (created, model);
CREATE INDEX IF NOT EXISTS ix_ctc_model_created ON combined_trades_closed (model, created);

CREATE TABLE IF NOT EXISTS combined_trades_open (
    guid varchar PRIMARY KEY, model varchar, product varchar, product_type varchar, created timestamp, last_update timestamp,
    signal varchar, entry_price double precision, latest_price double precision, trade_quantity double precision,
    net_return double precision, alt_net_return double precision, min_net_return numeric, max_net_return numeric,
    close_type varchar, trade_reason varchar, strategy_name varchar, target_profit double precision, target_loss double precision);
CREATE INDEX IF NOT EXISTS ix_cto_model_created ON combined_trades_open (model, created);

CREATE TABLE IF NOT EXISTS product_forex (
    model text, product varchar, product_type varchar, strategy_name varchar, strategy_params varchar, target_profit smallint);
CREATE INDEX IF NOT EXISTS ix_pf_model ON product_forex (model);

CREATE TABLE IF NOT EXISTS cache_import_ledger (
    name text PRIMARY KEY, sha256 text NOT NULL, rows integer, imported_at timestamptz NOT NULL DEFAULT now());
