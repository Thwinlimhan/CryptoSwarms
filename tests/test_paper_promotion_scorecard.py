from datetime import datetime, timedelta, timezone

from cryptoswarms.paper_trading import (
    PaperTrade,
    PromotionScorecardPolicy,
    evaluate_promotion_scorecard,
    summarize_paper_window,
)


def test_scorecard_blocks_low_sample_size():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    trades = [PaperTrade(time=now - timedelta(days=10 - i), strategy_id="s1", pnl_usd=2.0) for i in range(11)]

    summary = summarize_paper_window(trades, now=now, lookback_days=30)
    assert summary is not None
    result = evaluate_promotion_scorecard(summary, policy=PromotionScorecardPolicy(min_trades=30, min_days=10, min_sharpe=0.1))

    assert result.eligible is False
    assert any("sample size" in reason for reason in result.reasons)


def test_scorecard_includes_oos_and_drawdown_metrics():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    pnl = [4.0, 3.0, -1.0, 2.5, 3.2, -0.5, 3.5, 2.1, -0.4, 3.0, 2.8, -0.2, 3.4, 2.2, -0.3, 3.1, 2.9, -0.1, 3.3, 2.4, -0.2, 3.6, 2.7, -0.4, 3.0, 2.5, -0.2, 3.2, 2.6, -0.1, 3.5]
    trades = [PaperTrade(time=now - timedelta(days=30 - i), strategy_id="s1", pnl_usd=value) for i, value in enumerate(pnl)]

    summary = summarize_paper_window(trades, now=now, lookback_days=30)
    assert summary is not None

    assert summary.max_drawdown_usd >= 0
    assert isinstance(summary.out_of_sample_sharpe, float)
    assert isinstance(summary.oos_stability_ratio, float)
