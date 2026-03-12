from cryptoswarms.dashboard_insights import DashboardInsightInput, build_dashboard_insights


def test_build_dashboard_insights_computes_core_metrics():
    payload = DashboardInsightInput(
        trade_rows=[
            {"realised_pnl": 10.0, "slippage_bps": 2.0},
            {"realised_pnl": -5.0, "slippage_bps": 4.0},
            {"realised_pnl": 4.0, "slippage_bps": 3.0},
        ],
        validation_rows=[{"passed": True}, {"passed": False}, {"passed": True}],
        signal_rows=[{"confidence": 0.7, "acted_on": True}, {"confidence": 0.5, "acted_on": False}],
        attribution_rows=[{"hypothesis_id": "h1", "optimizer_run_id": "r1", "optimizer_candidate_id": "c1"}],
        regime={"regime": "trending_up", "confidence": 0.8},
        risk_event={"level": 1, "trigger": "none", "portfolio_heat": 0.3, "daily_dd": 0.02},
    )

    out = build_dashboard_insights(payload)

    assert out["trade_stats"]["trades"] == 3
    assert out["trade_stats"]["total_pnl_usd"] == 9.0
    assert out["validation_stats"]["pass_rate"] == 0.6667
    assert out["signal_stats"]["avg_confidence"] == 0.6
    assert out["regime"]["name"] == "trending_up"


def test_build_dashboard_insights_emits_actionable_warnings_for_weak_metrics():
    payload = DashboardInsightInput(
        trade_rows=[
            {"realised_pnl": -12.0, "slippage_bps": 10.5},
            {"realised_pnl": 2.0, "slippage_bps": 9.2},
            {"realised_pnl": -6.0, "slippage_bps": 11.1},
        ],
        validation_rows=[{"passed": False}, {"passed": True}, {"passed": False}],
        signal_rows=[{"confidence": 0.9, "acted_on": True}, {"confidence": 0.85, "acted_on": True}],
        attribution_rows=[{"hypothesis_id": "", "optimizer_run_id": "", "optimizer_candidate_id": ""}],
        regime={"regime": "chop", "confidence": 0.55},
        risk_event={"level": 3, "trigger": "drawdown", "portfolio_heat": 0.8, "daily_dd": 0.09},
    )

    out = build_dashboard_insights(payload)

    insights = " ".join(out["operator_insights"])
    assert "PnL is non-positive" in insights
    assert "Validation pass-rate is below 60%" in insights
    assert "slippage is above 8 bps" in insights
    assert "critical" in insights


def test_build_dashboard_insights_flags_missing_trade_data():
    payload = DashboardInsightInput(
        trade_rows=[],
        validation_rows=[],
        signal_rows=[],
        attribution_rows=[],
        regime={"regime": "unknown", "confidence": 0.0},
        risk_event=None,
    )

    out = build_dashboard_insights(payload)

    assert out["trade_stats"]["trades"] == 0
    assert out["regime"]["name"] == "unknown"
    assert out["operator_insights"] == [
        "No live trade data is available for the lookback window. Treat dashboard PnL and drawdown as unavailable."
    ]




