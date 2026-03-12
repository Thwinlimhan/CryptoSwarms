# Agentic Research Factory (All-In Integration)

This module turns the app into a background R&D factory inspired by top agentic and quant stacks.

## What is implemented

- `agents/research/research_factory.py`
  - Ingests live research connector outputs.
  - Cross-references local knowledge docs (books/papers).
  - Emits traceable hypotheses and queued backtest requests.

- `agents/research/skill_factory.py`
  - Generates reusable artifacts for other agents from books, papers, and articles.
  - Supports `skill`, `playbook`, and `tool_spec` artifact types.
  - Enforces promotion gates: provenance, tests, reviewer score, and quality score.

- `agents/research/stack_profiles.py`
  - Built-in integration map for:
    - autoresearch
    - RD-Agent
    - OpenBB Workspace
    - Freqtrade
    - QuantConnect Lean
    - Qlib
    - Jesse
    - vectorbt

- `agents/backtest/institutional_gate.py`
  - Institutional benchmark gate for strategy acceptance:
    - excess Sharpe vs baseline
    - max drawdown limits
    - profit factor threshold
    - minimum trade count

- `cryptoswarms/crypto_strategy_pack.py`
  - Crypto-fit signal modules:
    - pairs / spread mean reversion
    - volatility compression breakout
    - cross-sectional momentum rotation

## Run background factory

```powershell
.\.venv\Scripts\python.exe scripts\run_research_factory.py
```

or via Makefile:

```powershell
make research-factory
```

## Run skill factory

```powershell
.\.venv\Scripts\python.exe scripts\run_skill_factory.py
```

## Run crypto strategy pack demo

```powershell
.\.venv\Scripts\python.exe scripts\run_crypto_strategy_pack.py
```

or via Makefile:

```powershell
make crypto-alpha-pack
```

## How to operate

1. Keep one active strategy as default.
2. Let research factory run in the background and emit hypotheses.
3. Let skill factory convert validated knowledge into reusable agent artifacts.
4. Route emitted backtest requests through strict D10 + institutional benchmark gates.
5. Promote only when promotion scorecard, artifact verification, and attribution gates all pass.
