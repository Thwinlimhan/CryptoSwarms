from agents.orchestration.runtime_middleware import RuntimeOrchestrator, StageFlagMiddleware


def test_runtime_orchestrator_success_path():
    orchestrator = RuntimeOrchestrator(
        [
            StageFlagMiddleware("scope", required_flag="scope_ok"),
            StageFlagMiddleware("input", required_flag="input_ok"),
            StageFlagMiddleware("governor", required_flag="governor_ok"),
        ],
        max_retries=1,
    )

    out = orchestrator.execute({"scope_ok": True, "input_ok": True, "governor_ok": True})
    assert out.ok is True
    assert "scope" in out.stages
    assert "governor" in out.stages


def test_runtime_orchestrator_reports_failure_and_retries():
    orchestrator = RuntimeOrchestrator(
        [StageFlagMiddleware("scope", required_flag="scope_ok")],
        max_retries=1,
    )

    out = orchestrator.execute({"scope_ok": False})
    assert out.ok is False
    assert out.retries["scope"] >= 1
    assert out.checkpoints["scope"]["ok"] is False

