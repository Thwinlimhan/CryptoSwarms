from fastapi import APIRouter, Query
from typing import Any
from api.dependencies import dag_bridge, decision_memory_dag, dashboard_repo
from agents.orchestration.decision_council import DecisionCouncil, CouncilConfig, CouncilInput
from cryptoswarms.dag_recall import DagWalker
from api.utils import compute_dag_memory_stats, build_lineage_summary

router = APIRouter(prefix="/api/decision", tags=["decision"])

@router.get("/debate-preview")
async def debate_preview(
    scorecard_eligible: bool = Query(default=True),
    institutional_gate_ok: bool = Query(default=True),
    attribution_ready: bool = Query(default=True),
    risk_halt_active: bool = Query(default=False),
    strategy_count_ok: bool = Query(default=True),
    expected_value_after_costs_usd: float = Query(default=12.5),
    posterior_probability: float = Query(default=0.64, ge=0.0, le=1.0),
    project_id: str = Query(default="default"),
) -> dict[str, Any]:
    council = DecisionCouncil(config=CouncilConfig(debate_rounds=2, max_retries=2, min_go_confidence=0.6), dag_bridge=dag_bridge)
    out = await council.decide(
        CouncilInput(
            strategy_id="phase1-btc-breakout-15m",
            project_id=project_id,
            scorecard_eligible=scorecard_eligible,
            institutional_gate_ok=institutional_gate_ok,
            attribution_ready=attribution_ready,
            risk_halt_active=risk_halt_active,
            strategy_count_ok=strategy_count_ok,
            expected_value_after_costs_usd=expected_value_after_costs_usd,
            posterior_probability=posterior_probability,
        )
    )
    return {
        "project_id": project_id,
        "decision": out.decision,
        "confidence": out.confidence,
        "dissent_ratio": out.dissent_ratio,
        "passed_governor": out.passed_governor,
        "reason": out.reason,
        "stages": out.stages,
        "aggregate": {
            "decision": out.aggregate.decision,
            "confidence": out.aggregate.confidence,
            "dissent_ratio": out.aggregate.dissent_ratio,
            "vote_count": out.aggregate.vote_count,
        },
        "rounds": [
            {
                "round": r.round_index,
                "dissent_solver_ids": r.dissent_solver_ids,
                "votes": [
                    {
                        "solver_id": v.solver_id,
                        "stance": v.stance,
                        "confidence": v.confidence,
                        "rationale": v.rationale,
                    }
                    for v in r.votes
                ],
            }
            for r in out.rounds
        ],
    }

@router.get("/dag-preview")
async def dag_preview(
    topic: str = Query(default="phase1-btc-breakout-15m"),
    lookback_hours: int = Query(default=72, ge=1, le=720),
    max_nodes: int = Query(default=8, ge=1, le=50),
    token_budget: int = Query(default=800, ge=100, le=4000),
    project_id: str = Query(default="default"),
) -> dict[str, Any]:
    walker = DagWalker(decision_memory_dag)
    recall = walker.recall(
        topic=dag_bridge.scoped_topic(project_id=project_id, strategy_id=topic),
        lookback_hours=lookback_hours,
        max_nodes=max_nodes,
        token_budget=token_budget,
    )
    return {
        "project_id": project_id,
        "topic": topic,
        "token_estimate": recall.token_estimate,
        "truncated": recall.truncated,
        "node_count": len(recall.nodes),
        "nodes": [
            {
                "node_id": node.node_id,
                "node_type": node.node_type,
                "topic": node.topic,
                "content": node.content,
                "created_at": node.created_at.isoformat(),
                "metadata": node.metadata,
            }
            for node in recall.nodes
        ],
    }

@router.get("/dag-stats")
async def dag_stats() -> dict[str, Any]:
    return compute_dag_memory_stats()

@router.get("/attribution-lineage")
async def attribution_lineage(
    strategy_id: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict[str, Any]:
    traces = await dashboard_repo.fetch_live_trade_traces(limit=limit, strategy_id=strategy_id)
    return {
        "summary": build_lineage_summary(traces=traces, strategy_id=strategy_id),
        "traces": traces,
    }
