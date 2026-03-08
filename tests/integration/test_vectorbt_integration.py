import os

import pytest

from agents.backtest.engine_adapters import VectorbtBacktestRunner


def _ensure_vectorbt_available() -> None:
    try:
        import vectorbt  # noqa: F401
    except Exception as exc:
        if os.getenv("REQUIRE_BACKTEST_RUNTIMES", "").strip().lower() == "true":
            pytest.fail(f"vectorbt is required but unavailable: {exc}")
        pytest.skip("vectorbt runtime not installed")


def test_vectorbt_runner_executes_when_installed():
    _ensure_vectorbt_available()
    runner = VectorbtBacktestRunner()

    closes = [100 + i * 0.2 + ((-1) ** i) * 0.5 for i in range(200)]
    returns = runner(
        "unused",
        "unused",
        {"fast_window": 5, "slow_window": 20, "fees": 0.0005},
        {"close": closes, "slippage_bps": 2},
    )

    assert isinstance(returns, list)
    assert all(isinstance(v, float) for v in returns)
