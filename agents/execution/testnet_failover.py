from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agents.execution.execution_agent import ExchangeExecutionError, OrderRequest


@dataclass(slots=True)
class ExchangeFailoverExecutor:
    adapters: list[Any]
    max_attempts_per_adapter: int = 3

    def execute(self, order: OrderRequest) -> dict[str, Any]:
        if not self.adapters:
            raise ExchangeExecutionError("no adapters configured")

        errors: list[str] = []
        for adapter in self.adapters:
            for attempt in range(1, self.max_attempts_per_adapter + 1):
                try:
                    result = adapter.place_order(order)
                    result["attempt"] = attempt
                    return result
                except Exception as exc:  # noqa: BLE001
                    errors.append(f"{adapter.name}#{attempt}:{exc}")

        raise ExchangeExecutionError("all adapters failed: " + " | ".join(errors))

