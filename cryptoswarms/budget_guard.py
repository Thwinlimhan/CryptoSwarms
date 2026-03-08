from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetStatus:
    spent_usd: float
    budget_usd: float
    alert_threshold_usd: float
    within_budget: bool
    alert: bool
    blocked: bool


@dataclass(frozen=True)
class BudgetConfig:
    daily_budget_usd: float = 10.0
    alert_threshold_ratio: float = 0.7


def evaluate_budget(spent_usd: float, config: BudgetConfig = BudgetConfig()) -> BudgetStatus:
    spent = max(0.0, float(spent_usd))
    threshold = config.daily_budget_usd * config.alert_threshold_ratio
    return BudgetStatus(
        spent_usd=spent,
        budget_usd=config.daily_budget_usd,
        alert_threshold_usd=threshold,
        within_budget=spent <= config.daily_budget_usd,
        alert=spent >= threshold,
        blocked=spent > config.daily_budget_usd,
    )
