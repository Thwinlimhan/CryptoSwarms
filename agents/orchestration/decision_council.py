from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from typing import Protocol, runtime_checkable

from agents.orchestration.dag_memory_bridge import DagMemoryBridge
from agents.orchestration.debate_protocol import DebateAggregate, DebateRound, DebateVote, aggregate_weighted, run_cross_critique
from agents.orchestration.delegation_policy import DelegationPolicy, DelegationRequest
from agents.orchestration.mcp_registry import MCPRegistry, default_mcp_registry
from agents.orchestration.project_scope import ProjectScopeManager, default_project_scope_manager
from agents.research.security_controls import GuardrailResult, input_guardrail, output_guardrail, tool_guardrail
from agents.orchestration.skill_agent import SkillAgent
import asyncer


@dataclass(frozen=True)
class CouncilInput:
    strategy_id: str
    scorecard_eligible: bool
    institutional_gate_ok: bool
    attribution_ready: bool
    risk_halt_active: bool
    strategy_count_ok: bool
    expected_value_after_costs_usd: float
    posterior_probability: float
    project_id: str = "default"
    requested_secret_envs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CouncilConfig:
    debate_rounds: int = 2
    max_retries: int = 2
    min_go_confidence: float = 0.6
    allow_tools: tuple[str, ...] = ("read_metrics", "score_decision", "emit_report")
    mcp_max_risk_tier: str = "medium"
    use_hyper_skills: bool = False


@dataclass(frozen=True)
class CouncilDecision:
    decision: str
    confidence: float
    dissent_ratio: float
    passed_governor: bool
    reason: str
    stages: list[str]
    rounds: list[DebateRound]
    aggregate: DebateAggregate
    guardrails: dict[str, GuardrailResult]
    dag_context_node_ids: list[str]
    decision_checkpoint_node_id: str | None


@runtime_checkable
class DebateSolver(Protocol):
    solver_id: str

    async def vote(self, payload: CouncilInput) -> DebateVote:
        ...


@dataclass(frozen=True)
class ProbabilitySolver:
    """The Probability Architect (Phase 11 soul)"""
    solver_id: str = "probability_architect"

    async def vote(self, payload: CouncilInput) -> DebateVote:
        ev_ok = payload.expected_value_after_costs_usd > 5.0  # Min $5 EV hurdle
        post_ok = payload.posterior_probability >= 0.58
        
        stance = "go" if ev_ok and post_ok else "hold"
        # Confidence is anchored to the posterior but tempered by EV
        confidence = min(0.92, payload.posterior_probability)
        
        rationale = f"EV=${payload.expected_value_after_costs_usd:.2f}, post={payload.posterior_probability:.4f}"
        return DebateVote(self.solver_id, stance, confidence, rationale)


@dataclass(frozen=True)
class MicrostructureSolver:
    """The Microstructure Oracle (Phase 12 soul)"""
    solver_id: str = "microstructure_oracle"

    async def vote(self, payload: CouncilInput) -> DebateVote:
        # Heavily weighted toward scorecard and institutional gates (positioning)
        stance = "go" if payload.scorecard_eligible and payload.institutional_gate_ok else "hold"
        confidence = 0.82 if stance == "go" else 0.88
        return DebateVote(self.solver_id, stance, confidence, "market positioning + sig check")


@dataclass(frozen=True)
class CalibrationSolver:
    """The Calibration Governor (Phase 13 soul)"""
    solver_id: str = "calibration_governor"

    async def vote(self, payload: CouncilInput) -> DebateVote:
        # Aggregates attribution and readiness status
        ready = payload.attribution_ready and payload.strategy_count_ok
        stance = "go" if ready and not payload.risk_halt_active else "hold"
        confidence = 0.85 if stance == "go" else 0.95
        return DebateVote(self.solver_id, stance, confidence, "meta-calibration + readiness")


class SkillSolver:
    """A solver that delegates to a HyperSpace Skill.md agent."""
    def __init__(self, skill_name: str):
        self.agent = SkillAgent(skill_name)
        self.solver_id = skill_name

    async def vote(self, payload: CouncilInput) -> DebateVote:
        # Convert dataclass to dict for SkillAgent
        data = {
            "strategy_id": payload.strategy_id,
            "scorecard_eligible": payload.scorecard_eligible,
            "institutional_gate_ok": payload.institutional_gate_ok,
            "attribution_ready": payload.attribution_ready,
            "risk_halt_active": payload.risk_halt_active,
            "strategy_count_ok": payload.strategy_count_ok,
            "expected_value_after_costs_usd": payload.expected_value_after_costs_usd,
            "posterior_probability": payload.posterior_probability,
            "project_id": payload.project_id
        }
        res = await self.agent.execute(data)
        return DebateVote(
            solver_id=res.get("solver_id", self.solver_id),
            stance=res.get("stance", "hold"),
            confidence=float(res.get("confidence", 0.0)),
            rationale=res.get("rationale", "skill execution")
        )


class DecisionCouncil:
    def __init__(
        self,
        *,
        solvers: list[DebateSolver] | None = None,
        config: CouncilConfig = CouncilConfig(),
        dag_bridge: DagMemoryBridge | None = None,
        project_scope_manager: ProjectScopeManager | None = None,
        mcp_registry: MCPRegistry | None = None,
        delegation_policy: DelegationPolicy | None = None,
    ) -> None:
        if solvers:
            self.solvers = solvers
        elif config.use_hyper_skills:
            self.solvers = [
                SkillSolver("probability_architect"),
                SkillSolver("microstructure_oracle"),
                SkillSolver("calibration_governor")
            ]
        else:
            self.solvers = [ProbabilitySolver(), MicrostructureSolver(), CalibrationSolver()]
            
        self.config = config
        self.dag_bridge = dag_bridge
        self.project_scope_manager = project_scope_manager or default_project_scope_manager()
        self.mcp_registry = mcp_registry or default_mcp_registry()
        self.delegation_policy = delegation_policy or DelegationPolicy()

    async def decide(self, payload: CouncilInput) -> CouncilDecision:
        stages: list[str] = []
        dag_context_ids: list[str] = []

        scope_guard = self.project_scope_manager.authorize_strategy(
            project_id=payload.project_id,
            strategy_id=payload.strategy_id,
        )
        stages.append("project_scope_strategy")
        if not scope_guard.allowed:
            blocked = self._blocked_decision(
                "hold",
                scope_guard.reason,
                stages,
                GuardrailResult(allowed=False, reason=scope_guard.reason),
                dag_context_ids,
            )
            return self._persist_checkpoint(payload=payload, decision=blocked)

        secret_guard = self.project_scope_manager.authorize_secret_envs(
            project_id=payload.project_id,
            requested_envs=payload.requested_secret_envs,
        )
        stages.append("project_scope_secrets")
        if not secret_guard.allowed:
            blocked = self._blocked_decision(
                "hold",
                secret_guard.reason,
                stages,
                GuardrailResult(allowed=False, reason=secret_guard.reason),
                dag_context_ids,
            )
            return self._persist_checkpoint(payload=payload, decision=blocked)

        in_guard = input_guardrail(
            text=f"{payload.project_id}:{payload.strategy_id}:{payload.posterior_probability}:{payload.expected_value_after_costs_usd}",
            max_chars=300,
            banned_patterns=("rm -rf", "DROP TABLE", "DELETE FROM"),
        )
        stages.append("input_guardrail")
        if not in_guard.allowed:
            blocked = self._blocked_decision("hold", "input guardrail blocked", stages, in_guard, dag_context_ids)
            return self._persist_checkpoint(payload=payload, decision=blocked)

        if self.dag_bridge is not None:
            recall = self.dag_bridge.recall_for_decision(payload)
            dag_context_ids = [node.node_id for node in recall.nodes]
            stages.append("dag_recall")

        mcp_auth = self.mcp_registry.authorize(
            tool_id="score_decision",
            max_risk_tier=self.config.mcp_max_risk_tier,
            approval_granted=False,
        )
        stages.append("mcp_registry_guard")
        if not mcp_auth.allowed:
            blocked = self._blocked_decision(
                "hold",
                mcp_auth.reason,
                stages,
                in_guard,
                dag_context_ids,
            )
            return self._persist_checkpoint(payload=payload, decision=blocked)

        tool_guard = tool_guardrail(action="score_decision", allowed_actions=self.config.allow_tools, requires_approval=False)
        stages.append("tool_guardrail")
        if not tool_guard.allowed:
            blocked = self._blocked_decision("hold", "tool guardrail blocked", stages, in_guard, dag_context_ids, tool_guard)
            return self._persist_checkpoint(payload=payload, decision=blocked)

        delegation = self.delegation_policy.authorize(
            request=DelegationRequest(
                stage="debate",
                task_type="promotion_decision",
                project_id=payload.project_id,
                strategy_id=payload.strategy_id,
            ),
            scorecard_eligible=payload.scorecard_eligible,
            institutional_gate_ok=payload.institutional_gate_ok,
            attribution_ready=payload.attribution_ready,
            risk_halt_active=payload.risk_halt_active,
        )
        stages.append("a2a_delegation_guard")
        if not delegation.allowed:
            blocked = self._blocked_decision(
                "hold",
                delegation.reason,
                stages,
                in_guard,
                dag_context_ids,
                tool_guard,
            )
            return self._persist_checkpoint(payload=payload, decision=blocked)

        rounds: list[DebateRound] = []
        aggregate = DebateAggregate(decision="hold", confidence=0.0, dissent_ratio=0.0, vote_count=0)

        attempts = 0
        while attempts < self.config.max_retries:
            attempts += 1
            stages.append(f"debate_attempt_{attempts}")
            initial_votes = [solver.vote(payload) for solver in self.solvers]
            rounds = run_cross_critique(votes=initial_votes, rounds=self.config.debate_rounds)
            aggregate = aggregate_weighted(rounds[-1].votes if rounds else initial_votes)
            if aggregate.confidence >= self.config.min_go_confidence or aggregate.decision == "hold":
                break

        out_guard = output_guardrail(
            payload={
                "decision": aggregate.decision,
                "confidence": aggregate.confidence,
                "dissent_ratio": aggregate.dissent_ratio,
            },
            required_keys=("decision", "confidence", "dissent_ratio"),
        )
        stages.append("output_guardrail")
        if not out_guard.allowed:
            blocked = self._blocked_decision(
                "hold", "output guardrail blocked", stages, in_guard, dag_context_ids, tool_guard, out_guard
            )
            return self._persist_checkpoint(payload=payload, decision=blocked)

        passed_governor, governor_reason = self._governor_gate(payload=payload, aggregate=aggregate)
        stages.append("governor_gate")
        decision = "go" if passed_governor and aggregate.decision == "go" else "hold"
        reason = "governor passed" if decision == "go" else governor_reason

        out = CouncilDecision(
            decision=decision,
            confidence=aggregate.confidence,
            dissent_ratio=aggregate.dissent_ratio,
            passed_governor=passed_governor,
            reason=reason,
            stages=stages,
            rounds=rounds,
            aggregate=aggregate,
            guardrails={
                "input": in_guard,
                "tool": tool_guard,
                "output": out_guard,
            },
            dag_context_node_ids=dag_context_ids,
            decision_checkpoint_node_id=None,
        )
        return self._persist_checkpoint(payload=payload, decision=out)

    def _governor_gate(self, *, payload: CouncilInput, aggregate: DebateAggregate) -> tuple[bool, str]:
        if payload.risk_halt_active:
            return False, "risk halt active"
        if not payload.scorecard_eligible:
            return False, "scorecard not eligible"
        if not payload.institutional_gate_ok:
            return False, "institutional gate failed"
        if not payload.attribution_ready:
            return False, "attribution not ready"
        if not payload.strategy_count_ok:
            return False, "strategy count governance failed"
        if payload.expected_value_after_costs_usd <= 0:
            return False, "non-positive expected value"
        if aggregate.confidence < self.config.min_go_confidence:
            return False, "debate confidence below threshold"
        return True, "passed"

    def _persist_checkpoint(self, *, payload: CouncilInput, decision: CouncilDecision) -> CouncilDecision:
        if self.dag_bridge is None:
            return decision
        checkpoint_id = self.dag_bridge.write_decision_checkpoint(payload=payload, decision=decision)
        return CouncilDecision(
            decision=decision.decision,
            confidence=decision.confidence,
            dissent_ratio=decision.dissent_ratio,
            passed_governor=decision.passed_governor,
            reason=decision.reason,
            stages=decision.stages,
            rounds=decision.rounds,
            aggregate=decision.aggregate,
            guardrails=decision.guardrails,
            dag_context_node_ids=decision.dag_context_node_ids,
            decision_checkpoint_node_id=checkpoint_id,
        )

    def _blocked_decision(
        self,
        decision: str,
        reason: str,
        stages: list[str],
        in_guard: GuardrailResult,
        dag_context_ids: list[str],
        tool_guard: GuardrailResult | None = None,
        out_guard: GuardrailResult | None = None,
    ) -> CouncilDecision:
        empty = DebateAggregate(decision=decision, confidence=0.0, dissent_ratio=0.0, vote_count=0)
        return CouncilDecision(
            decision=decision,
            confidence=0.0,
            dissent_ratio=0.0,
            passed_governor=False,
            reason=reason,
            stages=stages,
            rounds=[],
            aggregate=empty,
            guardrails={
                "input": in_guard,
                "tool": tool_guard or GuardrailResult(allowed=False, reason="not-run"),
                "output": out_guard or GuardrailResult(allowed=False, reason="not-run"),
            },
            dag_context_node_ids=dag_context_ids,
            decision_checkpoint_node_id=None,
        )
