from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class StrategyDraft:
    hypothesis_id: str
    strategy_code: str
    metadata: dict[str, object]


@dataclass(frozen=True)
class BacktestReport:
    hypothesis_id: str
    passed: bool
    metrics: dict[str, float]


class StrategyCoder(Protocol):
    def generate(self, hypothesis_id: str, context: dict[str, object]) -> StrategyDraft: ...


class JesseEngine(Protocol):
    def backtest(self, draft: StrategyDraft) -> BacktestReport: ...


class GateEvaluator(Protocol):
    def evaluate(self, report: BacktestReport) -> tuple[bool, str]: ...


@dataclass(frozen=True)
class PipelineResult:
    accepted: bool
    reason: str
    draft: StrategyDraft
    report: BacktestReport
    decided_at: datetime


class StrategyHandoffOrchestrator:
    """Bridge between Strategy Coder output and Jesse backtesting."""

    def __init__(self, coder: StrategyCoder, jesse: JesseEngine) -> None:
        self._coder = coder
        self._jesse = jesse

    def run(self, hypothesis_id: str, context: dict[str, object]) -> BacktestReport:
        draft = self._coder.generate(hypothesis_id, context)
        return self._jesse.backtest(draft)


class GateChainOrchestrator:
    """Runs ordered gate evaluators and returns first-failure reason."""

    def __init__(self, gates: list[GateEvaluator]) -> None:
        self._gates = gates

    def evaluate(self, draft: StrategyDraft, report: BacktestReport) -> PipelineResult:
        for gate in self._gates:
            passed, reason = gate.evaluate(report)
            if not passed:
                return PipelineResult(
                    accepted=False,
                    reason=reason,
                    draft=draft,
                    report=report,
                    decided_at=datetime.now(timezone.utc),
                )

        return PipelineResult(
            accepted=True,
            reason="all gates passed",
            draft=draft,
            report=report,
            decided_at=datetime.now(timezone.utc),
        )
