from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyDurabilityReport:
    regimes_tested: int
    profitable_regimes: int
    min_regime_sharpe: float
    max_regime_drawdown: float
    live_days: int


@dataclass(frozen=True)
class StrategyCountPolicy:
    max_without_durability: int = 1
    min_regimes_tested: int = 3
    min_profitable_regimes: int = 2
    min_regime_sharpe: float = 0.8
    max_regime_drawdown: float = 0.2
    min_live_days: int = 60


@dataclass(frozen=True)
class StrategyCountDecision:
    approved: bool
    requested_count: int
    max_allowed_count: int
    reasons: list[str]


def is_durable_across_regimes(
    report: StrategyDurabilityReport,
    *,
    policy: StrategyCountPolicy = StrategyCountPolicy(),
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if report.regimes_tested < policy.min_regimes_tested:
        reasons.append(f"regimes tested below threshold: {report.regimes_tested} < {policy.min_regimes_tested}")
    if report.profitable_regimes < policy.min_profitable_regimes:
        reasons.append(
            f"profitable regimes below threshold: {report.profitable_regimes} < {policy.min_profitable_regimes}"
        )
    if report.min_regime_sharpe < policy.min_regime_sharpe:
        reasons.append(f"minimum regime sharpe below threshold: {report.min_regime_sharpe:.3f} < {policy.min_regime_sharpe:.3f}")
    if report.max_regime_drawdown > policy.max_regime_drawdown:
        reasons.append(
            f"regime drawdown above threshold: {report.max_regime_drawdown:.3f} > {policy.max_regime_drawdown:.3f}"
        )
    if report.live_days < policy.min_live_days:
        reasons.append(f"live days below threshold: {report.live_days} < {policy.min_live_days}")
    return len(reasons) == 0, reasons


def enforce_strategy_count(
    active_strategy_ids: list[str],
    *,
    durability_report: StrategyDurabilityReport | None,
    policy: StrategyCountPolicy = StrategyCountPolicy(),
) -> StrategyCountDecision:
    requested = len(active_strategy_ids)
    if requested <= policy.max_without_durability:
        return StrategyCountDecision(
            approved=True,
            requested_count=requested,
            max_allowed_count=policy.max_without_durability,
            reasons=[],
        )

    if durability_report is None:
        return StrategyCountDecision(
            approved=False,
            requested_count=requested,
            max_allowed_count=policy.max_without_durability,
            reasons=["durability report required before running more than one strategy"],
        )

    durable, reasons = is_durable_across_regimes(durability_report, policy=policy)
    return StrategyCountDecision(
        approved=durable,
        requested_count=requested,
        max_allowed_count=(requested if durable else policy.max_without_durability),
        reasons=reasons,
    )
