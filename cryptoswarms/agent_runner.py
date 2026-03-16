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
import time
import traceback
from datetime import datetime, timezone
from typing import Any

from api.settings import settings
from cryptoswarms.adapters.binance_market_data import BinanceMarketData
from cryptoswarms.adapters.binance_ws_stream import BinanceWebSocketStream
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
from agents.execution.order_persistence import OrderPersistence, OrderStatus
from agents.execution.order_reconciler import OrderReconciler
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
        self.persistence = OrderPersistence(db=self._db)
        self.reconciler = OrderReconciler(persistence=self.persistence, exchange=self._execution)
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
        self.hl_breaker = self.breakers.get_or_create(
            "hyperliquid",
            failure_threshold=5
        )

        # ── WebSocket Market Data Stream ──────────────────
        self._ws_stream = BinanceWebSocketStream(
            on_price_update=self._on_ws_price_update,
            on_kline=self._on_ws_kline,
            on_trade=self._on_ws_trade,
        )

        # ── Portfolio Tracker Connection ──────────────────
        # Will be connected to the API's PortfolioTracker on start()
        self._portfolio_tracker: Any = None

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

        # Connect portfolio tracker to live components
        try:
            from api.routes.portfolio import portfolio_tracker
            portfolio_tracker.connect_position_manager(self.pm)
            portfolio_tracker.connect_order_persistence(self.persistence)
            try:
                from api.routes.websocket import manager as ws_mgr
                portfolio_tracker.connect_ws_manager(ws_mgr)
            except Exception:
                pass
            self._portfolio_tracker = portfolio_tracker
            logger.info("Portfolio tracker connected to PositionManager & OrderPersistence")
        except Exception as exc:
            logger.warning("Could not connect portfolio tracker: %s", exc)

        # Start WebSocket market data stream
        try:
            top_symbols = await self._market_data.fetch_top_symbols(limit=10)
            await self._ws_stream.start(symbols=top_symbols)
            logger.info("Binance WebSocket stream started for %d symbols", len(top_symbols))
        except Exception as exc:
            logger.warning("Binance WS stream failed to start, using REST fallback: %s", exc)

        # Start Reconciler
        await self.reconciler.start()

        self._running = True
        self._tasks = [
            asyncio.create_task(self._scanner_loop(), name="scanner"),
            asyncio.create_task(self._risk_loop(), name="risk"),
            asyncio.create_task(self._regime_loop(), name="regime"),
            asyncio.create_task(self._funding_loop(), name="funding"),
            asyncio.create_task(self._research_loop(), name="researcher"),
            asyncio.create_task(self._portfolio_broadcast_loop(), name="portfolio_broadcast"),
            asyncio.create_task(self._ws_market_data_loop(), name="ws_market_data"),
        ]
        logger.info("AgentRunner started — %d background tasks", len(self._tasks))

    async def stop(self) -> None:
        """Cancel all background tasks and clean up."""
        self._running = False
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

        await self.reconciler.stop()
        await self._ws_stream.stop()
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
                
                # 1. Deduplicate & Convert Signals
                refined_signals = []
                from cryptoswarms.signals.signal_decay import Signal as DecaySignal
                for signal_dict in signals:
                    # Check for duplicates (5 min TTL)
                    is_new = await self.deduplicator.process_signal(signal_dict)
                    if not is_new:
                        continue
                    
                    # Convert to Signal object for processing
                    sig_obj = DecaySignal(
                        signal_type=signal_dict.get("signal_type", "technical"),
                        confidence=signal_dict.get("confidence", 0.7),
                        direction=signal_dict.get("direction", "LONG"), # Scanner should provide this eventually
                        metadata=signal_dict
                    )
                    
                    # Apply decay model to confidence
                    decay_result = self.decay_model.calculate_decayed_confidence(sig_obj)
                    sig_obj.confidence = decay_result.decayed_confidence
                    refined_signals.append(sig_obj)

                # Resolve conflicts across signals
                resolution = self.conflict_resolver.resolve_conflicts(refined_signals)
                if resolution.winning_signal:
                    active_signals = [resolution.winning_signal]
                else:
                    active_signals = refined_signals

                for signal in active_signals:
                    symbol = signal.metadata.get("symbol")
                    if not symbol: continue
                    
                    context = {
                        "current_regime": self.regime.last_regime,
                        "smart_money": any(s.signal_type == "SMART_MONEY" for s in refined_signals if s.metadata.get("symbol") == symbol),
                        "funding": self.funding.last_funding.get(symbol, 0.0)
                    }
                    
                    for strat_id, strategy in self.strategies.items():
                        try:
                            # Convert back to dict for strategy evaluation, keeping updated confidence
                            signal_dict = signal.metadata.copy()
                            signal_dict["confidence"] = signal.confidence
                            
                            decision = await strategy.evaluate(signal_dict, context)
                            if decision:
                                trace_id = f"tr_{int(time.time()*1000)}"
                                self.tracer.trace_signal(trace_id, signal)
                                
                                logger.info(f"Strategic Decision from {strat_id} | Trace: {trace_id}: {decision}")
                                
                                # Broadcast strategic decision
                                from api.routes.websocket import manager
                                await manager.broadcast({
                                    "type": "strategic_decision",
                                    "data": decision,
                                    "trace_id": trace_id
                                })

                                # Log to DB & Trace
                                await self._db.write_signal(
                                    agent_name=f"strat:{strat_id}",
                                    signal_type=f"DECISION_{decision['action']}",
                                    symbol=symbol,
                                    confidence=decision["confidence"],
                                    metadata={**decision, "trace_id": trace_id}
                                )

                                # ── POSITION SIZING & RISK ──
                                # 1. Base sizing (Kelly)
                                ks = kelly_size(
                                    win_rate=0.5,
                                    avg_win_pct=0.04,
                                    avg_loss_pct=0.02,
                                    bankroll_usd=self.base_bankroll
                                )
                                base_size = ks.suggested_size_usd
                                
                                # 2. Volatility Adjustment
                                size_usd = self.vol_sizer.calculate_position_size(symbol, base_size)
                                
                                # 3. Pre-trade Risk Checks
                                # Check correlation with existing portfolio
                                open_pos_list = list(self.pm.open_positions.values())
                                if not self.correlation_risk.check_correlation_limits(symbol, open_pos_list):
                                    logger.warning(f"Correlation limit hit for {symbol}, skipping")
                                    continue
                                
                                # Check sector limits
                                if not self.sector_risk.check_sector_limits(symbol, size_usd):
                                    logger.warning(f"Sector limit hit for {symbol}, skipping")
                                    continue

                                # ── EXECUTION ────────────────────────────────
                                if decision.get("action") in ["BUY", "SELL", "LONG", "SHORT"] and size_usd > 0:
                                    price = price_map.get(symbol)
                                    if not price:
                                        # Try WS cache first, then REST
                                        ws_price = self._ws_stream.get_price(symbol)
                                        if ws_price:
                                            price = ws_price.get("close", 0)
                                        if not price:
                                            price = (await self._market_data.fetch_ticker(symbol))["price"]

                                    # Execution with Locking & Circuit Breaking
                                    _exec_order_id: str | None = None

                                    async def do_execute():
                                        nonlocal _exec_order_id
                                        # Open position in manager
                                        pos = self.pm.open_position(
                                            strategy_id=strat_id,
                                            symbol=symbol,
                                            side=decision["action"],
                                            entry_price=price,
                                            size_usd=size_usd,
                                            stop_loss_pct=strategy.config.stop_loss_pct,
                                            take_profit_pct=strategy.config.parameters.get("take_profit_pct", 0.04)
                                        )
                                        
                                        # Persist intent (via bridge method)
                                        _exec_order_id = await self.persistence.persist_from_position(
                                            pos, strategy_id=strat_id
                                        )

                                        # Mark as submitted
                                        await self.persistence.update_status(
                                            _exec_order_id, OrderStatus.SUBMITTED
                                        )
                                        
                                        # Submit via Circuit Breaker
                                        intent = OrderIntent(
                                            symbol=symbol,
                                            side=decision["action"],
                                            quantity=pos.size_tokens
                                        )
                                        
                                        result = await self.hl_breaker.call_exchange(
                                            lambda: self._execution.execute(intent)
                                        )

                                        # Capture exchange_order_id from Hyperliquid response
                                        oid = None
                                        if result and result.get("status") == "ok":
                                            try:
                                                data = result.get("response", {}).get("data", {})
                                                statuses = data.get("statuses", [])
                                                for s in statuses:
                                                    if "resting" in s:
                                                        oid = s["resting"].get("oid")
                                                    elif "filled" in s:
                                                        oid = s["filled"].get("oid")
                                            except Exception:
                                                pass

                                        # Mark as filled (or submitted if we didn't get oid yet)
                                        await self.persistence.update_status(
                                            _exec_order_id,
                                            OrderStatus.FILLED,
                                            exchange_order_id=str(oid) if oid else None,
                                            filled_quantity=pos.size_tokens,
                                            filled_price=price,
                                        )

                                        # Broadcast order event
                                        try:
                                            from api.routes.websocket import manager as ws_mgr
                                            await ws_mgr.broadcast_order_event("filled", {
                                                "client_order_id": _exec_order_id,
                                                "symbol": symbol,
                                                "side": decision["action"],
                                                "price": price,
                                                "size_usd": size_usd,
                                                "strategy_id": strat_id,
                                            })
                                        except Exception:
                                            pass

                                        return result

                                    try:
                                        # Trace Decision
                                        self.tracer.trace_decision(trace_id, decision)
                                        
                                        # Execute with symbol-level lock
                                        await self.coordinator.execute_with_lock(symbol, do_execute)
                                        
                                        # Trace Fill
                                        self.tracer.trace_fill(trace_id, {"status": "executed", "price": price})
                                        
                                    except Exception as exec_err:
                                        logger.error(f"Execution failed: {exec_err}")
                                        # Mark order as failed
                                        if _exec_order_id:
                                            await self.persistence.update_status(
                                                _exec_order_id,
                                                OrderStatus.FAILED,
                                                error_message=str(exec_err),
                                            )
                                            # Broadcast failure
                                            try:
                                                from api.routes.websocket import manager as ws_mgr
                                                await ws_mgr.broadcast_order_event("failed", {
                                                    "client_order_id": _exec_order_id,
                                                    "symbol": symbol,
                                                    "error": str(exec_err),
                                                })
                                            except Exception:
                                                pass
                                        self.alerts.send_alert("CRITICAL", f"Execution failed for {symbol}: {exec_err}")
                                        # Check if we should degrade
                                        self.degradation.enter_degraded_mode("execution_failure")
                                else:
                                    logger.warning(f"Skipping execution for {symbol}: zero size or invalid action")
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

    # ── WebSocket Market Data Callbacks ─────────────────────────────

    async def _on_ws_price_update(self, event: dict[str, Any]) -> None:
        """Called when mini-ticker batch arrives."""
        # Update scanner prices from WS cache
        hot = self._ws_stream.get_hot_assets(limit=5)
        if hot:
            self.scanner.last_prices = hot

    async def _on_ws_kline(self, kline: dict[str, Any]) -> None:
        """Called on each kline event — could trigger breakout detection."""
        pass  # Scanner already runs breakout detection in its cycle

    async def _on_ws_trade(self, trade: dict[str, Any]) -> None:
        """Called on whale trade detection (>$50k)."""
        symbol = trade.get("symbol", "")
        value = trade.get("value_usd", 0)
        logger.info("Whale trade detected: %s $%.0f", symbol, value)

    async def _ws_market_data_loop(self) -> None:
        """Periodically broadcast WS market data to frontend clients."""
        logger.info("WS market data broadcaster started (interval=5s)")
        while self._running:
            try:
                if self._ws_stream.is_connected:
                    hot_assets = self._ws_stream.get_hot_assets(limit=8)
                    if hot_assets:
                        from api.routes.websocket import manager
                        await manager.broadcast_market_data(hot_assets)

                        # Update tracked symbol list periodically
                        top = self._ws_stream.get_top_by_volume(limit=10)
                        if top:
                            symbols = [t["symbol"] for t in top]
                            self._ws_stream.update_symbols(symbols)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.debug("WS market data broadcast error: %s", traceback.format_exc())
            await asyncio.sleep(5)

    async def _portfolio_broadcast_loop(self) -> None:
        """Periodically broadcast portfolio updates to frontend via WebSocket."""
        logger.info("Portfolio broadcast loop started (interval=3s)")
        while self._running:
            try:
                from api.routes.websocket import manager
                from api.routes.portfolio import portfolio_tracker

                snapshot = portfolio_tracker.get_portfolio_snapshot()
                await manager.broadcast_portfolio_update(
                    total_pnl=snapshot["total_pnl_usd"],
                    positions=snapshot["open_positions"],
                    risk_metrics=snapshot["risk_metrics"],
                )
            except asyncio.CancelledError:
                break
            except Exception:
                logger.debug("Portfolio broadcast error: %s", traceback.format_exc())
            await asyncio.sleep(3)
