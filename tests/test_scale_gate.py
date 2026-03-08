from cryptoswarms.scale_gate import ScaleReadiness, evaluate_scale_readiness


def test_scale_readiness_blocks_until_prerequisites_met():
    d = evaluate_scale_readiness(
        ScaleReadiness(
            first_strategy_stable=False,
            execution_reliability_slo_met=False,
            core_alpha_stable=False,
        )
    )

    assert d.allow_second_strategy is False
    assert d.allow_second_venue is False
    assert d.allow_polymarket_modifier is False
    assert len(d.reasons) == 3


def test_scale_readiness_allows_when_ready():
    d = evaluate_scale_readiness(
        ScaleReadiness(
            first_strategy_stable=True,
            execution_reliability_slo_met=True,
            core_alpha_stable=True,
        )
    )

    assert d.allow_second_strategy is True
    assert d.allow_second_venue is True
    assert d.allow_polymarket_modifier is True
