from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class GateStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"


@dataclass(slots=True)
class StrategyCandidate:
    strategy_id: str
    module_path: str
    class_name: str
    params: dict[str, float]
    market_data: Any
    benchmark_returns: list[float]


@dataclass(slots=True)
class GateResult:
    gate_number: int
    gate_name: str
    status: GateStatus
    score: float | None
    details: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(slots=True)
class ValidationSummary:
    strategy_id: str
    run_id: str
    gate_results: list[GateResult]

    @property
    def passed(self) -> bool:
        return bool(self.gate_results) and all(g.status == GateStatus.PASS for g in self.gate_results)
