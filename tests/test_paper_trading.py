from datetime import datetime, timedelta, timezone

from cryptoswarms.paper_trading import PaperTrade, promotion_decision, summarize_paper_window


def test_paper_window_summary_and_promotion_decision():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    trades = [
        PaperTrade(time=now - timedelta(days=30 - i), strategy_id="s1", pnl_usd=(4.0 if i % 2 == 0 else 1.0))
        for i in range(31)
    ]

    summary = summarize_paper_window(trades, now=now, lookback_days=30)
    assert summary is not None
    assert summary.days_covered >= 30

    eligible, reason = promotion_decision(summary, min_days=30, min_sharpe=0.2)
    assert eligible is True
    assert "eligible" in reason
