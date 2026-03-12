from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DelegationRequest:
    stage: str
    task_type: str
    project_id: str
    strategy_id: str


@dataclass(frozen=True)
class DelegationDecision:
    allowed: bool
    reason: str


class DelegationPolicy:
    """A2A delegation policy: allow only controlled internal stages, never bypass governor/risk constraints."""

    def __init__(self, *, allowed_stages: tuple[str, ...] = ("research", "debate", "aggregation")) -> None:
        self.allowed_stages = set(allowed_stages)

    def authorize(
        self,
        *,
        request: DelegationRequest,
        scorecard_eligible: bool,
        institutional_gate_ok: bool,
        attribution_ready: bool,
        risk_halt_active: bool,
    ) -> DelegationDecision:
        if request.stage not in self.allowed_stages:
            return DelegationDecision(False, f"delegation stage not allowed: {request.stage}")
        if risk_halt_active:
            return DelegationDecision(False, "risk halt active")
        if not scorecard_eligible:
            return DelegationDecision(False, "scorecard not eligible")
        if not institutional_gate_ok:
            return DelegationDecision(False, "institutional gate failed")
        if not attribution_ready:
            return DelegationDecision(False, "attribution not ready")
        return DelegationDecision(True, "ok")
