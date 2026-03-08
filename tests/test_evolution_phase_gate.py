from cryptoswarms.evolution_phase_gate import EvolutionReadiness, letta_activation_allowed


def test_letta_activation_blocked_before_phase4_criteria():
    allowed, reason = letta_activation_allowed(EvolutionReadiness(live_strategies=2, paper_history_days=120, live_history_days=70))
    assert allowed is False
    assert "3 live" in reason


def test_letta_activation_allowed_when_criteria_met():
    allowed, reason = letta_activation_allowed(EvolutionReadiness(live_strategies=3, paper_history_days=120, live_history_days=60))
    assert allowed is True
    assert "phase 4" in reason
