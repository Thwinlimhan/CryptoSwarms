from cryptoswarms.expansion_policy import ExpansionContext, evaluate_expansion


def test_expansion_policy_blocks_when_prerequisites_missing():
    result = evaluate_expansion(
        ExpansionContext(
            first_strategy_stable=False,
            execution_reliability_met=False,
            proven_bottleneck=False,
            sufficient_history_for_evolution=False,
        )
    )

    assert result.allow_second_strategy is False
    assert result.allow_second_exchange is False
    assert result.allow_new_agents is False
    assert result.allow_evolution_activation is False
    assert len(result.reasons) == 4
