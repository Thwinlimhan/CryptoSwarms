from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class VectorbtBacktestRunner:
    """Run a simple MA crossover backtest with vectorbt and return strategy returns."""

    def __call__(self, strategy_module: str, class_name: str, params: dict[str, float], market_data: Any) -> list[float]:
        try:
            import pandas as pd
            import vectorbt as vbt
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("vectorbt runtime is not installed") from exc

        if not isinstance(market_data, dict) or "close" not in market_data:
            raise ValueError("market_data must provide close series")

        close = pd.Series(market_data["close"], dtype="float64")
        fast_window = int(params.get("fast_window", 10))
        slow_window = int(params.get("slow_window", 30))
        fees = float(params.get("fees", 0.0005))
        slippage = float(market_data.get("slippage_bps", 1)) / 10_000.0

        fast = vbt.MA.run(close, window=fast_window)
        slow = vbt.MA.run(close, window=slow_window)
        entries = fast.ma_crossed_above(slow)
        exits = fast.ma_crossed_below(slow)

        portfolio = vbt.Portfolio.from_signals(close, entries, exits, fees=fees, slippage=slippage)
        returns = portfolio.returns().dropna().tolist()
        return [float(v) for v in returns]


@dataclass(slots=True)
class JesseFoldRunner:
    """Jesse adapter that delegates fold execution to an injected callable."""

    run_fold: Any

    def __call__(self, strategy_module: str, class_name: str, params: dict[str, float], market_data: Any, folds: int) -> list[list[float]]:
        try:
            import jesse  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("jesse runtime is not installed") from exc

        return [
            list(self.run_fold(strategy_module, class_name, params, market_data, fold_index, folds))
            for fold_index in range(folds)
        ]
