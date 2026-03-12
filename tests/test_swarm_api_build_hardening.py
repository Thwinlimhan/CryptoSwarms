from pathlib import Path


def test_agents_dockerfile_has_apt_network_resilience_settings():
    body = Path("agents/Dockerfile").read_text(encoding="utf-8")
    assert "Acquire::Retries" in body
    assert "Acquire::ForceIPv4" in body
    assert "Acquire::http::Timeout" in body
    assert "Acquire::https::Timeout" in body


def test_swarm_api_build_retry_script_exists():
    body = Path("scripts/run_swarm_api_build.ps1").read_text(encoding="utf-8")
    assert "docker compose build --progress=plain swarm-api" in body
    assert "$MaxAttempts" in body
