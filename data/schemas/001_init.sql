CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- OHLCV
CREATE TABLE IF NOT EXISTS candles (
  time TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  exchange TEXT NOT NULL,
  open DOUBLE PRECISION,
  high DOUBLE PRECISION,
  low DOUBLE PRECISION,
  close DOUBLE PRECISION,
  volume DOUBLE PRECISION
);
SELECT create_hypertable('candles', 'time', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_candles_symbol_exchange_time ON candles (symbol, exchange, time DESC);

-- Signals
CREATE TABLE IF NOT EXISTS signals (
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  agent_name TEXT NOT NULL,
  signal_type TEXT NOT NULL,
  symbol TEXT,
  confidence DOUBLE PRECISION,
  acted_on BOOLEAN DEFAULT FALSE,
  metadata JSONB
);
SELECT create_hypertable('signals', 'time', if_not_exists => TRUE);

-- Trades (paper + live, slippage tracked)
CREATE TABLE IF NOT EXISTS trades (
  id UUID DEFAULT gen_random_uuid(),
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  exchange TEXT NOT NULL,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  size DOUBLE PRECISION,
  entry_price DOUBLE PRECISION,
  exit_price DOUBLE PRECISION,
  realised_pnl DOUBLE PRECISION,
  strategy_id TEXT,
  mode TEXT NOT NULL DEFAULT 'paper',
  slippage_bps DOUBLE PRECISION,
  fees_usd DOUBLE PRECISION,
  routing_reason TEXT,
  metadata JSONB
);
SELECT create_hypertable('trades', 'time', if_not_exists => TRUE);

-- Validation results (every gate logged)
CREATE TABLE IF NOT EXISTS validations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  strategy_id TEXT NOT NULL,
  gate TEXT NOT NULL,
  passed BOOLEAN,
  slippage_mode TEXT,
  sharpe DOUBLE PRECISION,
  max_drawdown DOUBLE PRECISION,
  wfe_ratio DOUBLE PRECISION,
  sensitivity DOUBLE PRECISION,
  full_report JSONB
);

-- LLM cost tracking
CREATE TABLE IF NOT EXISTS llm_costs (
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  agent TEXT NOT NULL,
  model TEXT NOT NULL,
  tokens_in INTEGER,
  tokens_out INTEGER,
  cost_usd DOUBLE PRECISION
);
SELECT create_hypertable('llm_costs', 'time', if_not_exists => TRUE);

-- Market regime history
CREATE TABLE IF NOT EXISTS regimes (
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  regime TEXT NOT NULL,
  confidence DOUBLE PRECISION,
  indicators JSONB
);
SELECT create_hypertable('regimes', 'time', if_not_exists => TRUE);

-- Risk events + circuit breakers
CREATE TABLE IF NOT EXISTS risk_events (
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  level INTEGER NOT NULL,
  trigger TEXT NOT NULL,
  portfolio_heat DOUBLE PRECISION,
  daily_dd DOUBLE PRECISION,
  action_taken TEXT,
  resolved_at TIMESTAMPTZ
);
SELECT create_hypertable('risk_events', 'time', if_not_exists => TRUE);
