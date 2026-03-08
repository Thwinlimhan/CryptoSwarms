from datetime import datetime, timezone

from cryptoswarms.reporting import build_daily_summary


def test_build_daily_summary_counts_signals():
    summary = build_daily_summary(
        strategy_id="s1",
        signals=[{"signal_type": "BREAKOUT"}, {"signal_type": "REGIME"}],
        accepted_candidates=1,
        rejected_candidates=1,
        paper_trades=1,
        gross_pnl_usd=10.0,
        llm_cost_usd=0.2,
        now=datetime(2026, 3, 8, 0, 0, tzinfo=timezone.utc),
    )

    assert summary.date == "2026-03-08"
    assert summary.total_signals == 2
    assert "Daily Summary" in summary.as_markdown()
