# Crypto Swarm v6 - Implementation Checklist

## 0) Project Setup
- [x] Initialize repo structure (`docs/`, `infra/`, `services/`, `strategies/`, `scripts/`)
- [x] Create `.env.example` with required secrets and non-secret defaults
- [x] Add `docker-compose.yml` baseline for local services
- [x] Add `Makefile`/task runner for common commands (`up`, `down`, `test`, `lint`)
- [x] Add basic CI workflow (lint + unit tests)

## 1) Vertical Slice (MVS) - First Working Loop
- [x] Define one strategy hypothesis (single market + single timeframe)
- [x] Implement market data ingestion for that single source
- [x] Implement fast-screen backtest (VectorBT)
- [x] Implement deep validation backtest (Jesse)
- [x] Add 5-gate validation pipeline (at least Gate 1-3 to start)
- [x] Paper-trade execution path on one exchange/testnet
- [x] Persist run outputs (signals, fills, PnL, metadata)
- [x] Add a daily summary report for the single strategy

## 2) Core Infrastructure
- [x] TimescaleDB schema for OHLCV, signals, orders, fills, costs
- [x] Redis Streams channels for agent/event messaging
- [x] Mission Control deployment + connection to core services (placeholder service + API bridge endpoints)
- [x] Paperclip budget guardrails (`DAILY_LLM_BUDGET`, alert threshold) via budget guard module
- [x] Central config for model routing policy

## 3) Research Swarm (Minimal)
- [x] DeerFlow-based research pipeline skeleton
- [x] Add one news/source connector
- [x] Add one sentiment scoring module (local model first)
- [x] Store research outputs with timestamp + source provenance
- [x] Wire research output into strategy hypothesis queue

## 4) Backtest Swarm (Productionized)
- [x] Parameter sweep harness (bounded search space)
- [x] Walk-forward testing job scaffold
- [x] Slippage/fee stress scenarios
- [x] Automatic rejection reasons for failed candidates
- [x] Export comparable reports for accepted candidates

## 5) Execution Swarm (Safe by Default)
- [x] CONFIRM gate required on all order submission flows
- [x] Wallet/API key isolation per agent/service policy checks
- [x] Position sizing + max exposure controls
- [x] Kill-switch and circuit breaker conditions
- [x] Real-time order/fill reconciliation monitor

## 6) Memory Layer
- [x] Mem0 integration for working memory (`add`, `search`)
- [x] Qdrant collection setup and retention policy scaffold
- [x] Graphiti episode model for temporal knowledge scaffold
- [x] Minimal memory quality checks (duplication, stale facts)
- [x] Traceability: every memory item links to source/run id

## 7) Observability + Governance
- [x] LangSmith tracing integration scaffold
- [x] Cost dashboard tile(s): daily + rolling 7-day endpoint scaffold
- [x] Agent action audit log retained and queryable
- [x] Failure alerting (pipeline halt, exchange errors, budget breach)
- [x] Weekly review template for strategy/process decisions

## 8) Phase-Gated Expansion
- [x] Add second strategy only after first shows stable paper PnL (policy check)
- [x] Add second exchange only after execution reliability target met (policy check)
- [x] Add additional agents only when current bottleneck is proven (policy check)
- [x] Defer Evolution Swarm activation until sufficient live/paper history (policy check)

## 9) Definition of Done (MVS)
- [x] End-to-end run is reproducible from one command (`make phase1-loop`)
- [x] New strategy idea can be screened to result in < 1 day (scaffold)
- [x] All runs have artifacts (config, logs, metrics, decision outcome)
- [x] Budget and risk guards are enforced in code paths
- [x] Team can explain why any candidate was accepted/rejected (report + rejection reasons)

## Progress Snapshot
- **Current phase:** Phase 8 baseline scaffold complete
- **Current owner:** Codex + user
- **Last updated:** 2026-03-08
- **Blockers:** Cannot execute runtime validation in this shell (`python`/`pytest` unavailable)
