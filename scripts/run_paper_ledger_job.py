from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from agents.backtest.institutional_gate import InstitutionalBenchmark, evaluate_institutional_benchmark
from cryptoswarms.base_rate_registry import default_base_rate_registry
from cryptoswarms.decision_engine import BinaryDecisionInput, evaluate_binary_decision
from cryptoswarms.fractional_kelly import empirical_fractional_kelly, position_size_from_bankroll
from cryptoswarms.paper_trading import (
    PaperTrade,
    PromotionScorecardPolicy,
    evaluate_promotion_scorecard,
    summarize_paper_window,
)


def _sample_trades(now: datetime) -> list[PaperTrade]:
    trades: list[PaperTrade] = []
    for i in range(40):
        pnl = 5.0 if i % 4 != 0 else -1.5
        trades.append(PaperTrade(time=now - timedelta(days=39 - i), strategy_id="phase1-btc-breakout-15m", pnl_usd=pnl))
    return trades


def _profit_factor(trades: list[PaperTrade]) -> float:
    wins = sum(t.pnl_usd for t in trades if t.pnl_usd > 0)
    losses = abs(sum(t.pnl_usd for t in trades if t.pnl_usd < 0))
    if losses == 0:
        return 999.0 if wins > 0 else 0.0
    return round(wins / losses, 4)


def main() -> None:
    now = datetime.now(timezone.utc)
    trades = _sample_trades(now)
    summary = summarize_paper_window(trades, now=now, lookback_days=30)
    if summary is None:
        raise RuntimeError("no paper trades available in lookback window")

    policy = PromotionScorecardPolicy(
        min_days=30,
        min_trades=30,
        min_sharpe=1.0,
        max_drawdown_usd=150.0,
        min_oos_sharpe=0.5,
        min_oos_to_is_ratio=0.6,
    )
    scorecard = evaluate_promotion_scorecard(summary, policy=policy)

    institutional = evaluate_institutional_benchmark(
        InstitutionalBenchmark(
            strategy_sharpe=summary.sharpe,
            strategy_max_drawdown=min(1.0, summary.max_drawdown_usd / max(1.0, abs(summary.total_pnl_usd) + 100.0)),
            strategy_profit_factor=_profit_factor(trades),
            strategy_trade_count=summary.trade_count,
            baseline_sharpe=1.0,
            baseline_max_drawdown=0.25,
        )
    )

    base_rates = default_base_rate_registry()
    prior = base_rates.empirical_bayes_prior(summary.strategy_id, fallback=0.52, pseudo_count=30)
    likelihood_if_true = min(0.9, 0.55 + max(0.0, summary.oos_stability_ratio) * 0.2)
    likelihood_if_false = max(0.1, 0.45 - max(0.0, summary.oos_stability_ratio - 0.6) * 0.1)

    decision = evaluate_binary_decision(
        BinaryDecisionInput(
            prior_probability=prior,
            likelihood_if_true=likelihood_if_true,
            likelihood_if_false=likelihood_if_false,
            payoff_win_usd=100.0,
            payoff_loss_usd=-80.0,
            fees_usd=3.0,
            slippage_usd=2.0,
        )
    )

    kelly_fraction = empirical_fractional_kelly(
        win_probability=decision.posterior_probability,
        payoff_multiple=1.0,
        uncertainty_cv=0.35,
        kelly_fraction_multiplier=0.5,
        max_fraction=0.2,
    )
    suggested_notional_usd = position_size_from_bankroll(bankroll_usd=50000.0, fraction=kelly_fraction)

    out_dir = Path("artifacts") / "phase1"
    out_dir.mkdir(parents=True, exist_ok=True)

    report = {
        "generated_at": now.isoformat(),
        "strategy_id": summary.strategy_id,
        "window_start": summary.start_time.isoformat(),
        "window_end": summary.end_time.isoformat(),
        "days_covered": summary.days_covered,
        "trade_count": summary.trade_count,
        "total_pnl_usd": summary.total_pnl_usd,
        "sharpe": summary.sharpe,
        "max_drawdown_usd": summary.max_drawdown_usd,
        "in_sample_sharpe": summary.in_sample_sharpe,
        "out_of_sample_sharpe": summary.out_of_sample_sharpe,
        "oos_stability_ratio": summary.oos_stability_ratio,
        "policy": {
            "min_days": policy.min_days,
            "min_trades": policy.min_trades,
            "min_sharpe": policy.min_sharpe,
            "max_drawdown_usd": policy.max_drawdown_usd,
            "min_oos_sharpe": policy.min_oos_sharpe,
            "min_oos_to_is_ratio": policy.min_oos_to_is_ratio,
        },
        "promotion_eligible": scorecard.eligible,
        "reasons": scorecard.reasons,
        "institutional_gate": {
            "accepted": institutional.accepted,
            "reasons": institutional.reasons,
        },
        "decision_math": {
            "base_rate_prior": round(prior, 6),
            "posterior_probability": decision.posterior_probability,
            "expected_value_usd": decision.expected_value_usd,
            "expected_value_after_costs_usd": decision.expected_value_after_costs_usd,
            "costs_usd": decision.costs_usd,
            "positive_edge": decision.positive_edge,
        },
        "sizing": {
            "kelly_fraction": kelly_fraction,
            "suggested_notional_usd": suggested_notional_usd,
            "bankroll_usd": 50000.0,
        },
    }
    out_path = out_dir / "paper_promotion_report.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Paper report written: {out_path}")


if __name__ == "__main__":
    main()
