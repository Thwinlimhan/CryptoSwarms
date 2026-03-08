from datetime import datetime, timedelta, timezone

from cryptoswarms.status import AgentHeartbeat, build_agent_status, is_heartbeat_fresh


def test_heartbeat_fresh():
    heartbeat = datetime.now(timezone.utc) - timedelta(seconds=30)
    assert is_heartbeat_fresh(heartbeat, ttl_seconds=120) is True


def test_heartbeat_stale_when_missing():
    assert is_heartbeat_fresh(None) is False


def test_build_agent_status_payload():
    now = datetime.now(timezone.utc)
    payload = build_agent_status(
        [
            AgentHeartbeat(name="scanner", last_heartbeat=now, signals_today=12),
            AgentHeartbeat(name="alpha", last_heartbeat=now - timedelta(minutes=10), signals_today=3),
        ],
        ttl_seconds=60,
    )

    assert payload["scanner"]["status"] == "healthy"
    assert payload["alpha"]["status"] == "stale"
    assert payload["scanner"]["signals_today"] == 12
