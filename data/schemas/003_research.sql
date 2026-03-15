-- Swarm Autoresearcher Logs and Reports
CREATE TABLE IF NOT EXISTS research_experiments (
    id UUID DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    theme TEXT NOT NULL,
    variable TEXT NOT NULL,
    baseline_value TEXT,
    variant_value TEXT,
    score DOUBLE PRECISION,
    delta_vs_baseline DOUBLE PRECISION,
    metrics JSONB, -- quality, latency, token_efficiency, etc.
    status TEXT NOT NULL DEFAULT 'completed', -- completed, failed
    log TEXT,
    PRIMARY KEY (id, time)
);
SELECT create_hypertable('research_experiments', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS research_reports (
    id UUID DEFAULT gen_random_uuid(),
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date TEXT NOT NULL,
    theme TEXT NOT NULL,
    data_source TEXT,
    summary TEXT,
    recommendation TEXT,
    regressions TEXT,
    safety_note TEXT,
    full_data JSONB, -- snapshots of baseline/variants
    applied BOOLEAN DEFAULT FALSE,
    applied_at TIMESTAMPTZ,
    PRIMARY KEY (id, time)
);
SELECT create_hypertable('research_reports', 'time', if_not_exists => TRUE);
