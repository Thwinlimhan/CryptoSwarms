from __future__ import annotations

from dataclasses import dataclass

from cryptoswarms.bayesian_update import bayes_update, clamp_probability


@dataclass(frozen=True)
class OutcomeScenario:
    probability: float
    payoff_usd: float


@dataclass(frozen=True)
class ExpectedValueResult:
    expected_value_usd: float
    expected_value_after_costs_usd: float
    total_costs_usd: float


@dataclass(frozen=True)
class BinaryDecisionInput:
    prior_probability: float
    likelihood_if_true: float
    likelihood_if_false: float
    payoff_win_usd: float
    payoff_loss_usd: float
    fees_usd: float = 0.0
    slippage_usd: float = 0.0


@dataclass(frozen=True)
class BinaryDecisionResult:
    posterior_probability: float
    expected_value_usd: float
    expected_value_after_costs_usd: float
    costs_usd: float
    positive_edge: bool


def expected_value(*, scenarios: list[OutcomeScenario], fees_usd: float = 0.0, slippage_usd: float = 0.0) -> ExpectedValueResult:
    if not scenarios:
        return ExpectedValueResult(expected_value_usd=0.0, expected_value_after_costs_usd=0.0, total_costs_usd=0.0)

    ev = sum(float(s.probability) * float(s.payoff_usd) for s in scenarios)
    costs = max(0.0, float(fees_usd)) + max(0.0, float(slippage_usd))
    return ExpectedValueResult(
        expected_value_usd=round(ev, 6),
        expected_value_after_costs_usd=round(ev - costs, 6),
        total_costs_usd=round(costs, 6),
    )


def evaluate_binary_decision(inputs: BinaryDecisionInput) -> BinaryDecisionResult:
    posterior = bayes_update(
        prior=inputs.prior_probability,
        likelihood_if_true=inputs.likelihood_if_true,
        likelihood_if_false=inputs.likelihood_if_false,
    )

    p = clamp_probability(posterior)
    q = 1.0 - p
    raw_ev = p * float(inputs.payoff_win_usd) + q * float(inputs.payoff_loss_usd)
    costs = max(0.0, float(inputs.fees_usd)) + max(0.0, float(inputs.slippage_usd))
    net_ev = raw_ev - costs
    return BinaryDecisionResult(
        posterior_probability=round(p, 6),
        expected_value_usd=round(raw_ev, 6),
        expected_value_after_costs_usd=round(net_ev, 6),
        costs_usd=round(costs, 6),
        positive_edge=(net_ev > 0),
    )
