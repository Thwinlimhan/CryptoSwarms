"""Market scanner agent — scans Binance for breakouts, funding extremes, whale activity."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cryptoswarms.common.base_agent import BaseAgent
from cryptoswarms.common.stream_bus import StreamBus
from cryptoswarms.adapters.binance_market_data import BinanceMarketData
from cryptoswarms.adapters.timescale_sink import TimescaleSink
from cryptoswarms.adapters.redis_heartbeat import RedisHeartbeat

logger = logging.getLogger("scanner_agent")


@dataclass
class ScannerConfig:
    """Externalized scanner configuration."""
    interval_seconds: int = 60
    max_symbols: int = 15
    hot_symbols_count: int = 5
    max_signals_per_cycle: int = 10
    cooldown_cycles: int = 5
    breakout_confidence: float = 0.78
    funding_confidence: float = 0.72
    smart_money_confidence: float = 0.70
    smart_money_inflow_threshold: float = 500_000


class ScannerAgent(BaseAgent):
    """Scans markets for trading signals with dedup and cooldown."""

    def __init__(
        self,
        *,
        market_data: BinanceMarketData,
        db: TimescaleSink,
        heartbeat: RedisHeartbeat,
        stream_bus: StreamBus | None = None,
        config: ScannerConfig | None = None,
    ) -> None:
        super().__init__("market_scanner", stream_bus)
        self.market_data = market_data
        self.db = db
        self.heartbeat_adapter = heartbeat
        self.config = config or ScannerConfig()

        self.scan_count = 0
        self.last_signals: list[dict[str, Any]] = []
        # Rolling history of the last 200 signals across all cycles
        self.signal_history: deque[dict[str, Any]] = deque(maxlen=200)
        self.last_prices: list[dict[str, Any]] = []
        # Cooldown tracker: (symbol, signal_type) -> cycles remaining
        self._cooldowns: dict[tuple[str, str], int] = {}

    def _tick_cooldowns(self) -> None:
        """Decrement all cooldown counters by 1 each cycle; remove expired entries."""
        expired = [k for k, v in self._cooldowns.items() if v <= 1]
        for k in expired:
            del self._cooldowns[k]
        for k in self._cooldowns:
            self._cooldowns[k] -= 1

    def is_on_cooldown(self, symbol: str, signal_type: str) -> bool:
        return self._cooldowns.get((symbol, signal_type), 0) > 0

    def set_cooldown(self, symbol: str, signal_type: str) -> None:
        self._cooldowns[(symbol, signal_type)] = self.config.cooldown_cycles

    async def run_cycle(self) -> list[dict[str, Any]]:
        """Execute one scan cycle. Returns signals found."""
        self.scan_count += 1
        logger.info("=== Scanner cycle #%d ===", self.scan_count)

        # Tick down dedup cooldowns each cycle
        self._tick_cooldowns()

        # Set heartbeat (both via adapter and modern StreamBus)
        await self.heartbeat_adapter.set_heartbeat(self.agent_id)
        self.heartbeat()

        # Fetch top symbols
        symbols = await self.market_data.fetch_top_symbols(limit=20)
        if not symbols:
            logger.warning("No symbols fetched, skipping cycle")
            return []

        # Fetch prices for hot assets display
        hot_symbols = symbols[:self.config.hot_symbols_count]
        self.last_prices = await self.market_data.fetch_prices(hot_symbols)

        signals: list[dict[str, Any]] = []
        scanned = 0

        for symbol in symbols[:self.config.max_symbols]:
            scanned += 1

            # ── Breakout detection ────────────────────────────────
            if not self.is_on_cooldown(symbol, "BREAKOUT"):
                is_breakout = await self.market_data.breakout_detected(symbol)
                if is_breakout:
                    sig = {
                        "signal_type": "BREAKOUT",
                        "symbol": symbol,
                        "confidence": self.config.breakout_confidence,
                        "priority": "HIGH",
                        "source": "binance_scanner",
                    }
                    signals.append(sig)
                    self.set_cooldown(symbol, "BREAKOUT")
                    await self.db.write_signal(
                        agent_name="market_scanner",
                        signal_type="BREAKOUT",
                        symbol=symbol,
                        confidence=self.config.breakout_confidence,
                        metadata={"source": "binance_bollinger_breakout"},
                    )

            # ── Funding extreme ───────────────────────────────────
            funding_signal = await self.market_data.funding_extreme(symbol)
            if funding_signal and not self.is_on_cooldown(symbol, funding_signal):
                sig = {
                    "signal_type": funding_signal,
                    "symbol": symbol,
                    "confidence": self.config.funding_confidence,
                    "priority": "MEDIUM",
                    "source": "binance_funding",
                }
                signals.append(sig)
                self.set_cooldown(symbol, funding_signal)
                await self.db.write_signal(
                    agent_name="market_scanner",
                    signal_type=funding_signal,
                    symbol=symbol,
                    confidence=self.config.funding_confidence,
                    metadata={"source": "binance_funding_rate"},
                )

            # ── Smart money (top 5 by volume only) ───────────────
            if scanned <= 5 and not self.is_on_cooldown(symbol, "SMART_MONEY"):
                inflow = await self.market_data.smart_money_inflow(symbol)
                if inflow >= self.config.smart_money_inflow_threshold:
                    sig = {
                        "signal_type": "SMART_MONEY",
                        "symbol": symbol,
                        "confidence": self.config.smart_money_confidence,
                        "priority": "HIGH",
                        "source": "binance_trades",
                        "inflow_usd": inflow,
                    }
                    signals.append(sig)
                    self.set_cooldown(symbol, "SMART_MONEY")
                    await self.db.write_signal(
                        agent_name="market_scanner",
                        signal_type="SMART_MONEY",
                        symbol=symbol,
                        confidence=self.config.smart_money_confidence,
                        metadata={"source": "binance_large_trades", "inflow_usd": inflow},
                    )

            if len(signals) >= self.config.max_signals_per_cycle:
                break

        self.last_signals = signals
        self.signal_history.extend(signals)
        logger.info(
            "Scanner cycle #%d complete: %d symbols scanned, %d signals found",
            self.scan_count, scanned, len(signals),
        )
        return signals
