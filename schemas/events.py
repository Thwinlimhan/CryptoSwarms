from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    RESEARCH_SIGNAL = "research_signal"
    HYPOTHESIS = "hypothesis"
    VALIDATION_RESULT = "validation_result"
    EXECUTION_FILL = "execution_fill"
    RISK_HALT = "risk_halt"


class MarketSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class ValidationStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"


class HaltSeverity(str, Enum):
    WARNING = "warning"
    HARD_STOP = "hard_stop"


class ResearchSignalPayload(BaseModel):
    symbol: str
    timeframe: str
    signal_name: str
    confidence: float = Field(ge=0.0, le=1.0)
    source: str
    features: dict[str, float] = Field(default_factory=dict)


class HypothesisPayload(BaseModel):
    hypothesis_id: str
    thesis: str
    symbols: list[str]
    expected_horizon_hours: int = Field(gt=0)
    rationale: list[str] = Field(default_factory=list)


class ValidationResultPayload(BaseModel):
    run_id: str
    hypothesis_id: str
    status: ValidationStatus
    sharpe: float | None = None
    max_drawdown_pct: float | None = None
    notes: str | None = None


class ExecutionFillPayload(BaseModel):
    exchange: str
    order_id: str
    symbol: str
    side: MarketSide
    price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    fee: float = Field(ge=0)
    filled_at: datetime


class RiskHaltPayload(BaseModel):
    reason: str
    severity: HaltSeverity
    scope: str = Field(description="portfolio, strategy, or venue")
    triggered_by: str
    metrics: dict[str, float] = Field(default_factory=dict)


class EventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    producer: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)
    payload: dict[str, Any]
