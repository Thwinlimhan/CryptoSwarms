"""Degradation Manager — graceful system degradation under stress.

When issues are detected, reduces system risk exposure by:
- Increasing confidence thresholds
- Reducing max position sizes
- Limiting trading frequency
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("swarm.resilience.degradation")


class DegradationLevel(str, Enum):
    NORMAL = "NORMAL"
    MILD = "MILD"          # Slightly reduced activity
    MODERATE = "MODERATE"  # Significantly reduced activity
    SEVERE = "SEVERE"      # Only essential operations
    CRITICAL = "CRITICAL"  # Full halt except monitoring


@dataclass
class DegradationConfig:
    """Configuration that gets adjusted during degradation."""
    min_confidence: float = 0.3
    max_position_size: float = 1.0  # Multiplier (1.0 = 100%)
    max_concurrent_positions: int = 10
    signal_processing_interval: float = 1.0  # Multiplier
    allow_new_entries: bool = True
    allow_existing_exits: bool = True
    reason: str = "Normal operations"


# Degradation level presets
DEGRADATION_PRESETS: dict[DegradationLevel, DegradationConfig] = {
    DegradationLevel.NORMAL: DegradationConfig(
        min_confidence=0.3,
        max_position_size=1.0,
        max_concurrent_positions=10,
        signal_processing_interval=1.0,
        allow_new_entries=True,
        allow_existing_exits=True,
    ),
    DegradationLevel.MILD: DegradationConfig(
        min_confidence=0.4,
        max_position_size=0.75,
        max_concurrent_positions=7,
        signal_processing_interval=1.5,
        allow_new_entries=True,
        allow_existing_exits=True,
    ),
    DegradationLevel.MODERATE: DegradationConfig(
        min_confidence=0.5,
        max_position_size=0.5,
        max_concurrent_positions=5,
        signal_processing_interval=2.0,
        allow_new_entries=True,
        allow_existing_exits=True,
    ),
    DegradationLevel.SEVERE: DegradationConfig(
        min_confidence=0.7,
        max_position_size=0.25,
        max_concurrent_positions=3,
        signal_processing_interval=3.0,
        allow_new_entries=False,
        allow_existing_exits=True,
    ),
    DegradationLevel.CRITICAL: DegradationConfig(
        min_confidence=1.0,  # Effectively blocks all signals
        max_position_size=0.0,
        max_concurrent_positions=0,
        signal_processing_interval=5.0,
        allow_new_entries=False,
        allow_existing_exits=True,
        reason="Critical degradation — manual intervention required",
    ),
}


@dataclass
class DegradationEvent:
    """Record of a degradation state change."""
    timestamp: datetime
    previous_level: DegradationLevel
    new_level: DegradationLevel
    reason: str


class DegradationManager:
    """Manages graceful system degradation under stress.

    Adjusts system parameters (confidence thresholds, position sizes)
    based on detected issues to reduce risk exposure.
    """

    def __init__(
        self,
        presets: dict[DegradationLevel, DegradationConfig] | None = None,
    ) -> None:
        self._presets = presets or DEGRADATION_PRESETS
        self._current_level = DegradationLevel.NORMAL
        self._config = DegradationConfig()
        self._history: list[DegradationEvent] = []

    @property
    def level(self) -> DegradationLevel:
        return self._current_level

    @property
    def config(self) -> DegradationConfig:
        return self._config

    def enter_degraded_mode(
        self,
        reason: str,
        level: DegradationLevel | None = None,
    ) -> DegradationConfig:
        """Enter a degraded operating mode.

        Args:
            reason: Why degradation is being triggered.
            level: Specific degradation level, or auto-escalate if None.

        Returns:
            The new DegradationConfig in effect.
        """
        previous = self._current_level

        if level is not None:
            self._current_level = level
        else:
            # Auto-escalate one level
            levels = list(DegradationLevel)
            current_idx = levels.index(self._current_level)
            if current_idx < len(levels) - 1:
                self._current_level = levels[current_idx + 1]

        self._config = DegradationConfig(
            **{k: v for k, v in self._presets[self._current_level].__dict__.items()
               if k != "reason"}
        )
        self._config.reason = reason

        event = DegradationEvent(
            timestamp=datetime.now(timezone.utc),
            previous_level=previous,
            new_level=self._current_level,
            reason=reason,
        )
        self._history.append(event)

        logger.warning(
            "Entering degraded mode: %s → %s | Reason: %s | "
            "min_confidence=%.2f, max_position_size=%.0f%%",
            previous.value, self._current_level.value, reason,
            self._config.min_confidence,
            self._config.max_position_size * 100,
        )

        return self._config

    def recover(self, reason: str = "Manual recovery") -> DegradationConfig:
        """Recover one degradation level toward NORMAL.

        Returns:
            The new DegradationConfig in effect.
        """
        previous = self._current_level
        levels = list(DegradationLevel)
        current_idx = levels.index(self._current_level)

        if current_idx > 0:
            self._current_level = levels[current_idx - 1]
            self._config = DegradationConfig(
                **{k: v for k, v in self._presets[self._current_level].__dict__.items()
                   if k != "reason"}
            )
            self._config.reason = reason

            event = DegradationEvent(
                timestamp=datetime.now(timezone.utc),
                previous_level=previous,
                new_level=self._current_level,
                reason=reason,
            )
            self._history.append(event)

            logger.info(
                "Recovering from degradation: %s → %s | Reason: %s",
                previous.value, self._current_level.value, reason,
            )

        return self._config

    def reset(self, reason: str = "Full system reset") -> DegradationConfig:
        """Reset directly to NORMAL mode."""
        return self.enter_degraded_mode(reason, DegradationLevel.NORMAL)

    @property
    def is_degraded(self) -> bool:
        return self._current_level != DegradationLevel.NORMAL

    @property
    def history(self) -> list[DegradationEvent]:
        return list(self._history)

    def get_status(self) -> dict[str, Any]:
        """Return current degradation status."""
        return {
            "level": self._current_level.value,
            "is_degraded": self.is_degraded,
            "config": {
                "min_confidence": self._config.min_confidence,
                "max_position_size": self._config.max_position_size,
                "max_concurrent_positions": self._config.max_concurrent_positions,
                "allow_new_entries": self._config.allow_new_entries,
                "reason": self._config.reason,
            },
            "history_count": len(self._history),
        }
