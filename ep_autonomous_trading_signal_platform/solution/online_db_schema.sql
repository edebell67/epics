BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS strategies (
    strategy_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_name VARCHAR(150) NOT NULL,
    asset VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_strategies_name_asset_timeframe UNIQUE (strategy_name, asset, timeframe)
);

CREATE TABLE IF NOT EXISTS signals (
    signal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id) ON DELETE RESTRICT,
    signal_timestamp TIMESTAMPTZ NOT NULL,
    asset VARCHAR(50) NOT NULL,
    direction VARCHAR(10) NOT NULL,
    entry NUMERIC(18,8) NOT NULL,
    tp NUMERIC(18,8),
    sl NUMERIC(18,8),
    confidence NUMERIC(5,2),
    source_system VARCHAR(100),
    published_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_signals_direction CHECK (direction IN ('buy', 'sell')),
    CONSTRAINT chk_signals_confidence CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 100))
);

CREATE TABLE IF NOT EXISTS trade_results (
    trade_result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES signals(signal_id) ON DELETE CASCADE,
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id) ON DELETE RESTRICT,
    trade_open_time TIMESTAMPTZ NOT NULL,
    trade_close_time TIMESTAMPTZ,
    entry_price NUMERIC(18,8) NOT NULL,
    exit_price NUMERIC(18,8),
    profit_loss NUMERIC(18,8) NOT NULL DEFAULT 0,
    profit_loss_pct NUMERIC(9,4),
    status VARCHAR(20) NOT NULL DEFAULT 'open',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_trade_results_status CHECK (status IN ('open', 'closed', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS strategy_performance (
    strategy_performance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID NOT NULL REFERENCES strategies(strategy_id) ON DELETE CASCADE,
    performance_date DATE NOT NULL,
    asset VARCHAR(50) NOT NULL,
    timeframe VARCHAR(20) NOT NULL,
    win_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    profit_factor NUMERIC(10,4) NOT NULL DEFAULT 0,
    drawdown NUMERIC(10,4) NOT NULL DEFAULT 0,
    trade_count INTEGER NOT NULL DEFAULT 0,
    total_profit_loss NUMERIC(18,8) NOT NULL DEFAULT 0,
    avg_profit_loss NUMERIC(18,8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_strategy_performance UNIQUE (strategy_id, performance_date),
    CONSTRAINT chk_strategy_performance_win_rate CHECK (win_rate >= 0 AND win_rate <= 100),
    CONSTRAINT chk_strategy_performance_trade_count CHECK (trade_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_signals_strategy_timestamp
    ON signals (strategy_id, signal_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_signals_asset_timestamp
    ON signals (asset, signal_timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_trade_results_signal
    ON trade_results (signal_id);

CREATE INDEX IF NOT EXISTS idx_trade_results_strategy_status
    ON trade_results (strategy_id, status);

CREATE INDEX IF NOT EXISTS idx_strategy_performance_strategy_date
    ON strategy_performance (strategy_id, performance_date DESC);

COMMIT;
