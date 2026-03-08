from datetime import datetime, timedelta, timezone

from cryptoswarms.deadman import (
    DeadMansSwitchConfig,
    DeadMansSwitchState,
    evaluate_dead_mans_switch,
)


def test_halts_when_heartbeat_missing():
    now = datetime.now(timezone.utc)
    state = evaluate_dead_mans_switch(
        now=now,
        last_risk_heartbeat=None,
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
    )
    assert state.halted is True


def test_halts_when_heartbeat_stale():
    now = datetime.now(timezone.utc)
    state = evaluate_dead_mans_switch(
        now=now,
        last_risk_heartbeat=now - timedelta(seconds=300),
        current_halt_state=DeadMansSwitchState(halted=False, reason="init"),
        config=DeadMansSwitchConfig(max_heartbeat_age_seconds=90),
    )
    assert state.halted is True
    assert "stale" in state.reason.lower()


def test_recovers_after_cooling_period():
    now = datetime.now(timezone.utc)
    halt_since = now - timedelta(seconds=600)
    state = evaluate_dead_mans_switch(
        now=now,
        last_risk_heartbeat=now - timedelta(seconds=10),
        current_halt_state=DeadMansSwitchState(halted=True, reason="stale", halt_since=halt_since),
        config=DeadMansSwitchConfig(max_heartbeat_age_seconds=90, cooling_period_seconds=300),
    )
    assert state.halted is False
    assert "complete" in state.reason.lower()


def test_stays_halted_during_cooling_period():
    now = datetime.now(timezone.utc)
    halt_since = now - timedelta(seconds=120)
    state = evaluate_dead_mans_switch(
        now=now,
        last_risk_heartbeat=now - timedelta(seconds=5),
        current_halt_state=DeadMansSwitchState(halted=True, reason="stale", halt_since=halt_since),
        config=DeadMansSwitchConfig(max_heartbeat_age_seconds=90, cooling_period_seconds=300),
    )
    assert state.halted is True
    assert "cooling period" in state.reason.lower()
