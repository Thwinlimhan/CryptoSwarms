from pathlib import Path


def test_deepflow_agent_yaml_exists_and_has_required_keys():
    config_path = Path("infra/deepflow/deepflow-agent.yaml")
    assert config_path.exists(), "missing deepflow agent yaml config"
    body = config_path.read_text(encoding="utf-8")
    assert "controller-ips:" in body
    assert "vtap-group-id-request:" in body


def test_compose_mounts_deepflow_agent_yaml():
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    assert "deepflow-server:" in compose
    assert "deepflow-agent:" in compose
    assert "profiles: [\"observability\"]" in compose
    assert "./infra/deepflow/deepflow-agent.yaml:/etc/deepflow-agent/deepflow-agent.yaml:ro" in compose
