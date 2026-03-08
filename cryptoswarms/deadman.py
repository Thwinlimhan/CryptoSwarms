from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class DeadMansSwitchConfig:
    max_heartbeat_age_seconds: int = 90
    cooling_period_seconds: int = 300


@dataclass(frozen=True)
class DeadMansSwitchState:
    halted: bool
    reason: str
    halt_since: datetime | None = None


def _normalize_utc(ts: datetime | None) -> datetime | None:
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def evaluate_dead_mans_switch(
    *,
    now: datetime,
    last_risk_heartbeat: datetime | None,
    current_halt_state: DeadMansSwitchState,
    config: DeadMansSwitchConfig = DeadMansSwitchConfig(),
) -> DeadMansSwitchState:
    """Halt trading when risk-monitor heartbeat goes stale.

    Release behavior mirrors the v6 plan: require stable conditions for a cooling period.
    """

    now_utc = _normalize_utc(now)
    heartbeat_utc = _normalize_utc(last_risk_heartbeat)

    if heartbeat_utc is None:
        return DeadMansSwitchState(
            halted=True,
            reason="No risk heartbeat available.",
            halt_since=current_halt_state.halt_since or now_utc,
        )

    heartbeat_age = now_utc - heartbeat_utc
    stale = heartbeat_age > timedelta(seconds=config.max_heartbeat_age_seconds)

    if stale:
        return DeadMansSwitchState(
            halted=True,
            reason=f"Risk heartbeat stale ({int(heartbeat_age.total_seconds())}s old).",
            halt_since=current_halt_state.halt_since or now_utc,
        )

    if not current_halt_state.halted:
        return DeadMansSwitchState(halted=False, reason="Healthy.")

    # We are halted but heartbeat is fresh again. Enforce cooling window.
    halt_since = _normalize_utc(current_halt_state.halt_since) or now_utc
    halted_for = now_utc - halt_since
    if halted_for < timedelta(seconds=config.cooling_period_seconds):
        return DeadMansSwitchState(
            halted=True,
            reason=(
                "Heartbeat recovered; cooling period active "
                f"({int(halted_for.total_seconds())}/{config.cooling_period_seconds}s)."
            ),
            halt_since=halt_since,
        )

    return DeadMansSwitchState(halted=False, reason="Heartbeat recovered; cooling period complete.")
