"""Risk monitor agent — evaluates portfolio risk and publishes heartbeats."""

from __future__ import annotations

import logging
from cryptoswarms.common.base_agent import BaseAgent
from cryptoswarms.common.stream_bus import StreamBus
from cryptoswarms.adapters.timescale_sink import TimescaleSink
from cryptoswarms.adapters.redis_heartbeat import RedisHeartbeat

logger = logging.getLogger("risk_agent")


class RiskAgent(BaseAgent):
    """Monitors portfolio risk and reports state changes."""
    
    INTERVAL = 30

    def __init__(self, *, db: TimescaleSink, heartbeat: RedisHeartbeat, stream_bus: StreamBus | None = None) -> None:
        super().__init__("risk_monitor", stream_bus)
        self.db = db
        self.heartbeat_adapter = heartbeat
        self._last_risk_level: int = -1  # sentinel — forces first write

    async def run_cycle(self) -> None:
        """Evaluate risk and write to DB if level changed."""
        await self.heartbeat_adapter.set_heartbeat(self.agent_id)
        self.heartbeat()

        # Use placeholder logic for now as in current AgentRunner
        current_level = 0  # placeholder — wire real risk eval here
        if current_level != self._last_risk_level:
            await self.db.write_risk_event(
                level=current_level,
                trigger="state_change",
                portfolio_heat=0.0,
                daily_dd=0.0,
            )
            self._last_risk_level = current_level
            logger.info("Risk level changed to %d", current_level)
