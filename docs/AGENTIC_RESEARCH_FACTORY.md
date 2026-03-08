# Agentic Research Factory (All-In Integration)

This module turns the app into a background R&D factory inspired by top agentic and quant stacks.

## What is implemented

- `agents/research/research_factory.py`
  - Ingests live research connector outputs.
  - Cross-references local knowledge docs (books/papers).
  - Emits traceable hypotheses and queued backtest requests.

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

## Run background factory

```powershell
.\.venv\Scripts\python.exe scripts\run_research_factory.py
```

or via Makefile:

```powershell
make research-factory
```

## How to operate

1. Keep one active strategy as default.
2. Let research factory run in the background and emit hypotheses.
3. Route emitted backtest requests through strict D10 + institutional benchmark gates.
4. Promote only when promotion scorecard and attribution gates both pass.
