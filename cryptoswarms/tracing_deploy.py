from __future__ import annotations

import os
import socket
from dataclasses import dataclass


@dataclass(frozen=True)
class TracingDeploymentStatus:
    langsmith_ready: bool
    deepflow_reachable: bool


def _tcp_check(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def evaluate_tracing_deployment(env: dict[str, str] | None = None) -> TracingDeploymentStatus:
    env = env or dict(os.environ)
    langsmith_ready = (
        env.get("LANGCHAIN_TRACING_V2", "").strip().lower() in {"1", "true", "yes"}
        and bool(env.get("LANGCHAIN_API_KEY", "").strip())
        and bool(env.get("LANGCHAIN_PROJECT", "").strip())
    )

    deepflow_host = env.get("DEEPFLOW_HOST", "localhost")
    deepflow_port = int(env.get("DEEPFLOW_PORT", "20035"))
    deepflow_reachable = _tcp_check(deepflow_host, deepflow_port)

    return TracingDeploymentStatus(
        langsmith_ready=langsmith_ready,
        deepflow_reachable=deepflow_reachable,
    )
