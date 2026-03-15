from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("failure_ledger")

@dataclass
class DecisionRecord:
    id: str
    label: str
    time: datetime
    ev_estimate: float
    win_probability: float
    position_size_usd: float
    status: str = "pending"
    pnl_usd: float = 0.0
    bias_flags: list[str] = field(default_factory=list)
    notes: str = ""
    resolved_at: datetime | None = None
    strategy_id: str | None = None


class FailureLedger:
    """
    Advanced tracking for decision quality vs outcomes.
    Tracks 'Net Luck' (P&L - Expected P&L) and 'Calibration' (Actual vs Predicted Probability).
    """
    def __init__(self) -> None:
        self.decisions: dict[str, DecisionRecord] = {}

    def log_decision(self, record: DecisionRecord) -> None:
        self.decisions[record.id] = record
        logger.info(f"LOGGED DECISION: {record.label} (EV: ${record.ev_estimate})")

    def resolve_decision(self, id: str, result: str, pnl: float, notes: str = "") -> None:
        if id not in self.decisions:
            logger.error(f"Cannot resolve unknown decision: {id}")
            return
            
        record = self.decisions[id]
        record.status = result
        record.pnl_usd = pnl
        record.notes = notes
        record.resolved_at = datetime.now(timezone.utc)
        logger.info(f"RESOLVED DECISION: {record.label} as {result} (PnL: ${pnl})")

    def get_stats(self) -> dict[str, Any]:
        """Calculate calibration and luck metrics."""
        resolved = [d for d in self.decisions.values() if d.status in ["won", "lost"]]
        if not resolved:
            return {"status": "NO_DATA"}

        total_pnl = sum(d.pnl_usd for d in resolved)
        expected_pnl = sum(d.ev_estimate for d in resolved)
        net_luck = total_pnl - expected_pnl

        actual_wins = sum(1 for d in resolved if d.status == "won")
        expected_wins = sum(d.win_probability for d in resolved)
        calibration_error = (actual_wins - expected_wins) / len(resolved)

        return {
            "total_decisions": len(self.decisions),
            "resolved_count": len(resolved),
            "actual_pnl": total_pnl,
            "expected_pnl": expected_pnl,
            "net_luck": net_luck,
            "actual_win_rate": actual_wins / len(resolved),
            "expected_win_rate": expected_wins / len(resolved),
            "calibration_error": calibration_error,
            "bias_heatmap": self._calculate_bias_heatmap(resolved)
        }

    def _calculate_bias_heatmap(self, records: list[DecisionRecord]) -> dict[str, int]:
        heatmap: dict[str, int] = {}
        for r in records:
            for bias in r.bias_flags:
                heatmap[bias] = heatmap.get(bias, 0) + 1
        return heatmap
