from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class ScannerRunner(Protocol):
    def run_cycle(self, now: datetime | None = None) -> list[dict[str, object]]: ...


class Sleeper(Protocol):
    def sleep(self, seconds: float) -> None: ...


@dataclass(frozen=True)
class SchedulerConfig:
    cycle_seconds: int = 900
    retry_backoff_seconds: int = 30


class MarketScannerScheduler:
    """Simple scheduler wrapper with retry/backoff semantics."""

    def __init__(self, runner: ScannerRunner, sleeper: Sleeper, config: SchedulerConfig = SchedulerConfig()) -> None:
        self._runner = runner
        self._sleeper = sleeper
        self._config = config

    def run_once(self, now: datetime | None = None) -> list[dict[str, object]]:
        return self._runner.run_cycle(now=now or datetime.now(timezone.utc))

    def run_forever(self, max_cycles: int | None = None) -> None:
        completed = 0
        while True:
            try:
                self.run_once()
                completed += 1
                if max_cycles is not None and completed >= max_cycles:
                    return
                self._sleeper.sleep(self._config.cycle_seconds)
            except Exception:
                self._sleeper.sleep(self._config.retry_backoff_seconds)
