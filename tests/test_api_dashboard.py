import asyncio
from datetime import datetime, timezone

import api.main as main
from cryptoswarms.dashboard_insights import DashboardInsightInput


def test_dashboard_insights_endpoint():
    async def fake_fetch(_: int) -> DashboardInsightInput:
        return DashboardInsightInput(
            trade_rows=[{"realised_pnl": 5.0, "slippage_bps": 2.0}],
            validation_rows=[{"passed": True}],
            signal_rows=[{"confidence": 0.7, "acted_on": True}],
            regime={"regime": "trending_up", "confidence": 0.8},
            risk_event={"level": 1, "trigger": "none", "portfolio_heat": 0.2, "daily_dd": 0.01, "time": datetime(2026, 3, 8, tzinfo=timezone.utc)},
        )

    original = main._fetch_dashboard_insight_inputs
    main._fetch_dashboard_insight_inputs = fake_fetch
    try:
        payload = asyncio.run(main.dashboard_insights(lookback_hours=24))
    finally:
        main._fetch_dashboard_insight_inputs = original

    assert payload["trade_stats"]["total_pnl_usd"] == 5.0
    assert payload["regime"]["name"] == "trending_up"


def test_dashboard_page_renders_html():
    html = asyncio.run(main.dashboard_page())
    assert "CryptoSwarms Operator Deck" in html
