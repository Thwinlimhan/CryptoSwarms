"""Risk control sub-package — circuit breakers, execution guards, deadman switch."""

from cryptoswarms.risk import (
    RiskSnapshot, evaluate_circuit_breaker, CircuitBreakerLevel
)
from cryptoswarms.execution_guard import (
    ExecutionGateDecision, evaluate_pre_execution_gate
)
from cryptoswarms.deadman import (
    DeadMansSwitchConfig, DeadMansSwitchState, evaluate_dead_mans_switch
)
from cryptoswarms.budget_guard import (
    BudgetStatus, evaluate_budget
)
from cryptoswarms.macro_calendar import (
    MacroEvent, in_macro_blackout
)

__all__ = [
    "RiskSnapshot", "evaluate_circuit_breaker", "CircuitBreakerLevel",
    "ExecutionGateDecision", "evaluate_pre_execution_gate",
    "DeadMansSwitchConfig", "DeadMansSwitchState", "evaluate_dead_mans_switch",
    "BudgetStatus", "evaluate_budget",
    "MacroEvent", "in_macro_blackout",
]
