from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Protocol

from .models import ValidationSummary


class ExecutionQueue(Protocol):
    def xadd(self, stream: str, fields: dict[str, str]) -> str: ...


def emit_validation_event(queue: ExecutionQueue, summary: ValidationSummary, stream_name: str = "execution.validation.events") -> str:
    payload = {
        "run_id": summary.run_id,
        "strategy_id": summary.strategy_id,
        "status": "pass" if summary.passed else "fail",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_results": [
            {
                "gate_number": gate.gate_number,
                "gate_name": gate.gate_name,
                "status": gate.status.value,
                "score": gate.score,
                "details": gate.details,
            }
            for gate in summary.gate_results
        ],
    }
    return queue.xadd(stream_name, {"payload": json.dumps(payload)})
