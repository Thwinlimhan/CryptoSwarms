from __future__ import annotations


def clamp_probability(value: float) -> float:
    return min(0.999, max(0.001, float(value)))


def bayes_update(*, prior: float, likelihood_if_true: float, likelihood_if_false: float) -> float:
    p = clamp_probability(prior)
    lt = clamp_probability(likelihood_if_true)
    lf = clamp_probability(likelihood_if_false)

    numerator = lt * p
    denominator = numerator + lf * (1.0 - p)
    if denominator <= 0:
        return p
    return clamp_probability(numerator / denominator)


def sentiment_likelihoods(sentiment_score: float) -> tuple[float, float]:
    score = max(-1.0, min(1.0, float(sentiment_score)))
    strength = abs(score)
    if score >= 0:
        return 0.50 + 0.35 * strength, 0.50 - 0.20 * strength
    return 0.50 - 0.20 * strength, 0.50 + 0.35 * strength


def sequential_bayes_update(*, prior: float, evidence: list[tuple[float, float]]) -> float:
    post = clamp_probability(prior)
    for lt, lf in evidence:
        post = bayes_update(prior=post, likelihood_if_true=lt, likelihood_if_false=lf)
    return post
