-- Decision + Calibration Tracking (Failure Ledger)
CREATE TABLE IF NOT EXISTS decisions (
  id UUID DEFAULT gen_random_uuid(),
  time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  label TEXT NOT NULL,
  strategy_id TEXT,
  symbol TEXT,
  ev_estimate DOUBLE PRECISION,
  win_probability DOUBLE PRECISION,
  position_size_usd DOUBLE PRECISION,
  status TEXT NOT NULL DEFAULT 'pending', -- pending, won, lost, cancelled
  pnl_usd DOUBLE PRECISION,
  bias_flags JSONB, -- List of cognitive biases checked
  notes TEXT,
  resolved_at TIMESTAMPTZ,
  PRIMARY KEY (id, time)
);
SELECT create_hypertable('decisions', 'time', if_not_exists => TRUE);
