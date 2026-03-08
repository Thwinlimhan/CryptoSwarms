from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScaleReadiness:
    first_strategy_stable: bool
    execution_reliability_slo_met: bool
    core_alpha_stable: bool


@dataclass(frozen=True)
class ScaleDecision:
    allow_second_strategy: bool
    allow_second_venue: bool
    allow_polymarket_modifier: bool
    reasons: list[str]


def evaluate_scale_readiness(readiness: ScaleReadiness) -> ScaleDecision:
    reasons: list[str] = []

    if not readiness.first_strategy_stable:
        reasons.append("first strategy not yet stable")
    if not readiness.execution_reliability_slo_met:
        reasons.append("execution reliability SLO not met")
    if not readiness.core_alpha_stable:
        reasons.append("core alpha not yet stable")

    return ScaleDecision(
        allow_second_strategy=readiness.first_strategy_stable,
        allow_second_venue=readiness.execution_reliability_slo_met,
        allow_polymarket_modifier=readiness.core_alpha_stable,
        reasons=reasons,
    )
