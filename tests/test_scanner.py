from datetime import datetime, timezone

from cryptoswarms.scanner import MarketScannerCycleRunner


class FakeDataSource:
    def fetch_top_symbols(self, limit: int = 50) -> list[str]:
        return ["BTCUSDT", "ETHUSDT", "XRPUSDT"]

    def breakout_detected(self, symbol: str) -> bool:
        return symbol == "BTCUSDT"

    def funding_extreme(self, symbol: str) -> str | None:
        return "FUNDING_EXTREME_LONG" if symbol == "ETHUSDT" else None

    def smart_money_inflow(self, symbol: str) -> float:
        return 2_000_000.0 if symbol == "XRPUSDT" else 1000.0

    def classify_regime(self) -> str:
        return "TRENDING_UP"


class FakeSink:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    def publish(self, topic: str, payload: dict[str, object]) -> None:
        self.events.append((topic, payload))


class FakeStore:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}

    def set(self, key: str, value: str) -> None:
        self.data[key] = value

    def get(self, key: str) -> str | None:
        return self.data.get(key)


class FakeMemory:
    def __init__(self) -> None:
        self.records: list[tuple[str, bool]] = []

    def remember(self, text: str, important: bool = False) -> None:
        self.records.append((text, important))


def test_market_scanner_cycle_emits_multi_source_signals_and_heartbeat():
    sink = FakeSink()
    store = FakeStore()
    runner = MarketScannerCycleRunner(FakeDataSource(), sink, store)

    signals = runner.run_cycle(now=datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc))

    signal_types = [s["signal_type"] for s in signals]
    assert "BREAKOUT" in signal_types
    assert "FUNDING_EXTREME_LONG" in signal_types
    assert "SMART_MONEY" in signal_types
    assert "REGIME" in signal_types
    assert "heartbeat:market_scanner" in store.data
    assert len(sink.events) == len(signals)


def test_market_scanner_writes_memory_records():
    sink = FakeSink()
    store = FakeStore()
    memory = FakeMemory()
    runner = MarketScannerCycleRunner(FakeDataSource(), sink, store, memory_recorder=memory)

    signals = runner.run_cycle(now=datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc))

    assert len(memory.records) == len(signals)
    assert any("BREAKOUT" in text for text, _ in memory.records)
