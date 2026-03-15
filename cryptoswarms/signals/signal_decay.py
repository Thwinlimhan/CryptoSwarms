"""Signal Decay Model — models signal confidence decay over time.

Signals lose value over time. This module calculates the decayed
confidence based on signal type-specific half-lives.
"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("swarm.signals.decay")


# Default half-lives in seconds by signal type
DEFAULT_SIGNAL_HALF_LIVES: dict[str, float] = {
    "funding": 3600.0,           # 1 hour — funding rates change slowly
    "liquidation": 300.0,        # 5 minutes — cascades happen fast
    "volume": 600.0,             # 10 minutes — volume signals decay moderately
    "order_flow": 180.0,         # 3 minutes — order flow is very ephemeral
    "technical": 1800.0,         # 30 minutes — technical patterns persist longer
    "sentiment": 7200.0,         # 2 hours — sentiment is slow-moving
    "momentum": 900.0,           # 15 minutes
    "mean_reversion": 1200.0,    # 20 minutes
    "volatility_breakout": 600.0, # 10 minutes
}


@dataclass
class Signal:
    """Signal representation for decay modeling."""
    signal_type: str
    confidence: float
    direction: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecayResult:
    """Result of signal decay calculation."""
    original_confidence: float
    decayed_confidence: float
    decay_factor: float
    age_seconds: float
    half_life_seconds: float
    is_stale: bool  # True if decayed below actionable threshold
    message: str


class SignalDecayModel:
    """Models signal confidence decay over time.

    Uses exponential decay with type-specific half-lives:
    confidence(t) = original_confidence * 0.5^(age / half_life)
    """

    def __init__(
        self,
        signal_half_lives: dict[str, float] | None = None,
        stale_threshold: float = 0.1,  # Below this = stale/unusable
        default_half_life: float = 600.0,  # 10 minutes default
    ) -> None:
        self.signal_half_lives = signal_half_lives or DEFAULT_SIGNAL_HALF_LIVES.copy()
        self.stale_threshold = stale_threshold
        self.default_half_life = default_half_life

    def calculate_decayed_confidence(
        self,
        signal: Signal,
        current_time: datetime | None = None,
    ) -> DecayResult:
        """Calculate the decayed confidence of a signal.

        Args:
            signal: The signal to evaluate.
            current_time: Current time (defaults to now).

        Returns:
            DecayResult with the decayed confidence.
        """
        now = current_time or datetime.now(timezone.utc)
        age_seconds = max(0, (now - signal.created_at).total_seconds())

        half_life = self.signal_half_lives.get(
            signal.signal_type, self.default_half_life
        )

        if half_life <= 0:
            decay_factor = 0.0
        else:
            decay_factor = 0.5 ** (age_seconds / half_life)

        decayed_confidence = signal.confidence * decay_factor
        is_stale = decayed_confidence < self.stale_threshold

        if is_stale:
            logger.debug(
                "Signal %s is stale: conf=%.4f (was %.4f), age=%.0fs, half_life=%.0fs",
                signal.signal_type, decayed_confidence, signal.confidence,
                age_seconds, half_life,
            )

        return DecayResult(
            original_confidence=signal.confidence,
            decayed_confidence=round(decayed_confidence, 6),
            decay_factor=round(decay_factor, 6),
            age_seconds=round(age_seconds, 1),
            half_life_seconds=half_life,
            is_stale=is_stale,
            message=(
                f"Stale after {age_seconds:.0f}s"
                if is_stale
                else f"Active: {decayed_confidence:.4f} ({decay_factor:.1%} remaining)"
            ),
        )

    def filter_stale_signals(
        self,
        signals: list[Signal],
        current_time: datetime | None = None,
    ) -> list[Signal]:
        """Filter out stale signals, returning only those above the threshold.

        Args:
            signals: List of signals to filter.
            current_time: Current time (defaults to now).

        Returns:
            List of non-stale signals.
        """
        now = current_time or datetime.now(timezone.utc)
        active = []
        for signal in signals:
            result = self.calculate_decayed_confidence(signal, now)
            if not result.is_stale:
                # Update the signal's confidence with decayed value
                signal.confidence = result.decayed_confidence
                active.append(signal)

        logger.debug(
            "Filtered signals: %d/%d active", len(active), len(signals),
        )
        return active

    def get_time_to_stale(self, signal: Signal) -> float:
        """Calculate how many seconds until a signal becomes stale.

        Returns:
            Seconds until stale, or 0 if already stale.
        """
        if signal.confidence <= self.stale_threshold:
            return 0.0

        half_life = self.signal_half_lives.get(
            signal.signal_type, self.default_half_life
        )

        if half_life <= 0:
            return 0.0

        # Solve: confidence * 0.5^(t/half_life) = stale_threshold
        # t = half_life * log2(confidence / stale_threshold)
        ratio = signal.confidence / self.stale_threshold
        if ratio <= 1:
            return 0.0

        return half_life * math.log2(ratio)
