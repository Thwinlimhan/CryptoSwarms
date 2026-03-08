"""Canonical Redis stream names used by all agents."""

RESEARCH_SIGNALS = "stream:research:signals"
HYPOTHESES = "stream:research:hypotheses"
VALIDATION_RESULTS = "stream:validation:results"
EXECUTION_FILLS = "stream:execution:fills"
RISK_HALTS = "stream:risk:halts"
AGENT_HEARTBEATS = "stream:agent:heartbeats"


def dead_letter(stream_name: str) -> str:
    return f"{stream_name}:dlq"
