from __future__ import annotations

from dataclasses import dataclass


ROUTING_POLICY: dict[str, str] = {
    "sentiment_score": "qwen3.5-4b-local",
    "code_first_draft": "qwen3.5-4b-local",
    "data_extraction": "qwen3.5-4b-local",
    "pattern_match": "qwen3.5-4b-local",
    "simple_qa": "qwen3.5-4b-local",
    "news_analysis": "fingpt-local",
    "strategy_review": "glm-5-openrouter",
    "risk_check": "glm-5-openrouter",
    "code_final_review": "glm-5-openrouter",
    "novel_hypothesis": "claude-sonnet-4-6",
    "system_improvement": "claude-sonnet-4-6",
    "daily_brief": "perplexity-computer",
    "reg_monitoring": "perplexity-computer",
}


@dataclass(frozen=True)
class RoutingDecision:
    task: str
    model: str


def route_task(task: str) -> RoutingDecision:
    model = ROUTING_POLICY.get(task, "qwen3.5-4b-local")
    return RoutingDecision(task=task, model=model)
