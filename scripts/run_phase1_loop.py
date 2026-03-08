from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from redis import from_url as redis_from_url

from cryptoswarms.adapters import RedisKeyValueStore
from cryptoswarms.phase1_runtime import AsyncpgPhase1Store, Phase1SummaryRow, RedisStreamSignalSink
from cryptoswarms.reporting import build_daily_summary, write_daily_summary
from cryptoswarms.scanner import MarketScannerCycleRunner, ScannerConfig
from cryptoswarms.strategy_governance import (
    StrategyCountPolicy,
    StrategyDurabilityReport,
    enforce_strategy_count,
)
from memory.runtime_memory import AgentMemoryRecorder


@dataclass
class InMemoryKeyValueStore:
    values: dict[str, str]

    def set(self, key: str, value: str) -> None:
        self.values[key] = value

    def get(self, key: str) -> str | None:
        return self.values.get(key)


@dataclass
class ListSignalSink:
    messages: list[dict[str, object]]

    def publish(self, topic: str, payload: dict[str, object]) -> None:
        self.messages.append({"topic": topic, "payload": payload})


class StaticMarketDataSource:
    def fetch_top_symbols(self, limit: int = 50) -> list[str]:
        return ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def breakout_detected(self, symbol: str) -> bool:
        return symbol == "BTCUSDT"

    def funding_extreme(self, symbol: str) -> str | None:
        return "FUNDING_LONG_SQUEEZE" if symbol == "ETHUSDT" else None

    def smart_money_inflow(self, symbol: str) -> float:
        return 1_500_000.0 if symbol == "SOLUSDT" else 0.0

    def classify_regime(self) -> str:
        return "trending_up"


async def _persist_runtime_artifacts(
    dsn: str,
    run_time: datetime,
    strategy_id: str,
    signals: list[dict[str, object]],
    *,
    accepted: int,
    rejected: int,
    paper_trades: int,
    gross_pnl: float,
    llm_cost: float,
) -> None:
    store = AsyncpgPhase1Store(dsn)
    await store.ensure_schema()
    await store.write_signals(run_time, strategy_id, signals)
    await store.write_summary(
        Phase1SummaryRow(
            run_time=run_time,
            strategy_id=strategy_id,
            total_signals=len(signals),
            accepted_candidates=accepted,
            rejected_candidates=rejected,
            paper_trades=paper_trades,
            gross_pnl_usd=gross_pnl,
            llm_cost_usd=llm_cost,
        )
    )


def _build_runtime_io() -> tuple[object, object]:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    redis_client = redis_from_url(redis_url, encoding="utf-8", decode_responses=True)
    heartbeat_store = RedisKeyValueStore(redis_client)
    sink = RedisStreamSignalSink(redis_client)
    return heartbeat_store, sink


def _enforce_strategy_count_policy() -> None:
    configured = [s.strip() for s in os.getenv("ACTIVE_STRATEGY_IDS", "phase1-btc-breakout-15m").split(",") if s.strip()]
    if not configured:
        configured = ["phase1-btc-breakout-15m"]

    report = None
    if len(configured) > 1:
        report = StrategyDurabilityReport(
            regimes_tested=int(os.getenv("DURABILITY_REGIMES_TESTED", "0")),
            profitable_regimes=int(os.getenv("DURABILITY_PROFITABLE_REGIMES", "0")),
            min_regime_sharpe=float(os.getenv("DURABILITY_MIN_REGIME_SHARPE", "0")),
            max_regime_drawdown=float(os.getenv("DURABILITY_MAX_REGIME_DRAWDOWN", "1")),
            live_days=int(os.getenv("DURABILITY_LIVE_DAYS", "0")),
        )

    decision = enforce_strategy_count(
        configured,
        durability_report=report,
        policy=StrategyCountPolicy(),
    )
    if not decision.approved:
        raise RuntimeError(
            "strategy-count policy blocked run: " + "; ".join(decision.reasons)
        )


def main() -> None:
    now = datetime.now(timezone.utc)
    use_runtime = os.getenv("PHASE1_USE_RUNTIME_ADAPTERS", "false").strip().lower() in {"1", "true", "yes"}
    _enforce_strategy_count_policy()

    if use_runtime:
        heartbeat_store, sink = _build_runtime_io()
    else:
        heartbeat_store = InMemoryKeyValueStore(values={})
        sink = ListSignalSink(messages=[])

    memory = AgentMemoryRecorder("market_scanner")

    runner = MarketScannerCycleRunner(
        data_source=StaticMarketDataSource(),
        sink=sink,
        heartbeat_store=heartbeat_store,
        config=ScannerConfig(max_signals_per_cycle=5, min_confidence=0.65),
        memory_recorder=memory,
    )

    signals = runner.run_cycle(now=now)
    accepted = 1
    rejected = max(0, len(signals) - accepted)
    paper_trades = accepted
    gross_pnl = 12.5
    llm_cost = 0.09
    strategy_id = "phase1-btc-breakout-15m"

    artifacts = Path("artifacts") / "phase1"
    artifacts.mkdir(parents=True, exist_ok=True)

    (artifacts / "signals.json").write_text(json.dumps(signals, indent=2), encoding="utf-8")
    if isinstance(sink, ListSignalSink):
        (artifacts / "published_messages.json").write_text(json.dumps(sink.messages, indent=2), encoding="utf-8")

    summary = build_daily_summary(
        strategy_id=strategy_id,
        signals=signals,
        accepted_candidates=accepted,
        rejected_candidates=rejected,
        paper_trades=paper_trades,
        gross_pnl_usd=gross_pnl,
        llm_cost_usd=llm_cost,
        now=now,
    )
    summary_path = write_daily_summary(summary, artifacts)

    if use_runtime:
        db_password = os.getenv("DB_PASSWORD", "swarm")
        dsn = os.getenv("DB_URL", f"postgresql://swarm:{db_password}@localhost:5432/swarm_db")
        asyncio.run(
            _persist_runtime_artifacts(
                dsn,
                now,
                strategy_id,
                signals,
                accepted=accepted,
                rejected=rejected,
                paper_trades=paper_trades,
                gross_pnl=gross_pnl,
                llm_cost=llm_cost,
            )
        )

    print(f"Phase 1 loop completed at {now.isoformat()}")
    print(f"Signals: {len(signals)} | Accepted: {accepted} | Rejected: {rejected}")
    print(f"Artifacts: {artifacts}")
    print(f"Summary: {summary_path}")
    print(f"Runtime adapters enabled: {use_runtime}")


if __name__ == "__main__":
    main()
