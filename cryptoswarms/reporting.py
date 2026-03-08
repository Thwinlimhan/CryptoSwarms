from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class DailySummary:
    date: str
    strategy_id: str
    total_signals: int
    accepted_candidates: int
    rejected_candidates: int
    paper_trades: int
    gross_pnl_usd: float
    llm_cost_usd: float

    def as_markdown(self) -> str:
        return "\n".join(
            [
                f"# Daily Summary - {self.date}",
                "",
                f"- Strategy: `{self.strategy_id}`",
                f"- Signals generated: **{self.total_signals}**",
                f"- Candidates accepted: **{self.accepted_candidates}**",
                f"- Candidates rejected: **{self.rejected_candidates}**",
                f"- Paper trades: **{self.paper_trades}**",
                f"- Gross PnL (USD): **{self.gross_pnl_usd:.2f}**",
                f"- LLM spend (USD): **{self.llm_cost_usd:.2f}**",
            ]
        )


def build_daily_summary(
    *,
    strategy_id: str,
    signals: list[dict[str, object]],
    accepted_candidates: int,
    rejected_candidates: int,
    paper_trades: int,
    gross_pnl_usd: float,
    llm_cost_usd: float,
    now: datetime | None = None,
) -> DailySummary:
    ts = now or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return DailySummary(
        date=ts.date().isoformat(),
        strategy_id=strategy_id,
        total_signals=len(signals),
        accepted_candidates=accepted_candidates,
        rejected_candidates=rejected_candidates,
        paper_trades=paper_trades,
        gross_pnl_usd=float(gross_pnl_usd),
        llm_cost_usd=float(llm_cost_usd),
    )


def write_daily_summary(summary: DailySummary, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"daily_summary_{summary.date}.md"
    out_path.write_text(summary.as_markdown() + "\n", encoding="utf-8")
    return out_path
