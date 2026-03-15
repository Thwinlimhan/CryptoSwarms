from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from .deadman import DeadMansSwitchConfig, DeadMansSwitchState
from .execution_guard import ExecutionGateDecision, evaluate_pre_execution_gate
from .risk import RiskSnapshot


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    quantity: float
    reduce_only: bool = False


@dataclass(frozen=True)
class RoutedOrderDecision:
    accepted: bool
    reason: str
    effective_reduce_only: bool
    gate: ExecutionGateDecision


class OrderExecutor(Protocol):
    async def execute(self, intent: OrderIntent, reduce_only: bool = False) -> None: ...


class ExecutionRouter:
    """Skeleton router that enforces pre-execution safety gates before order execution."""

    def __init__(self, executor: OrderExecutor) -> None:
        self._executor = executor

    async def route(
        self,
        *,
        intent: OrderIntent,
        now: datetime,
        risk_snapshot: RiskSnapshot,
        last_risk_heartbeat: datetime | None,
        current_halt_state: DeadMansSwitchState,
        deadman_config: DeadMansSwitchConfig = DeadMansSwitchConfig(),
    ) -> RoutedOrderDecision:
        gate = evaluate_pre_execution_gate(
            risk_snapshot=risk_snapshot,
            now=now,
            last_risk_heartbeat=last_risk_heartbeat,
            current_halt_state=current_halt_state,
            deadman_config=deadman_config,
        )

        if gate.allow_entries:
            await self._executor.execute(intent, reduce_only=False)
            return RoutedOrderDecision(True, "accepted", False, gate)

        if gate.allow_reductions_only and intent.reduce_only:
            await self._executor.execute(intent, reduce_only=True)
            return RoutedOrderDecision(True, "accepted (reductions-only mode)", True, gate)

        return RoutedOrderDecision(False, gate.blocked_reason or "blocked by gate", gate.allow_reductions_only, gate)
