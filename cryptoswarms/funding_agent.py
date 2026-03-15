"""Funding rate fetcher agent."""

from __future__ import annotations

import logging
from cryptoswarms.common.base_agent import BaseAgent
from cryptoswarms.common.stream_bus import StreamBus
from cryptoswarms.adapters.binance_market_data import BinanceMarketData

logger = logging.getLogger("funding_agent")


class FundingAgent(BaseAgent):
    """Fetches and caches perp funding rates."""
    
    INTERVAL = 600

    def __init__(self, *, market_data: BinanceMarketData, stream_bus: StreamBus | None = None) -> None:
        super().__init__("funding_fetcher", stream_bus)
        self.market_data = market_data
        self.last_funding: dict[str, float] = {}

    async def run_cycle(self) -> dict[str, float]:
        """Fetch and cache funding rates."""
        self.heartbeat()
        rates = await self.market_data.fetch_funding_rates()
        self.last_funding = rates
        logger.info("Fetched %d funding rates", len(rates))
        return rates
