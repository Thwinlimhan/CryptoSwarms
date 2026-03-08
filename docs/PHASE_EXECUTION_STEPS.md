# Phase Execution Steps

## Phase 0
1. `cp .env.example .env`
2. `make up`

## Phase 1
1. `make phase1-smoke`
2. `make phase1-loop`
3. Check artifacts in `artifacts/phase1/`

## Phase 2
1. Start API: `python -m api.main`
2. Check bridge endpoints:
   - `/api/routing/policy`
   - `/api/costs/budget?spent_usd=6.5`
   - `/api/agents/status`

## Phase 3
1. Run `MinimalResearchPipeline` from `agents/research/deerflow_pipeline.py`
2. Verify queued hypothesis payload includes provenance URL and timestamp

## Phase 4
1. Run parameter sweep via `agents/backtest/production.py`
2. Export report JSON and review decision reasons

## Phase 5
1. Validate wallet env isolation with `cryptoswarms/wallet_isolation.py`
2. Reconcile orders/fills with `cryptoswarms/reconciliation.py`

## Phase 6
1. Apply retention with `memory/quality.py`
2. Run memory quality checks and review stale/duplicate IDs

## Phase 7
1. Append/query audit events using `cryptoswarms/observability.py`
2. Evaluate alert flags for budget/pipeline/exchange failures

## Phase 8
1. Evaluate expansion prerequisites using `cryptoswarms/expansion_policy.py`
2. Proceed only when all prerequisite checks are green
