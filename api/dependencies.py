"""Shared dependencies and state for the FastAPI application."""

import os
from pathlib import Path
from cryptoswarms.agent_runner import AgentRunner
from api.dashboard_repository import DashboardRepository
from agents.orchestration.dag_memory_bridge import DagMemoryBridge
from agents.orchestration.runtime_middleware import default_runtime_orchestrator
from agents.orchestration.subagent_executor import SubagentExecutor
from cryptoswarms.memory_dag import MemoryDag
from api.settings import settings

REGISTERED_AGENTS = ["market_scanner", "validation_pipeline", "risk_monitor"]
DAG_PATH = Path(os.getenv("DECISION_DAG_PATH", "data/agent_memory_dag.json"))

def _timescale_dsn_str() -> str:
    return (
        f"postgresql://{settings.timescaledb_user}:{settings.timescaledb_password}"
        f"@{settings.timescaledb_host}:{settings.timescaledb_port}/{settings.timescaledb_db}"
    )

agent_runner = AgentRunner(
    timescale_dsn=_timescale_dsn_str(),
    redis_url=settings.redis_url,
)

decision_memory_dag = MemoryDag()
dag_bridge = DagMemoryBridge(decision_memory_dag)
runtime_orchestrator = default_runtime_orchestrator()
subagent_executor = SubagentExecutor(max_parallelism=3, timeout_seconds=8.0)
dashboard_repo = DashboardRepository(REGISTERED_AGENTS)

def load_decision_dag() -> None:
    global decision_memory_dag, dag_bridge
    decision_memory_dag = MemoryDag.load_json(DAG_PATH)
    dag_bridge = DagMemoryBridge(decision_memory_dag)

def save_decision_dag() -> None:
    from cryptoswarms.dag_summarizer import DagSummarizationConfig, maybe_summarize_topics
    topics = {node.topic for node in decision_memory_dag.nodes() if node.topic}
    maybe_summarize_topics(
        decision_memory_dag,
        topics=topics,
        config=DagSummarizationConfig(max_nodes_per_topic=40, trigger_token_budget=1800, summary_max_chars=700),
    )
    decision_memory_dag.save_json(DAG_PATH)
