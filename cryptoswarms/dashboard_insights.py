from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Mapping, Sequence


@dataclass(frozen=True)
class DashboardInsightInput:
    trade_rows: Sequence[Mapping[str, object]]
    validation_rows: Sequence[Mapping[str, object]]
    signal_rows: Sequence[Mapping[str, object]]
    attribution_rows: Sequence[Mapping[str, object]]
    regime: Mapping[str, object]
    risk_event: Mapping[str, object] | None


def build_dashboard_insights(payload: DashboardInsightInput) -> dict[str, object]:
    pnl_series = [_to_float(row.get("realised_pnl")) for row in payload.trade_rows]
    slippage_series = [_to_float(row.get("slippage_bps")) for row in payload.trade_rows]
    trade_stats = _compute_trade_stats(pnl_series, slippage_series)

    validation_outcomes = [bool(row.get("passed")) for row in payload.validation_rows if row.get("passed") is not None]
    signal_conf = [_to_float(row.get("confidence")) for row in payload.signal_rows]
    signal_acted = [bool(row.get("acted_on")) for row in payload.signal_rows]

    validation_stats = _compute_validation_stats(validation_outcomes)
    signal_stats = _compute_signal_stats(signal_conf, signal_acted)
    attribution_stats = _compute_attribution_stats(payload.attribution_rows)

    risk_summary = {
        "latest_level": int(payload.risk_event.get("level", 0)) if payload.risk_event else 0,
        "latest_trigger": str(payload.risk_event.get("trigger", "none")) if payload.risk_event else "none",
        "portfolio_heat": round(_to_float(payload.risk_event.get("portfolio_heat")) if payload.risk_event else 0.0, 4),
        "daily_dd": round(_to_float(payload.risk_event.get("daily_dd")) if payload.risk_event else 0.0, 4),
        "event_time": _dt_iso(payload.risk_event.get("time")) if payload.risk_event else None,
    }

    insights = _build_operator_insights(
        trade_count=trade_stats["trades"],
        total_pnl=trade_stats["total_pnl_usd"],
        max_drawdown=trade_stats["max_drawdown_usd"],
        win_rate=trade_stats["win_rate"],
        validation_pass_rate=validation_stats["pass_rate"],
        avg_slippage_bps=trade_stats["avg_slippage_bps"],
        acted_ratio=signal_stats["acted_ratio"],
        attribution_coverage=attribution_stats["coverage_ratio"],
        risk_level=risk_summary["latest_level"],
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "trade_stats": trade_stats,
        "validation_stats": validation_stats,
        "signal_stats": signal_stats,
        "attribution_stats": attribution_stats,
        "regime": {
            "name": str(payload.regime.get("regime", "unknown")),
            "confidence": round(_to_float(payload.regime.get("confidence")), 4),
        },
        "risk": risk_summary,
        "operator_insights": insights,
    }


def _compute_trade_stats(pnl_series: Sequence[float], slippage_series: Sequence[float]) -> dict[str, float | int]:
    trades = len(pnl_series)
    wins = [p for p in pnl_series if p > 0]
    losses = [p for p in pnl_series if p < 0]
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    total_pnl = sum(pnl_series)
    win_rate = (len(wins) / trades) if trades > 0 else 0.0

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for pnl in pnl_series:
        cumulative += pnl
        peak = max(peak, cumulative)
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    sharpe_like = 0.0
    if trades >= 2:
        sigma = pstdev(pnl_series)
        if sigma > 0:
            sharpe_like = (mean(pnl_series) / sigma) * (trades**0.5)

    avg_slippage = mean(slippage_series) if slippage_series else 0.0
    return {
        "trades": trades,
        "total_pnl_usd": round(total_pnl, 4),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown_usd": round(max_drawdown, 4),
        "avg_slippage_bps": round(avg_slippage, 4),
        "sharpe_like": round(sharpe_like, 4),
    }


def _compute_validation_stats(outcomes: Sequence[bool]) -> dict[str, float | int]:
    total = len(outcomes)
    passed = sum(1 for item in outcomes if item)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": round((passed / total), 4) if total else 0.0,
    }


def _compute_signal_stats(confidences: Sequence[float], acted: Sequence[bool]) -> dict[str, float | int]:
    total = len(confidences)
    acted_count = sum(1 for item in acted if item)
    avg_conf = mean(confidences) if confidences else 0.0
    return {
        "total": total,
        "acted": acted_count,
        "acted_ratio": round((acted_count / total), 4) if total else 0.0,
        "avg_confidence": round(avg_conf, 4),
    }


def _compute_attribution_stats(rows: Sequence[Mapping[str, object]]) -> dict[str, float | int]:
    total = len(rows)
    traced = 0
    for row in rows:
        if all(
            isinstance(row.get(k), str) and str(row.get(k)).strip()
            for k in ("hypothesis_id", "optimizer_run_id", "optimizer_candidate_id")
        ):
            traced += 1
    return {
        "total": total,
        "traced": traced,
        "coverage_ratio": round((traced / total), 4) if total else 0.0,
    }


def _build_operator_insights(
    *,
    trade_count: int,
    total_pnl: float,
    max_drawdown: float,
    win_rate: float,
    validation_pass_rate: float,
    avg_slippage_bps: float,
    acted_ratio: float,
    attribution_coverage: float,
    risk_level: int,
) -> list[str]:
    items: list[str] = []

    if trade_count == 0:
        items.append("No live trade data is available for the lookback window. Treat dashboard PnL and drawdown as unavailable.")
        return items

    if total_pnl <= 0:
        items.append("PnL is non-positive for the lookback window. Tighten promotion gates before scaling exposure.")
    else:
        items.append("PnL is positive in the lookback window. Keep current risk limits until another full review cycle passes.")

    if max_drawdown > max(25.0, abs(total_pnl) * 0.6):
        items.append("Drawdown is elevated relative to profits. Reduce size multiplier and review loss clustering.")

    if win_rate < 0.45:
        items.append("Win rate is below 45%. Improve selectivity through higher confidence and stricter regime filters.")

    if validation_pass_rate < 0.6:
        items.append("Validation pass-rate is below 60%. Investigate gate failures before admitting new strategies.")

    if attribution_coverage < 0.95:
        items.append("Attribution coverage is below 95%. Block live scaling until all trades map to hypothesis and optimizer lineage.")

    if avg_slippage_bps > 8.0:
        items.append("Average slippage is above 8 bps. Enforce tighter impact guardrails and venue routing checks.")

    if acted_ratio > 0.8:
        items.append("Acted-on ratio is very high. Ensure scanner is not over-triggering low-edge signals.")

    if risk_level >= 3:
        items.append("Recent risk event level is critical. Keep execution in defensive mode until risk events normalize.")

    if not items:
        items.append("Metrics are stable. Continue current settings and monitor for regime shift.")
    return items


def _to_float(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _dt_iso(value: object) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    return None
