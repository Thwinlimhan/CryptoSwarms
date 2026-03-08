from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class MacroEvent:
    name: str
    at: datetime


def in_macro_blackout(now: datetime, events: tuple[MacroEvent, ...], window_minutes: int = 30) -> tuple[bool, str | None]:
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc)

    window = timedelta(minutes=window_minutes)
    for event in events:
        event_time = event.at
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        event_time = event_time.astimezone(timezone.utc)

        if abs(now - event_time) <= window:
            return True, event.name

    return False, None
