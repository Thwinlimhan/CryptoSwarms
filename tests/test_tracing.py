from datetime import datetime, timezone

from cryptoswarms.tracing import LlmTraceEvent, emit_langsmith_trace, langsmith_enabled


def test_langsmith_enabled_requires_all_flags():
    assert langsmith_enabled({"LANGCHAIN_TRACING_V2": "true", "LANGCHAIN_API_KEY": "k", "LANGCHAIN_PROJECT": "p"}) is True
    assert langsmith_enabled({"LANGCHAIN_TRACING_V2": "false", "LANGCHAIN_API_KEY": "k", "LANGCHAIN_PROJECT": "p"}) is False


def test_emit_langsmith_trace_returns_false_when_not_enabled():
    event = LlmTraceEvent(
        time=datetime.now(timezone.utc),
        agent="scanner",
        model="qwen",
        prompt_tokens=10,
        completion_tokens=20,
        cost_usd=0.01,
        metadata={"task": "score"},
    )
    assert emit_langsmith_trace(event, env={}) is False
