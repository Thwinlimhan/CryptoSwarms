# CryptoSwarms System Architecture

This document describes the high-level architecture and core components of the CryptoSwarms trading system, focusing on security, reliability, and risk management.

## System Overview

CryptoSwarms is an agentic AI trading system designed for perpetual futures markets. It uses a swarm of specialized agents to scan markets, evaluate risk, classify market regimes, and execute trades.

## Core Modules

### 1. Adapters (`cryptoswarms/adapters/`)
- **`exchange_config.py`**: Centralized configuration for exchange endpoints (Binance, Hyperliquid) supporting both live and testnet modes.
- **`exchange_errors.py`**: Structured error handling that translates exchange-specific error codes into domain exceptions.
- **`rate_limiter.py`**: Token-bucket based rate limiting to prevent API bans.
- **`websocket_manager.py`**: Manages persistent WebSocket connections with automatic exponential backoff reconnection.

### 2. Agents (`agents/`)
- **`orchestration/signal_deduplicator.py`**: Prevents duplicate signal processing using TTL-based caching.
- **`execution/execution_coordinator.py`**: Symbol-level locking to prevent concurrent order execution for the same asset.
- **`execution/order_persistence.py`**: Persists order intent before submission to ensure no "ghost orders" are lost.
- **`execution/order_reconciler.py`**: Periodically reconciles local order state with exchange state for consistency.

### 3. Risk Management (`cryptoswarms/risk/`)
- **`correlation_manager.py`**: Monitors and limits portfolio-wide correlation risk across asset groups.
- **`sector_limits.py`**: Enforces concentration limits within specific crypto sectors (DeFi, L1, AI, etc.).
- **`volatility_sizer.py`**: Adjusts position sizes inversely with realized volatility to target constant risk.

### 4. Signal Processing (`cryptoswarms/signals/`)
- **`conflict_resolver.py`**: Resolves opposing signals using a priority matrix (Funding > Volume > Technical).
- **`ensemble_weighter.py`**: Combines multiple signal sources using calibrated weights based on historical performance.
- **`regime_aware_signals.py`**: Adapts signal generation logic to the current market regime (Trending vs. Volatile vs. Ranging).
- **`signal_decay.py`**: Models the temporal decay of signal confidence using type-specific half-lives.

### 5. Resilience (`cryptoswarms/resilience/`)
- **`circuit_breaker.py`**: Implements the Circuit Breaker pattern for exchange API calls to prevent cascade failures.
- **`degradation_manager.py`**: Automatically scales down system activity (sizing, confidence thresholds) under technical or market stress.

### 6. Observability (`cryptoswarms/tracing/` & `monitoring/`)
- **`trace_logger.py`**: Structured JSON logging with trace IDs for end-to-end auditability.
- **`execution_tracer.py`**: Deep tracing of the full execution chain: Signal → Decision → Sizing → Execution → Fill.
- **`agent_metrics.py`**: Per-agent performance tracking (success rates, latency percentiles).
- **`alert_manager.py`**: Rules-based alerting for critical system events (drawdown, error rates, stale positions).

## Data Flow

1. **Market Data**: `WebSocketManager` streams live tick data and order book updates.
2. **Signal Generation**: `ScannerAgent` and `RegimeAgent` produce raw signals.
3. **Signal Refinement**: Signals are deduplicated, de-conflicted, and weighted by the `SignalEnsemble`.
4. **Risk Pre-flight**: `PositionManager` and `RiskManager` (Correlation, Sector, Volatility) evaluate the proposed trade.
5. **Execution**: `ExecutionCoordinator` locks the symbol, `OrderPersistence` saves the intent, and `HyperliquidAdapter` submits the order via a `CircuitBreaker`.
6. **Post-trade**: `OrderReconciler` verifies the fill, and `PerformanceAttributor` decomposes the PnL.

## Deployment & Testing

- **Hot Reload**: `HotReloadManager` allows swapping strategies at runtime by draining positions and reloading modules.
- **A/B Testing**: `ABTestFramework` routes signals to different strategy variants using consistent hashing.
- **Integration Tests**: `tests/integration/test_full_system.py` validates the entire pipeline from signal to execution.
