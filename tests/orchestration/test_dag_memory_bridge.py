from agents.orchestration.dag_memory_bridge import DagMemoryBridge
from agents.orchestration.decision_council import CouncilConfig, CouncilInput, DecisionCouncil
from cryptoswarms.memory_dag import MemoryDag


def test_decision_council_writes_checkpoint_node_when_dag_enabled():
    dag = MemoryDag()
    bridge = DagMemoryBridge(dag)
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=1, max_retries=1, min_go_confidence=0.55), dag_bridge=bridge)

    out = council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            scorecard_eligible=True,
            institutional_gate_ok=True,
            attribution_ready=True,
            risk_halt_active=False,
            strategy_count_ok=True,
            expected_value_after_costs_usd=10.0,
            posterior_probability=0.7,
        )
    )

    assert out.decision_checkpoint_node_id is not None
    node = dag.get_node(out.decision_checkpoint_node_id)
    assert node is not None
    assert node.node_type == "decision_checkpoint"
