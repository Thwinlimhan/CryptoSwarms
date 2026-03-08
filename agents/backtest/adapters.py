from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(slots=True)
class JesseAdapter:
    """Adapter for Jesse walk-forward execution.

    The injected callable allows integration with either jesse backtest internals
    or an HTTP service wrapper.
    """

    run_fold: Callable[[str, str, dict[str, float], Any, int, int], list[float]]

    def walk_forward(self, strategy_module: str, class_name: str, params: dict[str, float], market_data: Any, folds: int) -> list[list[float]]:
        return [
            self.run_fold(strategy_module, class_name, params, market_data, fold_index, folds)
            for fold_index in range(folds)
        ]


@dataclass(slots=True)
class TimescaleActiveReturnsProvider:
    connection: Any

    def __call__(self) -> dict[str, list[float]]:
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT strategy_id, array_agg(return ORDER BY ts) AS returns
            FROM strategy_returns
            WHERE active = TRUE
            GROUP BY strategy_id
            """
        )
        return {row[0]: list(row[1] or []) for row in cursor.fetchall()}


@dataclass(slots=True)
class DefaultRegimeTagger:
    """Segment data by supplied tags or fallback to a single 'all' regime."""

    def __call__(self, market_data: Any) -> dict[str, Any]:
        if isinstance(market_data, dict) and "regimes" in market_data:
            return {"regimes": market_data["regimes"]}
        return {"regimes": {"all": market_data}}
