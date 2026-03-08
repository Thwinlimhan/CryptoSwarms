from cryptoswarms.routing_policy import route_task


def test_route_task_uses_policy_and_fallback():
    assert route_task("risk_check").model == "glm-5-openrouter"
    assert route_task("unknown_task").model == "qwen3.5-4b-local"
