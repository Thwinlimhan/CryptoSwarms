# CryptoSwarms Agent Context
> Injected at startup for all Deep Agents operating on this codebase.

## Architecture Rules
- Strategy files live in `strategies/` — NEVER edit gate files or execution files
- All API calls go through skill_hub_clients.py adapters — never raw HTTP in strategies
- Validation pipeline has 9 gates (0-8) — a strategy must pass ALL to reach live trading
- The immutable artifacts system records every experiment — never delete from `/data/artifacts/`

## Current Market Context
- Primary instrument: BTC-PERP on Hyperliquid (1h and 15m timeframes)
- Current regime: update this manually or via MiroFish simulation output
- Active strategies: check `data/active_strategies.json`

## Code Style
- Python 3.11+, dataclasses with slots=True, no mutable defaults
- All new classes must have a corresponding test in tests/
- Gate functions must return GateResult with gate_number, gate_name, status, score, details

## Evolution Policy
- Read program.md before making any changes
- Minimum Sharpe improvement: 0.02 to keep an experiment
- Always run syntax-checker subagent before validation
- Log every experiment to /memories/evolution_log.md

## Enhancement Integration Status
- ✅ MiroFish: Swarm simulation via gate_7_swarm_regime (COMPLETE)
- ✅ Karpathy: Code evolution via DeepAgentEvolver (COMPLETE)
- ✅ Senpi AI: Smart-money scanner via SenpiHyperfeedConnector (COMPLETE)
- ✅ BkDplx: Microstructure recipes via gate_8_recipe_alignment (COMPLETE)
- ✅ Chub: API docs via fetch_api_docs tool (COMPLETE)
- ✅ Funding Arb: AR(12) predictor via gate_10_funding_arbitrage (COMPLETE)
- ✅ Hyperspace: P2P consensus via gate_9_hyperspace_consensus (COMPLETE)

**Integration Status**: 100% COMPLETE (7/7 enhancements implemented)
**Validation Pipeline**: 11 gates (0-10) fully operational
**Architecture**: All components wired and tested

## Microstructure Alignment Rule (added 2026-03-18)
- When editing strategy entry logic, check `candidate.market_data["microstructure"]["recipe"]`
- Prefer entries in: Trend Align, Absorption, Vacuum, Shock recipes
- Avoid entries in: Conflict, Drift, Exhaustion (highest failure rate in backtests)
- Never add indicator layers that conflict with OFI direction at entry
- Source: OFI primitives from Hyperliquid LOB — see agents/scanner/microstructure_primitives.py