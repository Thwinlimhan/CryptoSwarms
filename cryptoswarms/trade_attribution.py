from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class TradeAttribution:
    hypothesis_id: str
    optimizer_run_id: str
    optimizer_candidate_id: str
    research_source: str
    strategy_id: str
    attribution_version: str = "v1"


class TradeAttributionError(ValueError):
    """Raised when mandatory trade attribution fields are missing or invalid."""


def validate_trade_attribution(attribution: TradeAttribution) -> None:
    for field_name in (
        "hypothesis_id",
        "optimizer_run_id",
        "optimizer_candidate_id",
        "research_source",
        "strategy_id",
    ):
        value = getattr(attribution, field_name)
        if not isinstance(value, str) or not value.strip():
            raise TradeAttributionError(f"missing attribution field: {field_name}")


def attribution_payload(attribution: TradeAttribution) -> dict[str, str]:
    validate_trade_attribution(attribution)
    return {
        "hypothesis_id": attribution.hypothesis_id,
        "optimizer_run_id": attribution.optimizer_run_id,
        "optimizer_candidate_id": attribution.optimizer_candidate_id,
        "research_source": attribution.research_source,
        "strategy_id": attribution.strategy_id,
        "attribution_version": attribution.attribution_version,
    }


def extract_trade_trace(row: Mapping[str, Any]) -> dict[str, str | None]:
    metadata = row.get("metadata") if isinstance(row, Mapping) else None
    if not isinstance(metadata, Mapping):
        metadata = {}
    attribution = metadata.get("attribution")
    if not isinstance(attribution, Mapping):
        attribution = {}

    return {
        "trade_id": str(row.get("id") or row.get("trade_id") or ""),
        "strategy_id": str(attribution.get("strategy_id") or row.get("strategy_id") or ""),
        "hypothesis_id": _safe_str(attribution.get("hypothesis_id")),
        "optimizer_run_id": _safe_str(attribution.get("optimizer_run_id")),
        "optimizer_candidate_id": _safe_str(attribution.get("optimizer_candidate_id")),
        "research_source": _safe_str(attribution.get("research_source")),
        "attribution_version": _safe_str(attribution.get("attribution_version")),
    }


def _safe_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None
