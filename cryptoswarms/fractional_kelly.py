from __future__ import annotations


def kelly_fraction(*, win_probability: float, payoff_multiple: float) -> float:
    p = min(0.999, max(0.001, float(win_probability)))
    b = max(1e-6, float(payoff_multiple))
    q = 1.0 - p
    fraction = (p * b - q) / b
    return max(0.0, fraction)


def empirical_fractional_kelly(
    *,
    win_probability: float,
    payoff_multiple: float,
    uncertainty_cv: float,
    kelly_fraction_multiplier: float = 0.5,
    max_fraction: float = 0.25,
) -> float:
    raw = kelly_fraction(win_probability=win_probability, payoff_multiple=payoff_multiple)
    uncertainty_penalty = max(0.0, min(0.95, float(uncertainty_cv)))
    fraction = raw * max(0.0, min(1.0, float(kelly_fraction_multiplier))) * (1.0 - uncertainty_penalty)
    return round(max(0.0, min(float(max_fraction), fraction)), 6)


def position_size_from_bankroll(*, bankroll_usd: float, fraction: float) -> float:
    bankroll = max(0.0, float(bankroll_usd))
    f = max(0.0, min(1.0, float(fraction)))
    return round(bankroll * f, 6)
