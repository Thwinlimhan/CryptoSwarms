import os

import pytest

from agents.backtest.engine_adapters import JesseFoldRunner


def _ensure_jesse_available() -> None:
    try:
        import jesse  # noqa: F401
    except Exception as exc:
        if os.getenv("REQUIRE_BACKTEST_RUNTIMES", "").strip().lower() == "true":
            pytest.fail(f"jesse is required but unavailable: {exc}")
        pytest.skip("jesse runtime not installed")


def test_jesse_fold_runner_requires_runtime_or_skips():
    _ensure_jesse_available()

    runner = JesseFoldRunner(run_fold=lambda *_: [0.001, -0.0005, 0.0008])
    folds = runner("module", "Class", {"x": 1.0}, {"close": [1, 2, 3]}, 3)

    assert len(folds) == 3
    assert all(isinstance(series, list) for series in folds)
