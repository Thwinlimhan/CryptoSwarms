from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class LlmTraceEvent:
    time: datetime
    agent: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    metadata: dict[str, Any]


def langsmith_enabled(env: dict[str, str] | None = None) -> bool:
    environment = env or {}
    tracing_flag = environment.get("LANGCHAIN_TRACING_V2", "").strip().lower()
    api_key = environment.get("LANGCHAIN_API_KEY", "").strip()
    project = environment.get("LANGCHAIN_PROJECT", "").strip()
    return tracing_flag in {"1", "true", "yes"} and bool(api_key) and bool(project)


def emit_langsmith_trace(event: LlmTraceEvent, env: dict[str, str] | None = None) -> bool:
    environment = env or {}
    if not langsmith_enabled(environment):
        return False

    try:
        from langsmith import Client  # type: ignore
    except Exception:
        return False

    try:
        client = Client(api_key=environment.get("LANGCHAIN_API_KEY"))
        project = environment.get("LANGCHAIN_PROJECT")
        client.create_run(
            name=f"{event.agent}:{event.model}",
            run_type="llm",
            project_name=project,
            inputs={"metadata": event.metadata},
            outputs={
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "cost_usd": event.cost_usd,
            },
            start_time=event.time,
            end_time=datetime.now(timezone.utc),
        )
        return True
    except Exception:
        return False
