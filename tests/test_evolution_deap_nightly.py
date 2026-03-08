from agents.evolution.deap_nightly import NightlyOptimizer


def test_nightly_optimizer_returns_ranked_candidates():
    optimizer = NightlyOptimizer(
        score_fn=lambda p: 2.0 - abs(p.get("alpha", 1.0) - 1.2) - p.get("slippage", 0.0),
        base_params={"alpha": 1.0, "beta": 2.0},
        slippage=0.004,
    )

    candidates = optimizer.run(generations=5, step=0.1)

    assert len(candidates) >= 1
    assert candidates[0].score >= candidates[-1].score
    assert "slippage" not in candidates[0].params
