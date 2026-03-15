"""Background agent runner — the heart of CryptoSwarms.

Launches async background tasks that delegate to specialized agents:
  - ScannerAgent: scans Binance for breakouts, funding extremes, whale activity
  - RiskAgent: evaluates portfolio risk and publishes heartbeats
  - RegimeAgent: classifies market regime from BTC data
  - FundingAgent: fetches perpetual funding rates

All data is written to TimescaleDB (signals, regimes, risk_events)
and Redis (heartbeats) so the dashboard shows real, live data.
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from datetime import datetime
from typing import Any

from api.settings import settings
from cryptoswarms.adapters.binance_market_data import BinanceMarketData
from cryptoswarms.adapters.timescale_sink import TimescaleSink
from cryptoswarms.adapters.redis_heartbeat import RedisHeartbeat
from cryptoswarms.adapters.hyperliquid_adapter import HyperliquidAdapter

from cryptoswarms.scanner_agent import ScannerAgent, ScannerConfig
from cryptoswarms.risk_agent import RiskAgent
from cryptoswarms.regime_agent import RegimeAgent
from cryptoswarms.funding_agent import FundingAgent
from cryptoswarms.research_agent import ResearchAgent
from cryptoswarms.memory_dag import MemoryDag
from cryptoswarms.adapters.llm import LLMClient
from cryptoswarms.pipeline.strategy_loader import StrategyLoader
from cryptoswarms.execution_router import ExecutionRouter, OrderIntent
from cryptoswarms.position_manager import PositionManager, ExitReason
from cryptoswarms.kelly_sizer import kelly_size

# Reliability & Risk Components
from cryptoswarms.adapters.rate_limiter import ExchangeRateLimiter
from cryptoswarms.adapters.exchange_errors import ExchangeErrorHandler
from agents.orchestration.signal_deduplicator import SignalDeduplicator
from agents.execution.execution_coordinator import ExecutionCoordinator
from agents.execution.order_persistence import OrderPersistence
from cryptoswarms.resilience.circuit_breaker import CircuitBreakerRegistry, ExchangeCircuitBreaker
from cryptoswarms.resilience.degradation_manager import DegradationManager
from cryptoswarms.alerting.alert_manager import AlertManager
from cryptoswarms.monitoring.agent_metrics import get_agent_metrics
from cryptoswarms.risk.correlation_manager import CorrelationRiskManager
from cryptoswarms.risk.sector_limits import SectorRiskManager
from cryptoswarms.risk.volatility_sizer import VolatilityAdjustedSizer
from cryptoswarms.signals.conflict_resolver import SignalConflictResolver
from cryptoswarms.signals.ensemble_weighter import SignalEnsemble
from cryptoswarms.signals.signal_decay import SignalDecayModel
from cryptoswarms.tracing.execution_tracer import ExecutionTracer
from cryptoswarms.tracing.trace_logger import get_trace_logger

logger = logging.getLogger("agent_runner")


class AgentRunner:
    """Manages background agent loops — delegates to specialized agents."""

    def __init__(
        self,
        *,
        timescale_dsn: str,
        redis_url: str,
    ) -> None:
        self._market_data = BinanceMarketData()
        self._db = TimescaleSink(timescale_dsn)
        self._heartbeat = RedisHeartbeat(redis_url)
        self._execution = HyperliquidAdapter()
        
        # Initialize specialized agents with settings-driven config
        scanner_config = ScannerConfig(
            breakout_confidence=settings.scanner_breakout_confidence,
            funding_confidence=settings.scanner_funding_confidence,
            smart_money_confidence=settings.scanner_smart_money_confidence,
            cooldown_cycles=settings.scanner_cooldown_cycles
        )
        
        self.scanner = ScannerAgent(
            market_data=self._market_data,
            db=self._db,
            heartbeat=self._heartbeat,
            config=scanner_config
        )
        self.risk = RiskAgent(db=self._db, heartbeat=self._heartbeat)
        self.regime = RegimeAgent(
            market_data=self._market_data,
            db=self._db,
            heartbeat=self._heartbeat
        )
        self.funding = FundingAgent(market_data=self._market_data)
        
        # New: Research Memory & LLM
        self.dag = MemoryDag()
        self.llm = LLMClient()
        self.researcher = ResearchAgent(
            db=self._db, 
            heartbeat=self._heartbeat,
            dag=self.dag,
            llm=self.llm
        )

        # Portfolio Management
        self.pm = PositionManager()
        self.base_bankroll = 10000.0 # Virtual bankroll for paper trading

        # Load strategies
        self.strategy_loader = StrategyLoader()
        self.strategies = self.strategy_loader.load_all()

        # ── Reliability & Risk Orchestration ──────────────
        self.rate_limiter = ExchangeRateLimiter()
        self.error_handler = ExchangeErrorHandler()
        self.deduplicator = SignalDeduplicator()
        self.coordinator = ExecutionCoordinator()
        self.persistence = OrderPersistence()
        self.breakers = CircuitBreakerRegistry()
        self.degradation = DegradationManager()
        self.alerts = AlertManager()
        self.metrics = get_agent_metrics()
        self.tracer = ExecutionTracer()
        self.logger = get_trace_logger()
        
        # Risk Managers
        self.correlation_risk = CorrelationRiskManager()
        self.sector_risk = SectorRiskManager()
        self.vol_sizer = VolatilityAdjustedSizer()
        
        # Signal Refinement
        self.conflict_resolver = SignalConflictResolver()
        self.ensemble = SignalEnsemble()
        self.decay_model = SignalDecayModel()

        # Circuit Breaker for Hyperliquid
        self.hl_breaker = self.breakers.get_breaker(
            "hyperliquid",
            ExchangeCircuitBreaker(name="hyperliquid", failure_threshold=5)
        )

        self._tasks: list[asyncio.Task] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    # Delegate properties for API compatibility
    @property
    def scan_count(self) -> int:
        return self.scanner.scan_count

    @property
    def last_signals(self) -> list[dict[str, Any]]:
        return self.scanner.last_signals

    @property
    def signal_history(self) -> list[dict[str, Any]]:
        return list(self.scanner.signal_history)

    @property
    def last_regime(self) -> str:
        return self.regime.last_regime

    @property
    def last_funding(self) -> dict[str, float]:
        return self.funding.last_funding

    @property
    def last_prices(self) -> list[dict[str, Any]]:
        return self.scanner.last_prices

    async def start(self) -> None:
        """Connect dependencies and spawn background loops."""
        if self._running:
            logger.warning("AgentRunner already running")
            return

        logger.info("Starting AgentRunner...")
        await self._db.connect()
        await self._heartbeat.connect()

        self._running = True
        self._tasks = [
            asyncio.create_task(self._scanner_loop(), name="scanner"),
            asyncio.create_task(self._risk_loop(), name="risk"),
            asyncio.create_task(self._regime_loop(), name="regime"),
            asyncio.create_task(self._funding_loop(), name="funding"),
            asyncio.create_task(self._research_loop(), name="researcher"),
        ]
        logger.info("AgentRunner started — %d background tasks", len(self._tasks))

    async def stop(self) -> None:
        """Cancel all background tasks and clean up."""
        self._running = False
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        await self._market_data.close()
        await self._db.close()
        await self._heartbeat.close()
        await self._execution.close()
        self.researcher.heartbeat(status="stopped")
        logger.info("AgentRunner stopped")

    async def _scanner_loop(self) -> None:
        """Continuously scan markets via ScannerAgent."""
        logger.info("Scanner loop started (interval=%ds)", self.scanner.config.interval_seconds)
        while self._running:
            try:
                signals = await self.scanner.run_cycle()
                
                # Broadcast signals to connected WebSocket clients
                try:
                    from api.routes.websocket import manager
                    await manager.broadcast({
                        "type": "signals",
                        "data": signals,
                        "scan_count": self.scanner.scan_count,
                        "hot_assets": self.scanner.last_prices
                    })
                except Exception as e:
                    logger.error(f"Failed to broadcast WS message: {e}")

                # ── EXIT EVALUATION ──────────────────────────────
                # Check for stop-losses, take-profits, etc.
                if self.scanner.last_prices:
                    # Convert list of dicts [{"symbol": "BTC...", "price": 123...}] to dict {symbol: price}
                    price_map = {p["symbol"]: p["price"] for p in self.scanner.last_prices}
                    closed_trades = self.pm.check_exits(price_map)
                    for trade in closed_trades:
                        logger.info(f"TRADE CLOSED: {trade.symbol} | PnL: ${trade.pnl_usd} | Reason: {trade.exit_reason}")
                        # Broadcast exit
                        from api.routes.websocket import manager
                        await manager.broadcast({
                            "type": "trade_closed",
                            "data": trade.__dict__
                        })
                        
                        # Update DB with realized PnL
                        await self._db.resolve_decision(
                            decision_id=trade.position_id,
                            status="won" if trade.pnl_usd > 0 else "lost",
                            pnl=trade.pnl_usd,
                            notes=f"Exit reason: {trade.exit_reason}"
                        )

                # ── STRATEGY EVALUATION ──────────────────────────
                # Process signals through loaded strategies
                price_map = {p["symbol"]: p["price"] for p in self.scanner.last_prices} if self.scanner.last_prices else {}
                
                for signal in signals:
                    context = {
                        "current_regime": self.regime.last_regime,
                        "smart_money": any(s["signal_type"] == "SMART_MONEY" for s in signals if s["symbol"] == signal["symbol"]),
                        "funding": self.funding.last_funding.get(signal["symbol"], 0.0)
                    }
                    
                    for strat_id, strategy in self.strategies.items():
                        try:
                            decision = await strategy.evaluate(signal, context)
                            if decision:
                                logger.info(f"Strategic Decision from {strat_id}: {decision}")
                                
                                # Broadcast strategic decision
                                from api.routes.websocket import manager
                                await manager.broadcast({
                                    "type": "strategic_decision",
                                    "data": decision
                                })

                                # Log to DB
                                await self._db.write_signal(
                                    agent_name=f"strat:{strat_id}",
                                    signal_type=f"DECISION_{decision['action']}",
                                    symbol=decision["symbol"],
                                    confidence=decision["confidence"],
                                    metadata=decision
                                )

                                # ── POSITION SIZING (KELLY) ──
                                ks = kelly_size(
                                    win_rate=0.5, # Default starting point
                                    avg_win_pct=0.04,
                                    avg_loss_pct=0.02,
                                    bankroll_usd=self.base_bankroll
                                )
                                size_usd = ks.suggested_size_usd
                                
                                # ── EXECUTION ────────────────────────────────
                                if decision.get("action") in ["BUY", "SELL", "LONG", "SHORT"] and size_usd > 0:
                                    # Open position in manager
                                    symbol = decision["symbol"]
                                    price = price_map.get(symbol)
                                    if not price:
                                        logger.warning(f"No price for {symbol}, fetching now...")
                                        price = (await self._market_data.fetch_ticker(symbol))["price"]

                                    pos = self.pm.open_position(
                                        strategy_id=strat_id,
                                        symbol=symbol,
                                        side=decision["action"],
                                        entry_price=price,
                                        size_usd=size_usd,
                                        stop_loss_pct=strategy.config.stop_loss_pct,
                                        take_profit_pct=strategy.config.parameters.get("take_profit_pct", 0.04),
                                        trailing_stop_pct=strategy.config.parameters.get("trailing_stop_pct", 0.0)
                                    )
                                    # Persist to decisions table so failure ledger can resolve on close
                                    await self._db.write_decision({
                                        "id": pos.position_id,
                                        "label": decision.get("action", "open"),
                                        "strategy_id": strat_id,
                                        "symbol": symbol,
                                        "ev_estimate": float(decision.get("ev") or decision.get("expected_value") or 0.0),
                                        "win_probability": float(decision.get("confidence", 0.5)),
                                        "position_size_usd": size_usd,
                                        "bias_flags": [],
                                        "status": "pending",
                                    })

                                    logger.info(f"Executing {decision['action']} for {symbol} with size ${size_usd}")
                                    intent = OrderIntent(
                                        symbol=symbol,
                                        side=decision["action"],
                                        quantity=pos.size_tokens
                                    )
                                    # Send to Hyperliquid
                                    await self._execution.execute(intent)
                                else:
                                    logger.warning(f"Skipping execution for {decision['symbol']}: zero size or invalid action")
                        except Exception as e:
                            logger.error(f"Strategy {strat_id} evaluation error: {e}")
                    
            except asyncio.CancelledError:
                break
            except Exception:
                import traceback
                logger.error("Scanner cycle error:\n%s", traceback.format_exc())
            await asyncio.sleep(self.scanner.config.interval_seconds)

    async def _risk_loop(self) -> None:
        """Evaluate risk via RiskAgent."""
        logger.info("Risk monitor loop started (interval=%ds)", self.risk.INTERVAL)
        while self._running:
            try:
                await self.risk.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Risk loop error:\n%s", traceback.format_exc())
            await asyncio.sleep(self.risk.INTERVAL)

    async def _regime_loop(self) -> None:
        """Classify regime via RegimeAgent."""
        logger.info("Regime classifier started (interval=%ds)", self.regime.INTERVAL)
        while self._running:
            try:
                await self.regime.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Regime loop error:\n%s", traceback.format_exc())
            await asyncio.sleep(self.regime.INTERVAL)

    async def _funding_loop(self) -> None:
        """Fetch funding via FundingAgent."""
        logger.info("Funding rate fetcher started (interval=%ds)", self.funding.INTERVAL)
        while self._running:
            try:
                await self.funding.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Funding loop error:\n%s", traceback.format_exc())
            await asyncio.sleep(self.funding.INTERVAL)

    async def _research_loop(self) -> None:
        """Autoresearch loop following Karpathy pattern."""
        logger.info("Research loop started (interval=300s)")
        while self._running:
            try:
                await self.researcher.run_cycle()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.error("Research loop error:\n%s", traceback.format_exc())
            await asyncio.sleep(300) # Check for window every 5 mins
