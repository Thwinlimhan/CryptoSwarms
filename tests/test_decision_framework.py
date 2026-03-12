from datetime import datetime, timezone

from cryptoswarms.base_rate_registry import BaseRateProfile, BaseRateRegistry, default_base_rate_registry
from cryptoswarms.bayesian_update import bayes_update, sentiment_likelihoods, sequential_bayes_update
from cryptoswarms.decision_engine import BinaryDecisionInput, OutcomeScenario, evaluate_binary_decision, expected_value
from cryptoswarms.failure_ledger import FailureLedger
from cryptoswarms.fractional_kelly import empirical_fractional_kelly, kelly_fraction, position_size_from_bankroll


def test_base_rate_registry_empirical_bayes_prior_blends_observed_and_fallback():
    registry = BaseRateRegistry(
        profiles=[
            BaseRateProfile(
                key="s1",
                success_rate=0.7,
                sample_size=10,
                source="unit-test",
                updated_at=datetime(2026, 3, 8, tzinfo=timezone.utc),
            )
        ]
    )
    prior = registry.empirical_bayes_prior("s1", fallback=0.5, pseudo_count=10)
    assert 0.59 <= prior <= 0.61


def test_bayesian_update_and_sequential_updates():
    lt, lf = sentiment_likelihoods(0.8)
    post = bayes_update(prior=0.5, likelihood_if_true=lt, likelihood_if_false=lf)
    seq = sequential_bayes_update(prior=0.5, evidence=[(lt, lf), (0.6, 0.45)])
    assert post > 0.5
    assert seq > post


def test_expected_value_and_binary_decision_include_costs():
    ev = expected_value(
        scenarios=[OutcomeScenario(probability=0.6, payoff_usd=100.0), OutcomeScenario(probability=0.4, payoff_usd=-80.0)],
        fees_usd=3.0,
        slippage_usd=2.0,
    )
    assert ev.expected_value_usd == 28.0
    assert ev.expected_value_after_costs_usd == 23.0

    out = evaluate_binary_decision(
        BinaryDecisionInput(
            prior_probability=0.55,
            likelihood_if_true=0.65,
            likelihood_if_false=0.45,
            payoff_win_usd=100.0,
            payoff_loss_usd=-80.0,
            fees_usd=3.0,
            slippage_usd=2.0,
        )
    )
    assert out.posterior_probability > 0.55
    assert out.expected_value_after_costs_usd < out.expected_value_usd


def test_fractional_kelly_and_position_size():
    raw = kelly_fraction(win_probability=0.6, payoff_multiple=1.0)
    frac = empirical_fractional_kelly(
        win_probability=0.6,
        payoff_multiple=1.0,
        uncertainty_cv=0.35,
        kelly_fraction_multiplier=0.5,
        max_fraction=0.25,
    )
    size = position_size_from_bankroll(bankroll_usd=10000.0, fraction=frac)

    assert raw > frac
    assert 0.0 <= frac <= 0.25
    assert size >= 0.0


def test_failure_ledger_tracks_failure_rate_and_deprioritization():
    ledger = FailureLedger()
    for _ in range(7):
        ledger.record(key="alpha", passed=False)
    for _ in range(3):
        ledger.record(key="alpha", passed=True)

    rate = ledger.failure_rate(key="alpha", lookback_days=30)
    assert 0.69 <= rate <= 0.71
    assert ledger.should_deprioritize(key="alpha", lookback_days=30, threshold=0.6) is True


def test_default_base_rate_registry_contains_phase1_strategy():
    registry = default_base_rate_registry()
    rate = registry.get_rate("phase1-btc-breakout-15m", default=0.5)
    assert rate > 0.5
