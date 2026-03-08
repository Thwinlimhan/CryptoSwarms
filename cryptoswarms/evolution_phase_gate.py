from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvolutionReadiness:
    live_strategies: int
    paper_history_days: int
    live_history_days: int


def letta_activation_allowed(readiness: EvolutionReadiness) -> tuple[bool, str]:
    if readiness.live_strategies < 3:
        return False, "requires at least 3 live strategies"
    if readiness.paper_history_days < 90:
        return False, "requires at least 90 days paper history"
    if readiness.live_history_days < 60:
        return False, "requires at least 60 days live history"
    return True, "phase 4 readiness satisfied"
