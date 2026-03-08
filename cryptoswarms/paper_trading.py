from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class PaperTrade:
    time: datetime
    strategy_id: str
    pnl_usd: float


@dataclass(frozen=True)
class PaperWindowSummary:
    strategy_id: str
    start_time: datetime
    end_time: datetime
    days_covered: int
    trade_count: int
    total_pnl_usd: float
    sharpe: float
    max_drawdown_usd: float
    in_sample_sharpe: float
    out_of_sample_sharpe: float
    oos_stability_ratio: float


@dataclass(frozen=True)
class PromotionScorecardPolicy:
    min_days: int = 30
    min_trades: int = 30
    min_sharpe: float = 1.0
    max_drawdown_usd: float = 150.0
    min_oos_sharpe: float = 0.5
    min_oos_to_is_ratio: float = 0.6


@dataclass(frozen=True)
class PromotionScorecardResult:
    eligible: bool
    reasons: list[str]
    summary: PaperWindowSummary


def _compute_sharpe(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    std = statistics.pstdev(values)
    if std == 0:
        return 0.0
    return statistics.fmean(values) / std * math.sqrt(252)


def _max_drawdown(values: list[float]) -> float:
    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for pnl in values:
        cumulative += pnl
        peak = max(peak, cumulative)
        dd = peak - cumulative
        if dd > max_dd:
            max_dd = dd
    return max_dd


def _split_is_oos(values: list[float]) -> tuple[list[float], list[float]]:
    if len(values) < 4:
        return values, values
    split = max(2, int(len(values) * 0.7))
    split = min(split, len(values) - 2)
    return values[:split], values[split:]


def summarize_paper_window(trades: list[PaperTrade], *, now: datetime | None = None, lookback_days: int = 30) -> PaperWindowSummary | None:
    if not trades:
        return None

    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    strategy_id = trades[0].strategy_id
    start = now - timedelta(days=lookback_days)
    window = [t for t in trades if t.time >= start]
    if not window:
        return None

    ordered = sorted(window, key=lambda t: t.time)
    pnl_series = [float(t.pnl_usd) for t in ordered]
    in_sample, out_of_sample = _split_is_oos(pnl_series)

    in_sample_sharpe = _compute_sharpe(in_sample)
    oos_sharpe = _compute_sharpe(out_of_sample)
    if in_sample_sharpe > 0:
        stability_ratio = oos_sharpe / in_sample_sharpe
    else:
        stability_ratio = 1.0 if oos_sharpe > 0 else 0.0

    summary = PaperWindowSummary(
        strategy_id=strategy_id,
        start_time=min(t.time for t in ordered),
        end_time=max(t.time for t in ordered),
        days_covered=max(1, (max(t.time for t in ordered).date() - min(t.time for t in ordered).date()).days + 1),
        trade_count=len(ordered),
        total_pnl_usd=round(sum(pnl_series), 4),
        sharpe=round(_compute_sharpe(pnl_series), 4),
        max_drawdown_usd=round(_max_drawdown(pnl_series), 4),
        in_sample_sharpe=round(in_sample_sharpe, 4),
        out_of_sample_sharpe=round(oos_sharpe, 4),
        oos_stability_ratio=round(stability_ratio, 4),
    )
    return summary


def evaluate_promotion_scorecard(
    summary: PaperWindowSummary,
    *,
    policy: PromotionScorecardPolicy = PromotionScorecardPolicy(),
) -> PromotionScorecardResult:
    reasons: list[str] = []

    if summary.days_covered < policy.min_days:
        reasons.append(f"insufficient paper history: {summary.days_covered}d < {policy.min_days}d")
    if summary.trade_count < policy.min_trades:
        reasons.append(f"insufficient sample size: {summary.trade_count} < {policy.min_trades}")
    if summary.sharpe < policy.min_sharpe:
        reasons.append(f"paper sharpe below threshold: {summary.sharpe:.3f} < {policy.min_sharpe:.3f}")
    if summary.max_drawdown_usd > policy.max_drawdown_usd:
        reasons.append(
            f"drawdown above threshold: {summary.max_drawdown_usd:.3f} > {policy.max_drawdown_usd:.3f}"
        )
    if summary.out_of_sample_sharpe < policy.min_oos_sharpe:
        reasons.append(
            f"out-of-sample sharpe below threshold: {summary.out_of_sample_sharpe:.3f} < {policy.min_oos_sharpe:.3f}"
        )
    if summary.oos_stability_ratio < policy.min_oos_to_is_ratio:
        reasons.append(
            f"out-of-sample stability below threshold: {summary.oos_stability_ratio:.3f} < {policy.min_oos_to_is_ratio:.3f}"
        )

    return PromotionScorecardResult(eligible=(len(reasons) == 0), reasons=reasons, summary=summary)


def promotion_decision(summary: PaperWindowSummary, *, min_days: int = 30, min_sharpe: float = 1.0) -> tuple[bool, str]:
    # Backward-compatible wrapper now routed through strict scorecard policy.
    result = evaluate_promotion_scorecard(
        summary,
        policy=PromotionScorecardPolicy(
            min_days=min_days,
            min_trades=30,
            min_sharpe=min_sharpe,
            max_drawdown_usd=150.0,
            min_oos_sharpe=0.5,
            min_oos_to_is_ratio=0.6,
        ),
    )
    if result.eligible:
        return True, "eligible for live promotion review"
    return False, "; ".join(result.reasons)
