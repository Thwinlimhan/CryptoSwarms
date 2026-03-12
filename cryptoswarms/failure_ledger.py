from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class OutcomeRecord:
    key: str
    passed: bool
    timestamp: datetime
    note: str = ""


class FailureLedger:
    def __init__(self) -> None:
        self._records: list[OutcomeRecord] = []

    def record(self, *, key: str, passed: bool, note: str = "", timestamp: datetime | None = None) -> None:
        ts = timestamp or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        self._records.append(OutcomeRecord(key=key, passed=bool(passed), timestamp=ts, note=note))

    def failure_rate(self, *, key: str, lookback_days: int = 90) -> float:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, int(lookback_days)))
        rows = [r for r in self._records if r.key == key and r.timestamp >= cutoff]
        if not rows:
            return 0.0
        failures = sum(1 for r in rows if not r.passed)
        return failures / float(len(rows))

    def should_deprioritize(self, *, key: str, lookback_days: int = 90, threshold: float = 0.6) -> bool:
        return self.failure_rate(key=key, lookback_days=lookback_days) >= float(threshold)
