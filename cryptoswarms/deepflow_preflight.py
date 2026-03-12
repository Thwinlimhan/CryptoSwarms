from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping
import os


@dataclass(frozen=True)
class DeepflowPreflightStatus:
    ok: bool
    config_path: str
    controller_ips: tuple[str, ...]
    vtap_group_id: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _strip_quotes(value: str) -> str:
    raw = value.strip()
    if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
        return raw[1:-1].strip()
    return raw


def _parse_deepflow_yaml(text: str) -> tuple[tuple[str, ...], str]:
    controller_ips: list[str] = []
    vtap_group_id = ""
    in_controller_list = False

    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue

        stripped = line.strip()
        if stripped.startswith("controller-ips:"):
            in_controller_list = True
            continue

        if stripped.startswith("vtap-group-id-request:"):
            in_controller_list = False
            value = stripped.split(":", 1)[1].strip()
            vtap_group_id = _strip_quotes(value)
            continue

        if in_controller_list and stripped.startswith("-"):
            controller_ips.append(_strip_quotes(stripped[1:].strip()))
            continue

        if in_controller_list and not stripped.startswith("-"):
            in_controller_list = False

    return tuple(ip for ip in controller_ips if ip), vtap_group_id


def evaluate_deepflow_preflight(
    *,
    config_path: str | Path = "infra/deepflow/deepflow-agent.yaml",
    env: Mapping[str, str] | None = None,
) -> DeepflowPreflightStatus:
    path = Path(config_path)
    env_map = dict(os.environ) if env is None else dict(env)
    errors: list[str] = []
    warnings: list[str] = []

    if not path.exists():
        errors.append(f"config file not found: {path}")
        return DeepflowPreflightStatus(
            ok=False,
            config_path=str(path),
            controller_ips=(),
            vtap_group_id="",
            errors=tuple(errors),
            warnings=tuple(warnings),
        )

    body = path.read_text(encoding="utf-8")
    controller_ips, vtap_group_id = _parse_deepflow_yaml(body)

    if not controller_ips:
        errors.append("missing controller-ips list in deepflow-agent yaml")

    if not vtap_group_id:
        errors.append("missing vtap-group-id-request in deepflow-agent yaml")

    expected_controller = env_map.get("DEEPFLOW_CONTROLLER_IP", "").strip()
    if expected_controller and expected_controller not in controller_ips:
        errors.append(
            "DEEPFLOW_CONTROLLER_IP is set but not present in controller-ips "
            f"(expected={expected_controller})"
        )

    expected_group = env_map.get("DEEPFLOW_VTAP_GROUP_ID", "").strip()
    if expected_group and expected_group != vtap_group_id:
        errors.append(
            "DEEPFLOW_VTAP_GROUP_ID is set but does not match vtap-group-id-request "
            f"(expected={expected_group}, actual={vtap_group_id or '<empty>'})"
        )

    if vtap_group_id.startswith("g-") and len(vtap_group_id) < 5:
        warnings.append("vtap-group-id-request looks too short")

    if any(ip in {"127.0.0.1", "localhost"} for ip in controller_ips):
        warnings.append("controller-ips uses localhost loopback; set real controller IP for non-local deployments")

    return DeepflowPreflightStatus(
        ok=not errors,
        config_path=str(path),
        controller_ips=controller_ips,
        vtap_group_id=vtap_group_id,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
