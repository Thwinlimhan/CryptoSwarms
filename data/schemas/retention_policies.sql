-- TimescaleDB data retention policies
-- Run this once after the schema is set up to prevent disk exhaustion.

-- Keep raw risk check events for 30 days
-- (with the new state-change-only write pattern this is much less critical)
SELECT add_retention_policy('risk_events', INTERVAL '30 days', if_not_exists => TRUE);

-- Keep signals for 90 days
SELECT add_retention_policy('signals', INTERVAL '90 days', if_not_exists => TRUE);

-- Keep regime classifications for 90 days
SELECT add_retention_policy('regimes', INTERVAL '90 days', if_not_exists => TRUE);

-- Keep LLM cost rows for 365 days (needed for annual budget analysis)
SELECT add_retention_policy('llm_costs', INTERVAL '365 days', if_not_exists => TRUE);

-- Keep live trade records indefinitely (never auto-delete real trade history)
-- No retention policy on 'trades'
