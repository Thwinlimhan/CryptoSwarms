"""Decision science sub-package — EV, Bayesian, Kelly, base rates."""

from cryptoswarms.decision_engine import (
    BinaryDecisionInput, BinaryDecisionResult, ExpectedValueResult,
    OutcomeScenario, evaluate_binary_decision, expected_value,
)
from cryptoswarms.bayesian_update import (
    bayes_update, clamp_probability, sentiment_likelihoods, sequential_bayes_update,
)
from cryptoswarms.fractional_kelly import (
    empirical_fractional_kelly, kelly_fraction, position_size_from_bankroll,
)
from cryptoswarms.base_rate_registry import (
    BaseRateProfile, BaseRateRegistry, default_base_rate_registry,
)
from cryptoswarms.failure_ledger import FailureLedger, DecisionRecord

__all__ = [
    "BinaryDecisionInput", "BinaryDecisionResult", "ExpectedValueResult",
    "OutcomeScenario", "evaluate_binary_decision", "expected_value",
    "bayes_update", "clamp_probability", "sentiment_likelihoods", "sequential_bayes_update",
    "empirical_fractional_kelly", "kelly_fraction", "position_size_from_bankroll",
    "BaseRateProfile", "BaseRateRegistry", "default_base_rate_registry",
    "FailureLedger", "DecisionRecord",
]
