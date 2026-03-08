from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CircuitBreakerLevel(str, Enum):
    """Tiered protections from the v6 plan risk framework."""

    NORMAL = "NORMAL"
    L1_WARNING = "L1_WARNING"
    L2_CAUTION = "L2_CAUTION"
    L3_HALT = "L3_HALT"
    L4_EMERGENCY = "L4_EMERGENCY"


@dataclass(frozen=True)
class RiskSnapshot:
    """Runtime risk view used to determine trading permissions."""

    daily_drawdown_pct: float
    portfolio_heat_pct: float
    near_liquidation: bool = False


@dataclass(frozen=True)
class CircuitBreakerDecision:
    level: CircuitBreakerLevel
    allow_new_entries: bool
    reduce_position_size_pct: int
    require_manual_resume: bool
    message: str


def evaluate_circuit_breaker(snapshot: RiskSnapshot) -> CircuitBreakerDecision:
    """Apply tiered rules defined in the master plan.

    Input values are expected as positive percentages (e.g., 4.2 for -4.2% DD).
    """

    dd = snapshot.daily_drawdown_pct
    heat = snapshot.portfolio_heat_pct

    if snapshot.near_liquidation or dd >= 8.0:
        return CircuitBreakerDecision(
            level=CircuitBreakerLevel.L4_EMERGENCY,
            allow_new_entries=False,
            reduce_position_size_pct=100,
            require_manual_resume=True,
            message="Emergency: close riskiest position and require operator RESUME.",
        )

    if dd >= 5.0 or heat >= 20.0:
        return CircuitBreakerDecision(
            level=CircuitBreakerLevel.L3_HALT,
            allow_new_entries=False,
            reduce_position_size_pct=100,
            require_manual_resume=True,
            message="Circuit breaker active: full trading halt.",
        )

    if dd >= 4.0 or heat >= 18.0:
        return CircuitBreakerDecision(
            level=CircuitBreakerLevel.L2_CAUTION,
            allow_new_entries=False,
            reduce_position_size_pct=100,
            require_manual_resume=False,
            message="Caution: hold existing positions, block new entries.",
        )

    if dd >= 3.0 or heat >= 15.0:
        return CircuitBreakerDecision(
            level=CircuitBreakerLevel.L1_WARNING,
            allow_new_entries=True,
            reduce_position_size_pct=50,
            require_manual_resume=False,
            message="Warning: trading continues with reduced size.",
        )

    return CircuitBreakerDecision(
        level=CircuitBreakerLevel.NORMAL,
        allow_new_entries=True,
        reduce_position_size_pct=0,
        require_manual_resume=False,
        message="Normal operations.",
    )
