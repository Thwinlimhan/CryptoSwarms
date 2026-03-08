from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .deadman import (
    DeadMansSwitchConfig,
    DeadMansSwitchState,
    evaluate_dead_mans_switch,
)
from .risk import CircuitBreakerLevel, CircuitBreakerDecision, RiskSnapshot, evaluate_circuit_breaker


@dataclass(frozen=True)
class ExecutionGateDecision:
    allow_entries: bool
    allow_reductions_only: bool
    blocked_reason: str
    risk_decision: CircuitBreakerDecision
    deadman_state: DeadMansSwitchState


def evaluate_pre_execution_gate(
    *,
    risk_snapshot: RiskSnapshot,
    now: datetime,
    last_risk_heartbeat: datetime | None,
    current_halt_state: DeadMansSwitchState,
    deadman_config: DeadMansSwitchConfig = DeadMansSwitchConfig(),
) -> ExecutionGateDecision:
    """Single pre-trade gate combining risk tiers + dead-man switch state.

    Policy:
    - Dead-man HALT always blocks new entries and forces reductions-only mode.
    - If dead-man is healthy, circuit-breaker tiers decide if entries are allowed.
    - L2/L3/L4 risk tiers are reductions-only mode.
    """

    deadman_state = evaluate_dead_mans_switch(
        now=now,
        last_risk_heartbeat=last_risk_heartbeat,
        current_halt_state=current_halt_state,
        config=deadman_config,
    )
    risk_decision = evaluate_circuit_breaker(risk_snapshot)

    if deadman_state.halted:
        return ExecutionGateDecision(
            allow_entries=False,
            allow_reductions_only=True,
            blocked_reason=f"Dead-man switch active: {deadman_state.reason}",
            risk_decision=risk_decision,
            deadman_state=deadman_state,
        )

    reductions_only = risk_decision.level in {
        CircuitBreakerLevel.L2_CAUTION,
        CircuitBreakerLevel.L3_HALT,
        CircuitBreakerLevel.L4_EMERGENCY,
    }

    if not risk_decision.allow_new_entries:
        return ExecutionGateDecision(
            allow_entries=False,
            allow_reductions_only=reductions_only,
            blocked_reason=f"Risk gate active: {risk_decision.level}",
            risk_decision=risk_decision,
            deadman_state=deadman_state,
        )

    return ExecutionGateDecision(
        allow_entries=True,
        allow_reductions_only=False,
        blocked_reason="",
        risk_decision=risk_decision,
        deadman_state=deadman_state,
    )
