from datetime import datetime, timedelta, timezone

import pytest

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


def test_paper_window_summary_rejects_mixed_strategy_trades():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    trades = [
        PaperTrade(time=now - timedelta(days=3), strategy_id="s1", pnl_usd=3.0),
        PaperTrade(time=now - timedelta(days=2), strategy_id="s2", pnl_usd=1.0),
    ]

    with pytest.raises(ValueError, match="single strategy"):
        summarize_paper_window(trades, now=now, lookback_days=30)
