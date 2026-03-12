from agents.orchestration.decision_council import CouncilConfig, CouncilInput, DecisionCouncil


def test_decision_council_go_when_all_gates_pass_and_confident():
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=2, max_retries=2, min_go_confidence=0.55))
    out = council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            scorecard_eligible=True,
            institutional_gate_ok=True,
            attribution_ready=True,
            risk_halt_active=False,
            strategy_count_ok=True,
            expected_value_after_costs_usd=15.0,
            posterior_probability=0.68,
        )
    )

    assert out.decision == "go"
    assert out.passed_governor is True
    assert out.aggregate.vote_count == 3


def test_decision_council_hold_when_governor_gate_fails():
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=2, max_retries=2, min_go_confidence=0.55))
    out = council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            scorecard_eligible=True,
            institutional_gate_ok=True,
            attribution_ready=True,
            risk_halt_active=True,
            strategy_count_ok=True,
            expected_value_after_costs_usd=20.0,
            posterior_probability=0.72,
        )
    )

    assert out.decision == "hold"
    assert out.passed_governor is False
    assert "risk halt" in out.reason


def test_decision_council_blocks_unknown_project_scope():
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=1, max_retries=1, min_go_confidence=0.55))
    out = council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            project_id="unknown",
            scorecard_eligible=True,
            institutional_gate_ok=True,
            attribution_ready=True,
            risk_halt_active=False,
            strategy_count_ok=True,
            expected_value_after_costs_usd=15.0,
            posterior_probability=0.68,
        )
    )

    assert out.decision == "hold"
    assert "unknown project scope" in out.reason


def test_decision_council_blocks_disallowed_secret_request():
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=1, max_retries=1, min_go_confidence=0.55))
    out = council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            project_id="default",
            requested_secret_envs=("MAIN_WALLET_SECRET",),
            scorecard_eligible=True,
            institutional_gate_ok=True,
            attribution_ready=True,
            risk_halt_active=False,
            strategy_count_ok=True,
            expected_value_after_costs_usd=15.0,
            posterior_probability=0.68,
        )
    )

    assert out.decision == "hold"
    assert "secret env not allowed" in out.reason
