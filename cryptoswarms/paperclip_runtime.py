from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


class CostProvider(Protocol):
    def current_spend_usd(self) -> float: ...


class AuditSink(Protocol):
    def publish(self, channel: str, payload: dict[str, object]) -> None: ...


@dataclass(frozen=True)
class PaperclipDecision:
    allowed: bool
    reason: str
    projected_spend_usd: float


@dataclass(slots=True)
class PaperclipRuntimeGuard:
    cost_provider: CostProvider
    audit_sink: AuditSink
    daily_budget_usd: float = 10.0

    def check(self, *, estimated_increment_usd: float, action: str, actor: str) -> PaperclipDecision:
        current = max(0.0, float(self.cost_provider.current_spend_usd()))
        projected = current + max(0.0, float(estimated_increment_usd))
        allowed = projected <= self.daily_budget_usd

        decision = PaperclipDecision(
            allowed=allowed,
            reason="within_budget" if allowed else "paperclip_budget_exceeded",
            projected_spend_usd=round(projected, 6),
        )

        self.audit_sink.publish(
            "governance:paperclip",
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "action": action,
                "actor": actor,
                "allowed": decision.allowed,
                "reason": decision.reason,
                "projected_spend_usd": decision.projected_spend_usd,
                "daily_budget_usd": self.daily_budget_usd,
            },
        )
        return decision
