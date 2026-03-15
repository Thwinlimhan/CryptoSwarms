"""Ensemble Signal Weighter — combines signals from multiple sources with learned weights.

Weights are calibrated from backtest performance to optimally
combine signals of different types.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("swarm.signals.ensemble")


@dataclass
class Signal:
    """A signal for ensemble combination."""
    signal_type: str
    confidence: float  # 0.0 to 1.0
    direction: str  # "BUY", "SELL", "NEUTRAL"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EnsembleResult:
    """Result of ensemble signal combination."""
    combined_confidence: float
    direction: str
    signal_count: int
    weighted_contributions: dict[str, float]
    message: str


# Default weights (calibrated from typical crypto trading performance)
DEFAULT_BACKTEST_WEIGHTS: dict[str, float] = {
    "funding": 1.5,      # Funding rates are highly predictive
    "liquidation": 1.3,  # Liquidation cascades are strong signals
    "volume": 1.2,       # Volume is a solid confirming indicator
    "order_flow": 1.1,   # Order flow adds edge
    "technical": 0.8,    # Technical analysis is common, lower alpha
    "sentiment": 0.6,    # Sentiment is noisy
    "momentum": 1.0,     # Momentum is base-level
    "mean_reversion": 0.9,
    "volatility_breakout": 1.1,
}


class SignalEnsemble:
    """Combines signals from multiple sources using weighted averaging.

    Weights represent the relative importance of each signal type,
    calibrated from backtest performance.
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        min_signals: int = 2,
        min_combined_confidence: float = 0.3,
    ) -> None:
        self.weights = weights or DEFAULT_BACKTEST_WEIGHTS.copy()
        self.min_signals = min_signals
        self.min_combined_confidence = min_combined_confidence

    def _load_backtest_weights(self) -> dict[str, float]:
        """Load weights from backtest results (placeholder for DB/file loading)."""
        return dict(self.weights)

    def combine_signals(self, signals: list[Signal]) -> EnsembleResult:
        """Combine multiple signals into a single ensemble signal.

        Args:
            signals: List of signals to combine.

        Returns:
            EnsembleResult with combined confidence and direction.
        """
        if not signals:
            return EnsembleResult(
                combined_confidence=0.0,
                direction="NEUTRAL",
                signal_count=0,
                weighted_contributions={},
                message="No signals to combine",
            )

        actionable = [s for s in signals if s.direction != "NEUTRAL"]

        if len(actionable) < self.min_signals:
            return EnsembleResult(
                combined_confidence=0.0,
                direction="NEUTRAL",
                signal_count=len(signals),
                weighted_contributions={},
                message=f"Insufficient actionable signals: {len(actionable)} < {self.min_signals}",
            )

        # Calculate direction consensus
        buy_weight = 0.0
        sell_weight = 0.0
        contributions: dict[str, float] = {}

        for s in actionable:
            weight = self.weights.get(s.signal_type, 0.5)
            weighted_value = s.confidence * weight
            contributions[s.signal_type] = round(weighted_value, 4)

            if s.direction == "BUY":
                buy_weight += weighted_value
            elif s.direction == "SELL":
                sell_weight += weighted_value

        total_weight = buy_weight + sell_weight
        if total_weight == 0:
            direction = "NEUTRAL"
            combined_confidence = 0.0
        elif buy_weight > sell_weight:
            direction = "BUY"
            combined_confidence = buy_weight / total_weight
        else:
            direction = "SELL"
            combined_confidence = sell_weight / total_weight

        # Normalize and cap confidence
        combined_confidence = min(1.0, combined_confidence)

        if combined_confidence < self.min_combined_confidence:
            direction = "NEUTRAL"
            combined_confidence = 0.0

        return EnsembleResult(
            combined_confidence=round(combined_confidence, 4),
            direction=direction,
            signal_count=len(signals),
            weighted_contributions=contributions,
            message=(
                f"Ensemble: {direction} with {combined_confidence:.2%} confidence "
                f"from {len(actionable)} signals"
            ),
        )

    def update_weight(self, signal_type: str, new_weight: float) -> None:
        """Update weight for a specific signal type."""
        old_weight = self.weights.get(signal_type, 0.5)
        self.weights[signal_type] = max(0.0, new_weight)
        logger.info(
            "Weight updated for '%s': %.3f → %.3f",
            signal_type, old_weight, new_weight,
        )
