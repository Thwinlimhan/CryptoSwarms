# Decision Council Orchestration

This layer adds deterministic multi-agent orchestration for high-stakes promotion/live-go decisions.

## Components

- `agents/orchestration/decision_council.py`
  - State-machine style flow with stages:
    - input guardrail
    - DAG recall (bounded context fetch)
    - tool guardrail
    - debate rounds with retries
    - output guardrail
    - governor final gate
    - decision checkpoint write to DAG

- `agents/orchestration/debate_protocol.py`
  - AutoGen-style debate primitives:
    - independent solver votes
    - cross-critique rounds
    - weighted aggregation
    - dissent tracking

- `agents/orchestration/dag_memory_bridge.py`
  - Connects Decision Council to DAG memory.
  - Reads relevant nodes pre-decision and persists decision checkpoints post-decision.

## DAG memory

- `cryptoswarms/memory_dag.py`
  - Directed acyclic graph store for rolling summary/checkpoint nodes.
  - Enforces acyclic edge insertion.

- `cryptoswarms/dag_recall.py`
  - Bounded DAG walking by topic/time/max nodes/token budget.

## Solver roles

- `research_solver`: posterior + EV stance
- `risk_solver`: scorecard + institutional gate stance
- `execution_solver`: attribution + strategy-count readiness stance

## Final governor constraints

`go` is blocked unless all are true:
- scorecard eligible
- institutional gate pass
- attribution ready
- no risk halt
- strategy-count governance pass
- EV after costs > 0
- debate confidence threshold pass

## API preview

- `GET /api/decision/debate-preview`
  - Returns decision, confidence, dissent, stage trace, round votes, DAG context node ids, and checkpoint node id.

- `GET /api/decision/dag-preview`
  - Returns bounded DAG recall output by topic.

## Related controls

- `agents/research/security_controls.py`
  - input/tool/output guardrails
  - credential filtering
- `agents/research/skill_hub.py`
  - skill lifecycle: create/patch/edit/submit/approve + audit trail
- `agents/research/progressive_loader.py`
  - token-efficient progressive loading

## Subagent delegation

`ResearchFactory` fetches connector results in parallel using a thread pool and then deduplicates before hypothesis generation.
