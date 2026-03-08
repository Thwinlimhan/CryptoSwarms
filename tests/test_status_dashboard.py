from datetime import datetime, timedelta, timezone

from cryptoswarms.status_dashboard import build_agent_snapshots


def test_build_agent_snapshots_marks_stale_when_missing_or_old():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    heartbeats = {
        "market_scanner": now - timedelta(seconds=30),
        "risk_monitor": now - timedelta(seconds=301),
        "validation_pipeline": None,
    }
    counts = {"market_scanner": 6, "risk_monitor": 1}

    result = build_agent_snapshots(
        now=now,
        agents=["market_scanner", "risk_monitor", "validation_pipeline"],
        heartbeat_lookup=heartbeats,
        signal_counts=counts,
        stale_after_seconds=180,
    )

    assert result["market_scanner"]["status"] == "healthy"
    assert result["risk_monitor"]["status"] == "stale"
    assert result["validation_pipeline"]["status"] == "stale"
