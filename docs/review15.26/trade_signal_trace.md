# CryptoSwarms Trade Signal Trace: Origin to Execution

**Analysis Date:** March 15, 2026  
**Trace Scope:** Complete end-to-end signal flow with failure mode analysis

## Signal Flow Overview

```
Market Scanner → Research Factory → Cache Lookup → Backtesting Pipeline → 
Risk Framework → Decision Council → Execution Router → Exchange API → 
Post-Trade Logging → Memory Update
```

---

## **HANDOFF 1: Market Scanner → Research Factory**

### Data Structure Passed:
```python
# From scanner.py _emit()
signal_payload = {
    "signal_type": "BREAKOUT",           # BREAKOUT | SMART_MONEY | FUNDING | REGIME
    "symbol": "BTCUSDT", 
    "confidence": 0.65,                  # min_confidence from ScannerConfig
    "priority": "HIGH",                  # HIGH | MEDIUM | LOW
    "data": {
        "source": "scanner_breakout",
        "inflow_usd": 2_500_000.0       # for SMART_MONEY signals
    },
    "suggested_hypothesis": "BREAKOUT candidate for BTCUSDT"
}
```

### Transport Mechanism:
- **Protocol:** `SignalSink.publish(topic="research:signals", payload=dict)`
- **Implementation:** Direct method call (no queue/async)

### What Can Go Wrong:
1. **Scanner data source failure**: `MarketDataSource.fetch_top_symbols()` throws exception
2. **Signal sink unavailable**: Research factory not listening to signals
3. **Memory recorder failure**: `MemoryRecorder.remember()` fails silently
4. **Heartbeat store failure**: Scanner heartbeat not recorded

### Timeout/Retry Mechanism:
- ❌ **No timeout**: Scanner runs synchronously with no time limits
- ❌ **No retry**: Failed signals are lost permanently
- ❌ **No circuit breaker**: Connector failures can block entire cycle

### Failure Logging:
- ✅ **Memory recorder**: Logs signal to runtime memory if available
- ❌ **No error logging**: Exceptions not caught or logged
- ❌ **No dead letter queue**: Failed signals disappear

### Recovery:
- ❌ **Not recoverable**: Lost signals cannot be replayed

---

## **HANDOFF 2: Research Factory → Layer 2 Cache Lookup**

### Data Structure Passed:
```python
# From research_factory.py _recall_context_nodes()
dag_walker_query = {
    "topic": "btcusdt_research",
    "lookback_hours": 72,
    "max_nodes": 4,
    "token_budget": 500,
    "provenance_half_life_hours": 72,
    "min_provenance_confidence": 0.15
}

# Returns DagRecallResult
context_result = {
    "nodes": [MemoryDagNode(...)],      # Previous research context
    "token_estimate": 347,
    "truncated": False
}
```

### Transport Mechanism:
- **Protocol:** Direct `DagWalker.recall()` method call
- **Implementation:** In-memory DAG traversal with provenance decay

### What Can Go Wrong:
1. **DAG corruption**: Memory DAG nodes have invalid timestamps or metadata
2. **Provenance decay overflow**: Exponential decay calculation fails with extreme values
3. **Token budget exceeded**: Context truncated, losing important historical signals
4. **Memory exhaustion**: Large DAG causes OOM during traversal

### Timeout/Retry Mechanism:
- ❌ **No timeout**: DAG traversal can run indefinitely on large graphs
- ❌ **No retry**: Failed lookups return empty context
- ⚠️ **Graceful degradation**: Returns empty result on failure

### Failure Logging:
- ❌ **Silent failures**: DAG lookup failures not logged
- ✅ **Metadata tracking**: Provenance confidence and age recorded

### Recovery:
- ✅ **Partially recoverable**: Research can continue without historical context
- ❌ **Context loss**: Failed lookups lose valuable signal history

---

## **HANDOFF 3: Research Factory → Backtesting Pipeline**

### Data Structure Passed:
```python
# From research_factory.py _build_backtest_request()
backtest_request = BacktestRequest(
    request_id="bt-btcusdt-20260315-001",
    hypothesis_id="research-btcusdt-0",
    strategy_module="strategies.breakout_momentum",
    class_name="BreakoutMomentumStrategy", 
    params={
        "lookback_period": 14.0,
        "breakout_threshold": 0.02,
        "stop_loss": 0.015,
        "take_profit": 0.045
    },
    market_data={"close": [45000.0, 45100.0, ...]},  # OHLCV data
    benchmark_returns=[0.001, -0.002, 0.003, ...]
)

# Converted to StrategyCandidate for validation
strategy_candidate = StrategyCandidate(
    strategy_id="research-btcusdt-0",
    module_path="strategies.breakout_momentum",
    class_name="BreakoutMomentumStrategy",
    params=backtest_request.params,
    market_data=backtest_request.market_data,
    benchmark_returns=backtest_request.benchmark_returns
)
```

### Transport Mechanism:
- **Protocol:** `HypothesisQueue.publish(payload=dict)` 
- **Implementation:** Direct queue publish (likely Redis streams)

### What Can Go Wrong:
1. **Strategy module import failure**: Module path invalid or class doesn't exist
2. **Parameter validation failure**: Invalid parameter types or ranges
3. **Market data corruption**: Missing OHLCV data or invalid timestamps
4. **Queue unavailable**: Backtest queue down or full
5. **Serialization failure**: Complex objects can't be JSON serialized

### Timeout/Retry Mechanism:
- ❌ **No timeout**: Queue publish can block indefinitely
- ❌ **No retry**: Failed publishes are lost
- ❌ **No backpressure**: Queue can overflow with requests

### Failure Logging:
- ❌ **No error handling**: Exceptions not caught in research factory
- ✅ **Memory recording**: Hypothesis recorded to DAG before queue publish

### Recovery:
- ❌ **Not recoverable**: Failed backtest requests are lost permanently
- ⚠️ **Partial recovery**: Hypothesis exists in DAG but won't be validated

---

## **HANDOFF 4: Backtesting Pipeline → Risk Framework**

### Data Structure Passed:
```python
# From validation_pipeline.py emit_validation_event()
validation_summary = ValidationSummary(
    strategy_id="research-btcusdt-0",
    run_id="550e8400-e29b-41d4-a716-446655440000",
    gate_results=[
        GateResult(gate_number=1, gate_name="syntax_check", status=GateStatus.PASS, score=1.0),
        GateResult(gate_number=0, gate_name="data_quality", status=GateStatus.PASS, score=0.98),
        GateResult(gate_number=2, gate_name="sensitivity", status=GateStatus.PASS, score=0.82),
        GateResult(gate_number=3, gate_name="vectorbt_screen", status=GateStatus.PASS, score=0.75),
        GateResult(gate_number=4, gate_name="walk_forward", status=GateStatus.PASS, score=0.68),
        GateResult(gate_number=5, gate_name="regime_evaluation", status=GateStatus.PASS, score=0.71),
        GateResult(gate_number=6, gate_name="correlation_check", status=GateStatus.PASS, score=0.89)
    ]
)

# Emitted to execution queue as JSON
queue_payload = {
    "run_id": "550e8400-e29b-41d4-a716-446655440000",
    "strategy_id": "research-btcusdt-0", 
    "status": "pass",                    # "pass" | "fail"
    "generated_at": "2026-03-15T14:30:00Z",
    "gate_results": [...]               # Serialized gate results
}
```

### Transport Mechanism:
- **Protocol:** `ExecutionQueue.xadd(stream="execution.validation.events", fields=dict)`
- **Implementation:** Redis Streams with JSON payload

### What Can Go Wrong:
1. **Gate execution failure**: Individual gates crash during validation
2. **Database persistence failure**: Gate results can't be saved to TimescaleDB
3. **Queue stream failure**: Redis streams unavailable or corrupted
4. **JSON serialization failure**: Complex gate details can't be serialized
5. **Early exit cascade**: One gate failure blocks remaining gates

### Timeout/Retry Mechanism:
- ✅ **Gate isolation**: Each gate fails independently with early exit
- ❌ **No timeout**: Long-running backtests can block pipeline
- ❌ **No retry**: Failed validations are not retried

### Failure Logging:
- ✅ **Database persistence**: Each gate result saved to TimescaleDB
- ✅ **Queue event**: Validation summary emitted regardless of pass/fail
- ❌ **No error details**: Exception details not captured in gate results

### Recovery:
- ✅ **Fully recoverable**: Gate results persisted, can replay from any gate
- ✅ **Audit trail**: Complete validation history in database

---

## **HANDOFF 5: Risk Framework → Decision Council**

### Data Structure Passed:
```python
# From decision_council.py CouncilInput
council_input = CouncilInput(
    strategy_id="research-btcusdt-0",
    scorecard_eligible=True,            # Passed institutional gate
    institutional_gate_ok=True,         # Excess Sharpe ≥ 0.15
    attribution_ready=True,             # Live attribution available
    risk_halt_active=False,             # No circuit breaker active
    strategy_count_ok=True,             # Under strategy count limits
    expected_value_after_costs_usd=12.50,  # EV calculation result
    posterior_probability=0.73,         # Bayesian update result
    project_id="default",
    requested_secret_envs=("HYPERLIQUID_PRIVATE_KEY",)
)
```

### Transport Mechanism:
- **Protocol:** Direct `DecisionCouncil.decide(payload=CouncilInput)` async method call
- **Implementation:** In-process async function call

### What Can Go Wrong:
1. **Guardrail failures**: Input/output/tool/delegation guardrails reject decision
2. **DAG context failure**: Memory DAG lookup fails during decision context
3. **Debate solver failure**: Individual solvers crash during voting
4. **MCP registry failure**: Tool authorization fails
5. **Governor gate failure**: Final risk checks fail
6. **Circular dependency**: Guardrails create infinite loops

### Timeout/Retry Mechanism:
- ❌ **No timeout**: Decision process can run indefinitely
- ❌ **No retry**: Failed decisions are not retried
- ⚠️ **Partial retry**: Individual debate rounds can be retried

### Failure Logging:
- ✅ **Comprehensive logging**: All guardrail results captured
- ✅ **Debate history**: All rounds and votes recorded
- ✅ **Decision checkpoint**: Final decision persisted to DAG

### Recovery:
- ✅ **Fully recoverable**: Decision checkpoints enable replay
- ✅ **Audit trail**: Complete decision history with dissent tracking

---

## **HANDOFF 6: Decision Council → Execution Router**

### Data Structure Passed:
```python
# From decision_council.py CouncilDecision
council_decision = CouncilDecision(
    decision="go",                      # "go" | "hold"
    confidence=0.78,
    dissent_ratio=0.15,                # Minority dissent percentage
    passed_governor=True,
    reason="EV=$12.50, post=0.73, institutional_gate=pass",
    stages=["input_guard", "project_scope", "dag_recall", "mcp_registry", 
            "tool_guard", "delegation_guard", "debate", "governor", "output_guard"],
    rounds=[DebateRound(...)],         # Complete debate history
    aggregate=DebateAggregate(...),    # Weighted vote aggregation
    guardrails={"input": GuardrailResult(...), ...},
    dag_context_node_ids=["abc123", "def456"],
    decision_checkpoint_node_id="ghi789"
)

# Converted to OrderIntent for execution
order_intent = OrderIntent(
    symbol="BTCUSDT",
    side="BUY",                        # BUY | SELL
    quantity=0.025,                    # Kelly-sized position
    reduce_only=False
)
```

### Transport Mechanism:
- **Protocol:** Direct `ExecutionRouter.route()` async method call
- **Implementation:** In-process async function with risk snapshot

### What Can Go Wrong:
1. **Risk snapshot stale**: Risk data outdated during decision delay
2. **Heartbeat timeout**: Risk monitor heartbeat expired
3. **Circuit breaker activation**: Risk tier changed during decision process
4. **Dead-man switch triggered**: Risk monitor crashed
5. **Order intent validation**: Invalid symbol/quantity/side parameters

### Timeout/Retry Mechanism:
- ❌ **No timeout**: Execution routing can block indefinitely
- ❌ **No retry**: Failed routing not retried
- ✅ **Graceful degradation**: Reduces to reductions-only mode on risk issues

### Failure Logging:
- ✅ **Gate decision logging**: All risk gate decisions recorded
- ✅ **Execution decision**: Route decision with reason captured
- ❌ **No error details**: Exception details not captured

### Recovery:
- ✅ **Recoverable**: Can retry with fresh risk snapshot
- ⚠️ **Timing sensitive**: Market conditions may have changed

---

## **HANDOFF 7: Execution Router → Exchange API**

### Data Structure Passed:
```python
# From execution_router.py to OrderExecutor
order_intent = OrderIntent(
    symbol="BTCUSDT",
    side="BUY", 
    quantity=0.025,
    reduce_only=False
)

# HyperliquidAdapter.execute() converts to HL format
hl_order_payload = {
    "action": {
        "type": "order",
        "orders": [{
            "a": 0,                     # Asset ID for BTC
            "b": True,                  # is_buy = True
            "s": "0.025",              # Size as string
            "p": "45450.0",            # Limit price (1% slippage)
            "t": {"limit": {"tif": "Gtc"}},  # Time in force
            "r": False                  # reduce_only
        }],
        "grouping": "na"
    },
    "nonce": 0,
    "signature": {"r": "", "s": "", "v": 0},  # Placeholder for paper mode
    "wallet": "0x742d35Cc6634C0532925a3b8D4C9db96590b5b8c"
}
```

### Transport Mechanism:
- **Protocol:** `OrderExecutor.execute(intent, reduce_only)` async method
- **Implementation:** HTTP POST to Hyperliquid/HyPaper API via `httpx.AsyncClient`

### What Can Go Wrong:
1. **Network failure**: HTTP request timeout or connection error
2. **API authentication failure**: Invalid wallet or signature
3. **Exchange rejection**: Insufficient balance, invalid symbol, market closed
4. **Rate limiting**: Exchange API rate limits exceeded
5. **Price slippage**: Market moved beyond 1% slippage tolerance
6. **Asset mapping failure**: Symbol not found in exchange metadata

### Timeout/Retry Mechanism:
- ✅ **HTTP timeout**: 10-second timeout on HTTP requests
- ❌ **No retry**: Failed orders not retried automatically
- ❌ **No exponential backoff**: Rate limit failures not handled

### Failure Logging:
- ✅ **Error logging**: HTTP failures logged with details
- ❌ **No structured logging**: Errors not captured in structured format
- ❌ **No order tracking**: No order ID tracking for fills/cancels

### Recovery:
- ❌ **Not recoverable**: Failed orders lost, no retry mechanism
- ❌ **No order status**: Can't check if order was partially filled

---

## **HANDOFF 8: Exchange API → Post-Trade Logging**

### Data Structure Passed:
```python
# From HyperliquidAdapter response
exchange_response = {
    "status": "ok",                    # "ok" | "err"
    "response": {
        "type": "order",
        "data": {
            "statuses": [{
                "resting": {
                    "oid": 12345678,          # Order ID
                    "cloid": "0x1a2b3c..."    # Client order ID
                }
            }]
        }
    }
}

# Converted to risk event
risk_event = {
    "table": "risk_events",
    "event_type": "order_placed",
    "timestamp": "2026-03-15T14:30:15Z",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.025,
    "order_id": 12345678,
    "status": "resting"
}
```

### Transport Mechanism:
- **Protocol:** `RiskEventLogger.log(event=dict)` method call
- **Implementation:** In-memory list append (InMemoryRiskEventLogger)

### What Can Go Wrong:
1. **Logger unavailable**: Risk event logger not initialized
2. **Memory overflow**: In-memory logger grows unbounded
3. **Serialization failure**: Complex event objects can't be logged
4. **Heartbeat failure**: Risk monitor heartbeat not published
5. **Event publisher failure**: Risk events not published to channels

### Timeout/Retry Mechanism:
- ❌ **No timeout**: Logging operations synchronous
- ❌ **No retry**: Failed log writes are lost
- ❌ **No persistence**: In-memory logger loses data on restart

### Failure Logging:
- ✅ **Event capture**: Risk events captured in memory
- ❌ **No error handling**: Logger failures not handled
- ❌ **No durability**: Events lost on process restart

### Recovery:
- ❌ **Not recoverable**: In-memory events lost on failure
- ❌ **No audit trail**: No persistent record of trade execution

---

## **HANDOFF 9: Post-Trade Logging → Memory Update**

### Data Structure Passed:
```python
# From risk_monitor.py to MemoryDag
execution_memory_node = MemoryDagNode(
    node_id="exec789",                 # SHA1 hash of content
    node_type="execution_result",
    topic="btcusdt_execution",
    content="BUY 0.025 BTCUSDT @ 45450.0 - Order ID: 12345678",
    created_at=datetime(2026, 3, 15, 14, 30, 15, tzinfo=timezone.utc),
    metadata={
        "symbol": "BTCUSDT",
        "side": "BUY", 
        "quantity": 0.025,
        "price": 45450.0,
        "order_id": 12345678,
        "strategy_id": "research-btcusdt-0",
        "confidence": 0.78,
        "expected_value": 12.50
    }
)

# DAG edge linking decision to execution
dag_edge = MemoryDagEdge(
    from_node_id="ghi789",            # Decision checkpoint node
    to_node_id="exec789"              # Execution result node
)
```

### Transport Mechanism:
- **Protocol:** Direct `MemoryDag.add_node()` and `MemoryDag.add_edge()` method calls
- **Implementation:** In-memory DAG with periodic JSON persistence

### What Can Go Wrong:
1. **DAG corruption**: Invalid node IDs or circular references
2. **Memory exhaustion**: DAG grows too large for available memory
3. **Persistence failure**: JSON serialization fails during save
4. **Concurrent access**: Multiple threads modifying DAG simultaneously
5. **Metadata overflow**: Large metadata objects cause memory issues

### Timeout/Retry Mechanism:
- ❌ **No timeout**: DAG operations synchronous
- ❌ **No retry**: Failed DAG updates are lost
- ⚠️ **Graceful degradation**: DAG continues without failed nodes

### Failure Logging:
- ❌ **Silent failures**: DAG update failures not logged
- ❌ **No validation**: Invalid nodes accepted into DAG
- ✅ **Persistence**: Periodic JSON saves provide recovery

### Recovery:
- ✅ **Partially recoverable**: Can reload from last JSON save
- ❌ **Data loss**: Recent updates lost between saves

---

## **Critical Failure Points Analysis**

### **Most Fragile Handoff: #7 (Execution Router → Exchange API)**

**Why This Is The Most Fragile:**

1. **Network Dependency**: Only handoff that crosses network boundary
2. **External System**: Relies on third-party exchange availability
3. **No Retry Logic**: Failed orders are permanently lost
4. **Authentication Complexity**: Wallet signing and nonce management
5. **Market Timing**: Price slippage can invalidate entire trade thesis
6. **Rate Limiting**: Exchange can throttle or block requests
7. **Partial Fills**: No handling of partial order execution

**Failure Impact:**
- **Financial Loss**: Failed trades can miss profitable opportunities
- **Strategy Invalidation**: Market conditions change during retry delays
- **Audit Trail Gaps**: No record of failed execution attempts
- **Risk Accumulation**: Failed risk-reducing orders leave positions exposed

**Recommended Improvements:**
```python
class RobustOrderExecutor:
    async def execute_with_retry(self, intent: OrderIntent, max_retries: int = 3) -> ExecutionResult:
        for attempt in range(max_retries):
            try:
                result = await self._execute_order(intent)
                await self._log_execution(result)
                return result
            except RateLimitError as e:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            except NetworkError as e:
                if attempt == max_retries - 1:
                    await self._log_failed_execution(intent, e)
                    raise
```

### **Second Most Fragile: #3 (Research Factory → Backtesting Pipeline)**

**Why This Is Critical:**
- **No Error Handling**: Exceptions not caught in research factory
- **Queue Dependency**: Backtest queue can be unavailable or full
- **Serialization Risk**: Complex objects may fail JSON serialization
- **No Backpressure**: Queue overflow can lose requests

### **Third Most Fragile: #1 (Market Scanner → Research Factory)**

**Why This Matters:**
- **No Circuit Breakers**: Connector failures block entire research cycle
- **No Timeout**: Scanner can hang indefinitely on data source failures
- **Signal Loss**: Failed signals disappear without recovery mechanism

---

## **System-Wide Recommendations**

### **Immediate Fixes:**

1. **Add Retry Logic to Exchange Execution**
   ```python
   @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
   async def execute_order(self, intent: OrderIntent) -> ExecutionResult:
   ```

2. **Implement Circuit Breakers for Research**
   ```python
   class ResearchCircuitBreaker:
       def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
           self.failure_count = 0
           self.last_failure_time = None
           self.state = "CLOSED"  # CLOSED | OPEN | HALF_OPEN
   ```

3. **Add Structured Error Logging**
   ```python
   logger.error("Order execution failed", extra={
       "symbol": intent.symbol,
       "side": intent.side, 
       "quantity": intent.quantity,
       "error_type": type(e).__name__,
       "error_message": str(e)
   })
   ```

### **Architectural Improvements:**

1. **Event-Driven Architecture**: Replace direct method calls with async events
2. **Dead Letter Queues**: Capture and replay failed messages
3. **Distributed Tracing**: Track signals across all handoffs
4. **Health Checks**: Monitor each component's availability
5. **Graceful Degradation**: Continue operating with reduced functionality

### **Monitoring & Observability:**

1. **End-to-End Tracing**: Track signal ID through entire pipeline
2. **Latency Monitoring**: Measure time at each handoff
3. **Error Rate Tracking**: Monitor failure rates per component
4. **Business Metrics**: Track signal-to-execution conversion rates

The current architecture has sophisticated domain logic but lacks the operational resilience needed for production trading systems. The exchange execution handoff represents the highest risk point and should be the first priority for improvement.