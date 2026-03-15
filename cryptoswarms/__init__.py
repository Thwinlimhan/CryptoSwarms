"""Core domain logic for CryptoSwarms.

DEPRECATION NOTICE:
Directly importing from 'cryptoswarms' is deprecated. 
Please use targeted sub-package imports instead:
  - cryptoswarms.decision
  - cryptoswarms.risk_control
  - cryptoswarms.memory
  - cryptoswarms.pipeline
"""

import warnings
from typing import Any

warnings.warn(
    "Directly importing from 'cryptoswarms' is deprecated. Use sub-packages instead.",
    DeprecationWarning, stacklevel=2
)

# ── Decision Science ────────────────────────────────────────────────────────
from .decision import (
    BinaryDecisionInput, BinaryDecisionResult, ExpectedValueResult,
    OutcomeScenario, evaluate_binary_decision, expected_value,
    bayes_update, clamp_probability, sentiment_likelihoods, sequential_bayes_update,
    empirical_fractional_kelly, kelly_fraction, position_size_from_bankroll,
    BaseRateProfile, BaseRateRegistry, default_base_rate_registry,
    FailureLedger, DecisionRecord,
)

# ── Risk & Safety ────────────────────────────────────────────────────────────
from .risk_control import (
    RiskSnapshot, evaluate_circuit_breaker, CircuitBreakerLevel,
    ExecutionGateDecision, evaluate_pre_execution_gate,
    DeadMansSwitchConfig, DeadMansSwitchState, evaluate_dead_mans_switch,
    BudgetStatus, evaluate_budget,
    MacroEvent, in_macro_blackout,
)
# Legacy re-exports to match existing __all__
from .risk import CircuitBreakerLevel, RiskSnapshot
from .deadman import DeadMansSwitchConfig, DeadMansSwitchState, evaluate_dead_mans_switch

# ── Memory ───────────────────────────────────────────────────────────────────
from .memory import (
    MemoryDagNode, MemoryDagEdge, MemoryDag,
    DagRecallResult, DagWalker,
    DagSummarizationConfig, DagSummarizationResult, maybe_summarize_topic, maybe_summarize_topics,
)
# Legacy re-exports
from .memory_dag import MemoryDag, MemoryDagEdge, MemoryDagNode
from .dag_recall import DagRecallResult
from .dag_summarizer import DagSummarizationConfig, DagSummarizationResult, maybe_summarize_topic, maybe_summarize_topics

# ── Pipeline & Agents ───────────────────────────────────────────────────────
from .pipeline import (
    AgentRunner, ScannerAgent, ScannerConfig as ScannerAgentConfig,
    RiskAgent, RegimeAgent, FundingAgent,
)
# Existing pipeline modules
from .pipeline import BacktestReport, GateChainOrchestrator, PipelineResult, StrategyDraft, StrategyHandoffOrchestrator
from .scheduler import MarketScannerScheduler, SchedulerConfig
from .scanner import MarketScannerCycleRunner, ScannerConfig

# ── Other Infrastructure ─────────────────────────────────────────────────────
from .core_adapters import PostgresSqlExecutor, RedisKeyValueStore
from .deepflow_preflight import DeepflowPreflightStatus, evaluate_deepflow_preflight
from .crypto_strategy_pack import (
    CompressionBreakoutPoint, MomentumRotationResult, PairSpreadPoint,
    cross_sectional_momentum_rotation, pairs_spread_mean_reversion, volatility_compression_breakout,
)
from .execution_router import ExecutionRouter, OrderIntent, RoutedOrderDecision
from .costs import LlmCostEvent, ensure_costs_schema, read_daily_cost_totals, write_llm_cost
from .storage import HeartbeatRecord, get_heartbeat, set_heartbeat

__all__ = [
    "BacktestReport", "BaseRateProfile", "BaseRateRegistry", "BinaryDecisionInput",
    "BinaryDecisionResult", "CompressionBreakoutPoint", "DagRecallResult",
    "DagWalker", "DeepflowPreflightStatus", "ExpectedValueResult",
    "FailureLedger", "GateChainOrchestrator", "MemoryDag",
    "MemoryDagEdge", "MemoryDagNode", "DagSummarizationConfig",
    "DagSummarizationResult", "maybe_summarize_topic", "maybe_summarize_topics",
    "TopicSummary", "summarize_dag_topics",
    "MomentumRotationResult", "DecisionRecord", "OutcomeScenario",
    "PairSpreadPoint", "PipelineResult", "StrategyDraft",
    "StrategyHandoffOrchestrator", "MarketScannerScheduler", "SchedulerConfig",
    "PostgresSqlExecutor", "RedisKeyValueStore", "ExecutionRouter",
    "OrderIntent", "RoutedOrderDecision",
    "RiskSnapshot", "evaluate_circuit_breaker", "CircuitBreakerLevel",
    "ExecutionGateDecision", "evaluate_pre_execution_gate",
    "DeadMansSwitchConfig", "DeadMansSwitchState", "evaluate_dead_mans_switch",
    "BudgetStatus", "evaluate_budget",
    "MacroEvent", "in_macro_blackout",
    "pairs_spread_mean_reversion", "volatility_compression_breakout",
    "AgentRunner", "ScannerAgent", "RiskAgent", "RegimeAgent", "FundingAgent",
]
