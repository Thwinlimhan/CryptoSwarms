"""Signal Conflict Resolver — resolves conflicts between multiple signals on the same symbol.

When multiple agents produce conflicting signals, this module applies
a priority matrix to determine the winning signal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.signals.conflict")


@dataclass
class Signal:
    """Signal representation for conflict resolution."""
    symbol: str
    signal_type: str  # "funding", "volume", "technical", "sentiment", etc.
    direction: str  # "BUY", "SELL", "NEUTRAL"
    confidence: float  # 0.0 to 1.0
    source_agent: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ConflictResolutionResult:
    """Result of conflict resolution."""
    winning_signal: Signal | None
    all_signals: list[Signal]
    conflict_detected: bool
    resolution_method: str
    details: str


# Default priority: funding signals > volume signals > technical signals
DEFAULT_PRIORITY_MAP: dict[str, int] = {
    "funding": 5,
    "liquidation": 4,
    "volume": 3,
    "order_flow": 3,
    "technical": 2,
    "sentiment": 1,
    "mean_reversion": 1,
    "momentum": 2,
    "volatility_breakout": 3,
}


class SignalConflictResolver:
    """Resolves conflicts between multiple signals on the same symbol.

    Uses a priority matrix and confidence scoring to determine
    which signal should be acted upon when agents disagree.
    """

    def __init__(
        self,
        priority_map: dict[str, int] | None = None,
        confidence_weight: float = 0.3,
    ) -> None:
        self.priority_map = priority_map or DEFAULT_PRIORITY_MAP
        self.confidence_weight = confidence_weight  # How much confidence affects score

    def resolve_conflicts(self, signals: list[Signal]) -> ConflictResolutionResult:
        """Resolve conflicts among a list of signals.

        Args:
            signals: List of signals (usually for the same symbol).

        Returns:
            ConflictResolutionResult with the winning signal.
        """
        if not signals:
            return ConflictResolutionResult(
                winning_signal=None,
                all_signals=[],
                conflict_detected=False,
                resolution_method="none",
                details="No signals to resolve",
            )

        if len(signals) == 1:
            return ConflictResolutionResult(
                winning_signal=signals[0],
                all_signals=signals,
                conflict_detected=False,
                resolution_method="single",
                details="Only one signal, no conflict",
            )

        # Check if there's actually a conflict (different directions)
        directions = {s.direction for s in signals if s.direction != "NEUTRAL"}
        conflict_detected = len(directions) > 1

        if not conflict_detected:
            # All agree on direction — combine by highest priority * confidence
            winner = self._select_by_priority(signals)
            return ConflictResolutionResult(
                winning_signal=winner,
                all_signals=signals,
                conflict_detected=False,
                resolution_method="consensus",
                details=f"All signals agree on {winner.direction if winner else 'NEUTRAL'}",
            )

        # Conflict detected — use priority + confidence scoring
        winner = self._select_by_priority(signals)
        losing_directions = directions - {winner.direction if winner else ""}

        logger.warning(
            "Signal conflict on %s: %s wins over %s (priority=%d, conf=%.2f)",
            signals[0].symbol if signals else "?",
            winner.signal_type if winner else "none",
            losing_directions,
            self.priority_map.get(winner.signal_type if winner else "", 0),
            winner.confidence if winner else 0,
        )

        return ConflictResolutionResult(
            winning_signal=winner,
            all_signals=signals,
            conflict_detected=True,
            resolution_method="priority_confidence",
            details=(
                f"Conflict resolved: {winner.signal_type if winner else 'none'} "
                f"({winner.direction if winner else 'NEUTRAL'}) "
                f"wins with score {self._score(winner) if winner else 0:.2f}"
            ),
        )

    def _score(self, signal: Signal) -> float:
        """Calculate combined priority + confidence score."""
        priority = self.priority_map.get(signal.signal_type, 0)
        return priority + (signal.confidence * self.confidence_weight)

    def _select_by_priority(self, signals: list[Signal]) -> Signal | None:
        """Select the highest-scoring signal."""
        actionable = [s for s in signals if s.direction != "NEUTRAL"]
        if not actionable:
            return signals[0] if signals else None
        return max(actionable, key=self._score)

    def resolve_by_symbol(
        self, signals: list[Signal]
    ) -> dict[str, ConflictResolutionResult]:
        """Group signals by symbol and resolve conflicts for each."""
        grouped: dict[str, list[Signal]] = {}
        for s in signals:
            grouped.setdefault(s.symbol, []).append(s)

        return {
            symbol: self.resolve_conflicts(group)
            for symbol, group in grouped.items()
        }
