from pathlib import Path

from cryptoswarms.deepflow_preflight import evaluate_deepflow_preflight


def test_deepflow_preflight_ok_when_yaml_matches_env(tmp_path):
    config = tmp_path / "deepflow-agent.yaml"
    config.write_text(
        "controller-ips:\n  - 10.0.0.5\nvtap-group-id-request: g-prod\n",
        encoding="utf-8",
    )

    status = evaluate_deepflow_preflight(
        config_path=config,
        env={
            "DEEPFLOW_CONTROLLER_IP": "10.0.0.5",
            "DEEPFLOW_VTAP_GROUP_ID": "g-prod",
        },
    )

    assert status.ok is True
    assert status.errors == ()
    assert status.vtap_group_id == "g-prod"
    assert status.controller_ips == ("10.0.0.5",)


def test_deepflow_preflight_fails_on_missing_required_keys(tmp_path):
    config = tmp_path / "deepflow-agent.yaml"
    config.write_text("controller-ips:\n", encoding="utf-8")

    status = evaluate_deepflow_preflight(config_path=config)

    assert status.ok is False
    assert any("missing controller-ips" in e or "missing vtap-group-id-request" in e for e in status.errors)


def test_deepflow_preflight_fails_on_env_mismatch(tmp_path):
    config = tmp_path / "deepflow-agent.yaml"
    config.write_text(
        "controller-ips:\n  - 127.0.0.1\nvtap-group-id-request: g-local\n",
        encoding="utf-8",
    )

    status = evaluate_deepflow_preflight(
        config_path=config,
        env={
            "DEEPFLOW_CONTROLLER_IP": "10.1.1.7",
            "DEEPFLOW_VTAP_GROUP_ID": "g-prod",
        },
    )

    assert status.ok is False
    assert any("DEEPFLOW_CONTROLLER_IP" in e for e in status.errors)
    assert any("DEEPFLOW_VTAP_GROUP_ID" in e for e in status.errors)


def test_deepflow_preflight_errors_when_file_missing(tmp_path):
    missing = Path(tmp_path) / "none.yaml"
    status = evaluate_deepflow_preflight(config_path=missing)
    assert status.ok is False
    assert any("config file not found" in e for e in status.errors)
