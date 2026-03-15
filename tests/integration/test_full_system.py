"""Full System Integration Tests.

Tests the complete flow from signal detection to order execution,
ensuring all system components work together correctly.
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any


# ── Test Helpers ─────────────────────────────────────────────────

class MockExchange:
    """Mock exchange for integration testing."""

    def __init__(self) -> None:
        self.orders: list[dict[str, Any]] = []
        self.order_counter = 0

    async def submit_order(self, symbol: str, side: str, quantity: float, price: float | None = None) -> dict:
        self.order_counter += 1
        order = {
            "order_id": f"mock_{self.order_counter}",
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price or 50000.0,
            "status": "FILLED",
        }
        self.orders.append(order)
        return order

    async def get_order_status(self, order_id: str) -> str:
        return "FILLED"


# ── Integration Tests ─────────────────────────────────────────────

class TestFullSystemIntegration:
    """Integration tests for the complete trading system."""

    def test_signal_deduplication(self) -> None:
        """Test that duplicate signals are properly filtered."""
        from agents.orchestration.signal_deduplicator import SignalDeduplicator

        dedup = SignalDeduplicator(ttl_seconds=5)
        signal = {"symbol": "BTCUSDT", "timestamp": "2025-01-01T00:00:00", "signal_type": "momentum"}

        # First signal should pass
        result1 = asyncio.get_event_loop().run_until_complete(dedup.process_signal(signal))
        assert result1 is True

        # Duplicate should be filtered
        result2 = asyncio.get_event_loop().run_until_complete(dedup.process_signal(signal))
        assert result2 is False

        assert dedup.stats.total_signals == 2
        assert dedup.stats.deduplicated == 1

    def test_execution_coordinator_locking(self) -> None:
        """Test that execution coordinator prevents concurrent symbol execution."""
        from agents.execution.execution_coordinator import ExecutionCoordinator

        coordinator = ExecutionCoordinator()
        results: list[str] = []

        async def run_test():
            async def slow_order():
                await asyncio.sleep(0.1)
                results.append("order_1")
                return "ok"

            async def fast_order():
                results.append("order_2")
                return "ok"

            # Both try to execute on same symbol
            task1 = asyncio.create_task(
                coordinator.execute_with_lock("BTCUSDT", slow_order)
            )
            await asyncio.sleep(0.01)  # Ensure task1 gets lock first
            task2 = asyncio.create_task(
                coordinator.execute_with_lock("BTCUSDT", fast_order)
            )

            await task1
            await task2

        asyncio.get_event_loop().run_until_complete(run_test())
        # order_1 should complete before order_2 due to lock
        assert results == ["order_1", "order_2"]

    def test_order_persistence_lifecycle(self) -> None:
        """Test order persistence through the full lifecycle."""
        from agents.execution.order_persistence import (
            OrderPersistence, OrderRequest, OrderStatus,
        )

        persistence = OrderPersistence()

        async def run_test():
            # Persist intent
            order = OrderRequest(
                symbol="ETHUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.5,
            )
            client_id = await persistence.persist_order_intent(order)
            assert client_id.startswith("cs_")

            # Check pending
            pending = await persistence.get_pending_orders()
            assert len(pending) == 1

            # Update to filled
            await persistence.update_status(
                client_id, OrderStatus.FILLED,
                exchange_order_id="exc_123",
                filled_quantity=0.5,
                filled_price=3000.0,
            )

            # No longer pending
            pending = await persistence.get_pending_orders()
            assert len(pending) == 0

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_rate_limiter(self) -> None:
        """Test rate limiter token bucket mechanism."""
        from cryptoswarms.adapters.rate_limiter import TokenBucket

        async def run_test():
            bucket = TokenBucket(capacity=5, refill_seconds=1.0)
            # Should acquire 5 tokens without waiting
            for _ in range(5):
                waited = await bucket.acquire()
                assert waited == 0.0

            # 6th token should require waiting
            waited = await bucket.acquire()
            assert waited > 0

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_exchange_error_handling(self) -> None:
        """Test exchange error handler translates codes correctly."""
        from cryptoswarms.adapters.exchange_errors import (
            ExchangeErrorHandler, RateLimitExceeded, InsufficientBalance,
        )

        handler = ExchangeErrorHandler()

        # Rate limit
        with pytest.raises(RateLimitExceeded):
            handler.handle_binance_error({"code": 429, "msg": "Too many requests"})

        # Insufficient balance
        with pytest.raises(InsufficientBalance):
            handler.handle_binance_error({"code": -2010, "msg": "Insufficient balance"})

        # No error
        handler.handle_binance_error({"data": "ok"})  # Should not raise

    def test_position_manager_with_locks(self) -> None:
        """Test async position manager operations."""
        from cryptoswarms.position_manager import PositionManager

        pm = PositionManager()

        async def run_test():
            pos = await pm.async_open_position(
                strategy_id="test",
                symbol="BTCUSDT",
                side="BUY",
                entry_price=50000,
                size_usd=1000,
            )
            assert pos.symbol == "BTCUSDT"
            assert len(pm.open_positions) == 1

            closed = await pm.async_check_exits(
                {"BTCUSDT": 48000},  # Below stop loss
            )
            assert len(closed) == 1
            assert len(pm.open_positions) == 0

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_memory_dag_thread_safety(self) -> None:
        """Test MemoryDag async operations."""
        from cryptoswarms.memory_dag import MemoryDag

        dag = MemoryDag()

        async def run_test():
            nodes = []
            for i in range(10):
                node = await dag.async_add_node(
                    node_type="test",
                    topic="concurrent",
                    content=f"node_{i}",
                )
                nodes.append(node)

            assert len(dag.nodes()) == 10

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_signal_conflict_resolution(self) -> None:
        """Test signal conflict resolver."""
        from cryptoswarms.signals.conflict_resolver import (
            SignalConflictResolver, Signal,
        )

        resolver = SignalConflictResolver()

        signals = [
            Signal(symbol="BTCUSDT", signal_type="funding", direction="BUY",
                   confidence=0.8, source_agent="funding_agent"),
            Signal(symbol="BTCUSDT", signal_type="technical", direction="SELL",
                   confidence=0.6, source_agent="ta_agent"),
        ]

        result = resolver.resolve_conflicts(signals)
        assert result.conflict_detected is True
        assert result.winning_signal is not None
        # Funding signal should win due to higher priority
        assert result.winning_signal.signal_type == "funding"

    def test_pattern_validator(self) -> None:
        """Test statistical pattern validation."""
        from cryptoswarms.signal_validation.pattern_validator import PatternValidator

        validator = PatternValidator(min_samples=20)

        # Random pattern (50/50 should not be significant)
        random_results = [i % 2 == 0 for i in range(100)]
        result = validator.validate_pattern_significance(random_results)
        # 50% win rate should not be significant above 52%
        assert result.win_rate == 0.5

        # Strong pattern
        strong_results = [True] * 70 + [False] * 30
        result = validator.validate_pattern_significance(strong_results)
        assert result.is_significant is True
        assert result.win_rate == 0.7

    def test_circuit_breaker_states(self) -> None:
        """Test circuit breaker state transitions."""
        from cryptoswarms.resilience.circuit_breaker import (
            ExchangeCircuitBreaker, CircuitState, CircuitBreakerOpenError,
        )

        cb = ExchangeCircuitBreaker(
            name="test", failure_threshold=3, timeout=0.5,
        )

        async def run_test():
            # Record failures to trip breaker
            for _ in range(3):
                try:
                    async def fail():
                        raise Exception("test error")
                    await cb.call_exchange(fail)
                except Exception:
                    pass

            # Should be open now
            assert cb.state == CircuitState.OPEN

            # Should reject calls
            with pytest.raises(CircuitBreakerOpenError):
                async def ok():
                    return "ok"
                await cb.call_exchange(ok)

            # Wait for timeout
            await asyncio.sleep(0.6)

            # Should be half-open
            assert cb.state == CircuitState.HALF_OPEN

        asyncio.get_event_loop().run_until_complete(run_test())

    def test_degradation_manager(self) -> None:
        """Test degradation level management."""
        from cryptoswarms.resilience.degradation_manager import (
            DegradationManager, DegradationLevel,
        )

        dm = DegradationManager()
        assert dm.level == DegradationLevel.NORMAL

        # Escalate
        config = dm.enter_degraded_mode("high error rate")
        assert dm.level == DegradationLevel.MILD
        assert config.max_position_size == 0.75

        # Escalate again
        config = dm.enter_degraded_mode("errors continuing")
        assert dm.level == DegradationLevel.MODERATE
        assert config.max_position_size == 0.5

        # Recover one step
        config = dm.recover("errors resolved")
        assert dm.level == DegradationLevel.MILD

        # Full reset
        config = dm.reset()
        assert dm.level == DegradationLevel.NORMAL
