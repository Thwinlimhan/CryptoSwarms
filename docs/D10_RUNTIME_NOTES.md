# D10 Backtest Runtime Notes

## Status
- CI enforces backtest runtime integration tests in a dedicated `backtest-runtimes` job (`Python 3.11`, `REQUIRE_BACKTEST_RUNTIMES=true`).
- CI now runs a strict runtime availability check before tests: `scripts/check_backtest_runtimes.py`.
- Local host Python may skip runtime-heavy backtest tests if optional dependencies are unavailable.

## Local strict execution workaround
Run strict backtest runtime tests in Docker (Python 3.11):

```powershell
pwsh -File scripts/run_backtest_runtime_in_docker.ps1
```

This runs:
1. `pip install -e .[backtest] pytest`
2. `REQUIRE_BACKTEST_RUNTIMES=true`
3. runtime availability check (`scripts/check_backtest_runtimes.py`)
4. integration tests for `vectorbt` and `jesse`

## Enforcement policy
- Treat CI `backtest-runtimes` as authoritative.
- Use Docker runner locally when host runtime is incompatible.
