from datetime import datetime, timezone

from cryptoswarms.dashboard_insights import DashboardInsightInput, build_dashboard_insights


def test_build_dashboard_insights_computes_core_metrics():
    payload = DashboardInsightInput(
        trade_rows=[
            {"realised_pnl": 10.0, "slippage_bps": 2.0},
            {"realised_pnl": -4.0, "slippage_bps": 3.0},
            {"realised_pnl": 6.0, "slippage_bps": 1.5},
        ],
        validation_rows=[{"passed": True}, {"passed": False}, {"passed": True}],
        signal_rows=[
            {"confidence": 0.8, "acted_on": True},
            {"confidence": 0.6, "acted_on": False},
            {"confidence": 0.9, "acted_on": True},
        ],
        regime={"regime": "trending_up", "confidence": 0.72},
        risk_event={"level": 2, "trigger": "heat", "portfolio_heat": 0.48, "daily_dd": 0.02, "time": datetime(2026, 3, 8, tzinfo=timezone.utc)},
    )

    out = build_dashboard_insights(payload)

    assert out["trade_stats"]["trades"] == 3
    assert out["trade_stats"]["total_pnl_usd"] == 12.0
    assert out["validation_stats"]["pass_rate"] == 0.6667
    assert out["signal_stats"]["acted_ratio"] == 0.6667
    assert out["regime"]["name"] == "trending_up"


def test_build_dashboard_insights_emits_actionable_warnings_for_weak_metrics():
    payload = DashboardInsightInput(
        trade_rows=[
            {"realised_pnl": -5.0, "slippage_bps": 10.0},
            {"realised_pnl": -3.0, "slippage_bps": 12.0},
            {"realised_pnl": 1.0, "slippage_bps": 9.0},
        ],
        validation_rows=[{"passed": False}, {"passed": False}],
        signal_rows=[
            {"confidence": 0.4, "acted_on": True},
            {"confidence": 0.5, "acted_on": True},
            {"confidence": 0.45, "acted_on": True},
        ],
        regime={"regime": "choppy", "confidence": 0.55},
        risk_event={"level": 3, "trigger": "dd_breach", "portfolio_heat": 0.8, "daily_dd": 0.07, "time": datetime(2026, 3, 8, tzinfo=timezone.utc)},
    )

    out = build_dashboard_insights(payload)

    insights = " ".join(out["operator_insights"])
    assert "PnL is non-positive" in insights
    assert "Validation pass-rate is below 60%" in insights
    assert "slippage is above 8 bps" in insights
    assert "critical" in insights
