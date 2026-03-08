from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptoswarms.scanner import MarketScannerCycleRunner, ScannerConfig


@dataclass
class InMemoryKeyValueStore:
    values: dict[str, str]

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)


@dataclass
class ListSignalSink:
    messages: list[dict[str, object]]

    def publish(self, topic: str, payload: dict[str, object]) -> None:
        self.messages.append({"topic": topic, "payload": payload})


class StaticMarketDataSource:
    def fetch_top_symbols(self, limit: int = 50) -> list[str]:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def breakout_detected(self, symbol: str) -> bool:
        return symbol == "BTCUSDT"

    def funding_extreme(self, symbol: str) -> str | None:
        if symbol == "ETHUSDT":
            return "FUNDING_LONG_SQUEEZE"
        return None

    def smart_money_inflow(self, symbol: str) -> float:
        if symbol == "SOLUSDT":
            return 1_500_000.0
        return 0.0

    def classify_regime(self) -> str:
        return "trending_up"


def main() -> None:
    sink = ListSignalSink(messages=[])
    store = InMemoryKeyValueStore(values={})
    runner = MarketScannerCycleRunner(
        data_source=StaticMarketDataSource(),
        sink=sink,
        heartbeat_store=store,
        config=ScannerConfig(max_signals_per_cycle=5, min_confidence=0.65),
    )
    signals = runner.run_cycle(now=datetime.now(timezone.utc))

    out_dir = Path("docs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "phase1_smoke_output.json"
    out_file.write_text(json.dumps({"signals": signals, "published": sink.messages}, indent=2), encoding="utf-8")

    print(f"Signals emitted: {len(signals)}")
    print(f"Output written: {out_file}")


if __name__ == "__main__":
    main()
