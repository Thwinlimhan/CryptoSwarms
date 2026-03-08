from cryptoswarms.scheduler import MarketScannerScheduler, SchedulerConfig


class FakeRunner:
    def __init__(self, fail_first: bool = False) -> None:
        self.calls = 0
        self.fail_first = fail_first

    def run_cycle(self, now=None):
        self.calls += 1
        if self.fail_first and self.calls == 1:
            raise RuntimeError("temporary failure")
        return [{"signal_type": "BREAKOUT"}]


class FakeSleeper:
    def __init__(self) -> None:
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)


def test_scheduler_runs_cycles_and_sleeps_interval():
    runner = FakeRunner()
    sleeper = FakeSleeper()
    scheduler = MarketScannerScheduler(runner, sleeper, SchedulerConfig(cycle_seconds=15, retry_backoff_seconds=2))

    scheduler.run_forever(max_cycles=2)

    assert runner.calls == 2
    assert sleeper.sleeps == [15]


def test_scheduler_retries_with_backoff_after_failure():
    runner = FakeRunner(fail_first=True)
    sleeper = FakeSleeper()
    scheduler = MarketScannerScheduler(runner, sleeper, SchedulerConfig(cycle_seconds=15, retry_backoff_seconds=2))

    scheduler.run_forever(max_cycles=1)

    assert runner.calls == 2
    assert sleeper.sleeps[0] == 2
