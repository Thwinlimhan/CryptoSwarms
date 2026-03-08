from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InstitutionalBenchmark:
    strategy_sharpe: float
    strategy_max_drawdown: float
    strategy_profit_factor: float
    strategy_trade_count: int
    baseline_sharpe: float
    baseline_max_drawdown: float


@dataclass(frozen=True)
class InstitutionalGatePolicy:
    min_excess_sharpe: float = 0.15
    max_drawdown: float = 0.2
    min_profit_factor: float = 1.2
    min_trade_count: int = 120


@dataclass(frozen=True)
class InstitutionalGateDecision:
    accepted: bool
    reasons: list[str]


def evaluate_institutional_benchmark(
    benchmark: InstitutionalBenchmark,
    *,
    policy: InstitutionalGatePolicy = InstitutionalGatePolicy(),
) -> InstitutionalGateDecision:
    reasons: list[str] = []

    excess_sharpe = benchmark.strategy_sharpe - benchmark.baseline_sharpe
    if excess_sharpe < policy.min_excess_sharpe:
        reasons.append(
            f"excess sharpe below threshold: {excess_sharpe:.3f} < {policy.min_excess_sharpe:.3f}"
        )

    if benchmark.strategy_max_drawdown > policy.max_drawdown:
        reasons.append(
            f"max drawdown above threshold: {benchmark.strategy_max_drawdown:.3f} > {policy.max_drawdown:.3f}"
        )

    if benchmark.strategy_max_drawdown > benchmark.baseline_max_drawdown:
        reasons.append(
            f"drawdown worse than baseline: {benchmark.strategy_max_drawdown:.3f} > {benchmark.baseline_max_drawdown:.3f}"
        )

    if benchmark.strategy_profit_factor < policy.min_profit_factor:
        reasons.append(
            f"profit factor below threshold: {benchmark.strategy_profit_factor:.3f} < {policy.min_profit_factor:.3f}"
        )

    if benchmark.strategy_trade_count < policy.min_trade_count:
        reasons.append(
            f"trade count below threshold: {benchmark.strategy_trade_count} < {policy.min_trade_count}"
        )

    return InstitutionalGateDecision(accepted=len(reasons) == 0, reasons=reasons)
