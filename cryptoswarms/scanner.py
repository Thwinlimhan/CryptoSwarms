from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

from memory.runtime_memory import MemoryRecorder, NullMemoryRecorder
from .storage import HeartbeatRecord, KeyValueStore, set_heartbeat


class SignalSink(Protocol):
    def publish(self, topic: str, payload: dict[str, object]) -> None: ...


class MarketDataSource(Protocol):
    def fetch_top_symbols(self, limit: int = 50) -> list[str]: ...

    def breakout_detected(self, symbol: str) -> bool: ...

    def funding_extreme(self, symbol: str) -> str | None: ...

    def smart_money_inflow(self, symbol: str) -> float: ...

    def classify_regime(self) -> str: ...


@dataclass(frozen=True)
class ScannerConfig:
    max_signals_per_cycle: int = 20
    min_confidence: float = 0.65
    smart_money_threshold_usd: float = 1_000_000.0


class MarketScannerCycleRunner:
    """Vertical-slice scanner runner with pluggable market data + sink adapters."""

    def __init__(
        self,
        data_source: MarketDataSource,
        sink: SignalSink,
        heartbeat_store: KeyValueStore,
        config: ScannerConfig = ScannerConfig(),
        memory_recorder: MemoryRecorder | None = None,
    ) -> None:
        self._data_source = data_source
        self._sink = sink
        self._heartbeat_store = heartbeat_store
        self._config = config
        self._memory = memory_recorder or NullMemoryRecorder()

    def run_cycle(self, now: datetime | None = None) -> list[dict[str, object]]:
        now = now or datetime.now(timezone.utc)
        set_heartbeat(self._heartbeat_store, HeartbeatRecord(component="market_scanner", timestamp=now))

        signals: list[dict[str, object]] = []

        for symbol in self._data_source.fetch_top_symbols(limit=50):
            if len(signals) >= self._config.max_signals_per_cycle:
                break

            if self._data_source.breakout_detected(symbol):
                signals.append(self._emit(symbol, "BREAKOUT", "HIGH", {"source": "scanner_breakout"}))

            if len(signals) >= self._config.max_signals_per_cycle:
                break

            funding_signal = self._data_source.funding_extreme(symbol)
            if funding_signal is not None:
                signals.append(self._emit(symbol, funding_signal, "MEDIUM", {"source": "scanner_funding"}))

            if len(signals) >= self._config.max_signals_per_cycle:
                break

            inflow = self._data_source.smart_money_inflow(symbol)
            if inflow >= self._config.smart_money_threshold_usd:
                signals.append(
                    self._emit(
                        symbol,
                        "SMART_MONEY",
                        "HIGH",
                        {"source": "scanner_smart_money", "inflow_usd": inflow},
                    )
                )

        if len(signals) < self._config.max_signals_per_cycle:
            regime = self._data_source.classify_regime()
            signals.append(
                self._emit(
                    "BTCUSDT",
                    "REGIME",
                    "HIGH",
                    {"source": "scanner_regime", "regime": regime},
                )
            )

        return signals

    def _emit(self, symbol: str, signal_type: str, priority: str, data: dict[str, object]) -> dict[str, object]:
        payload = {
            "signal_type": signal_type,
            "symbol": symbol,
            "confidence": max(self._config.min_confidence, 0.65),
            "priority": priority,
            "data": data,
            "suggested_hypothesis": f"{signal_type} candidate for {symbol}",
        }
        self._sink.publish("research:signals", payload)
        self._memory.remember(
            f"scanner signal={signal_type} symbol={symbol} priority={priority} confidence={payload['confidence']}",
            important=(priority == "HIGH"),
        )
        return payload
