from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExpansionContext:
    first_strategy_stable: bool
    execution_reliability_met: bool
    proven_bottleneck: bool
    sufficient_history_for_evolution: bool


@dataclass(frozen=True)
class ExpansionDecision:
    allow_second_strategy: bool
    allow_second_exchange: bool
    allow_new_agents: bool
    allow_evolution_activation: bool
    reasons: list[str]


def evaluate_expansion(context: ExpansionContext) -> ExpansionDecision:
    reasons: list[str] = []

    if not context.first_strategy_stable:
        reasons.append("first strategy not yet stable in paper/live")
    if not context.execution_reliability_met:
        reasons.append("execution reliability target not met")
    if not context.proven_bottleneck:
        reasons.append("no proven bottleneck for adding new agents")
    if not context.sufficient_history_for_evolution:
        reasons.append("insufficient history for evolution swarm")

    return ExpansionDecision(
        allow_second_strategy=context.first_strategy_stable,
        allow_second_exchange=context.execution_reliability_met,
        allow_new_agents=context.proven_bottleneck,
        allow_evolution_activation=context.sufficient_history_for_evolution,
        reasons=reasons,
    )
