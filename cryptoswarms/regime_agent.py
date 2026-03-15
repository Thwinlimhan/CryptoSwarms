"""Regime classifier agent — classifies market regime from BTC data."""

from __future__ import annotations

import logging
from cryptoswarms.common.base_agent import BaseAgent
from cryptoswarms.common.stream_bus import StreamBus
from cryptoswarms.adapters.binance_market_data import BinanceMarketData
from cryptoswarms.adapters.timescale_sink import TimescaleSink
from cryptoswarms.adapters.redis_heartbeat import RedisHeartbeat

logger = logging.getLogger("regime_agent")

CONFIDENCE_MAP = {
    "volatility_expansion": 0.82,
    "volatility_crash": 0.90,
    "trending_up": 0.75,
    "trending_down": 0.75,
    "range_bound": 0.68,
    "unknown": 0.30,
}


class RegimeAgent(BaseAgent):
    """Classifies market regime periodically."""
    
    INTERVAL = 300

    def __init__(
        self,
        *,
        market_data: BinanceMarketData,
        db: TimescaleSink,
        heartbeat: RedisHeartbeat,
        stream_bus: StreamBus | None = None,
    ) -> None:
        super().__init__("regime_classifier", stream_bus)
        self.market_data = market_data
        self.db = db
        self.heartbeat_adapter = heartbeat
        self.last_regime: str = "unknown"

    async def run_cycle(self) -> str:
        """Classify and write market regime."""
        await self.heartbeat_adapter.set_heartbeat("validation_pipeline")
        self.heartbeat()

        regime = await self.market_data.classify_regime()
        self.last_regime = regime

        confidence = CONFIDENCE_MAP.get(regime, 0.5)

        await self.db.write_regime(
            regime=regime,
            confidence=confidence,
            indicators={"source": "btc_1h_vola_trend"},
        )
        logger.info("Regime classified: %s (confidence=%.2f)", regime, confidence)
        return regime
