# Decision Framework

This project now includes a decision framework that turns qualitative research into explicit math used by agents.

## Modules

- `cryptoswarms/base_rate_registry.py`
  - Stores success-rate priors by strategy family.
  - Supports empirical Bayes blending via pseudo-counts.

- `cryptoswarms/bayesian_update.py`
  - Bayesian update primitives and sentiment-to-likelihood mapping.
  - Supports sequential evidence updates.

- `cryptoswarms/decision_engine.py`
  - Expected value calculator with explicit cost deduction.
  - Binary-decision evaluator returning posterior probability and net EV.

- `cryptoswarms/fractional_kelly.py`
  - Kelly fraction and uncertainty-haircut fractional Kelly sizing.
  - Notional sizing from bankroll.

- `cryptoswarms/failure_ledger.py`
  - Tracks pass/fail outcomes by key.
  - Provides failure-rate driven deprioritization checks.

## Active integrations

- `agents/research/research_factory.py`
  - Uses base-rate prior + Bayesian updates for hypothesis confidence.
  - Applies failure-ledger survivorship penalty.
  - Emits `decision_math` in queue payload.
  - Adds `kelly_fraction` and `ev_after_costs_usd` to backtest params.

- `scripts/run_paper_ledger_job.py`
  - Adds `decision_math` (prior, posterior, EV net of costs).
  - Adds `sizing` block (fractional Kelly and suggested notional).

## Run

```powershell
.\.venv\Scripts\python.exe scripts\run_research_factory.py
.\.venv\Scripts\python.exe scripts\run_paper_ledger_job.py
```

The latest promotion report is written to `artifacts/phase1/paper_promotion_report.json`.
