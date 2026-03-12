from __future__ import annotations

import json
import sys

from cryptoswarms.deepflow_preflight import evaluate_deepflow_preflight


def main() -> None:
    status = evaluate_deepflow_preflight()
    payload = {
        "ok": status.ok,
        "config_path": status.config_path,
        "controller_ips": list(status.controller_ips),
        "vtap_group_id": status.vtap_group_id,
        "errors": list(status.errors),
        "warnings": list(status.warnings),
    }
    print(json.dumps(payload, indent=2))
    if not status.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
