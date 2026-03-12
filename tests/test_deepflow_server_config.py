from pathlib import Path


def test_deepflow_server_yaml_exists_and_has_no_tabs():
    config_path = Path("infra/deepflow/server.yaml")
    assert config_path.exists(), "missing deepflow server yaml config"
    body = config_path.read_text(encoding="utf-8")
    assert "\t" not in body, "server yaml contains tab indentation"
    assert "controller-ips:" in body
