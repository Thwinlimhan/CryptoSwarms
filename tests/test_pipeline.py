from cryptoswarms.pipeline import (
    BacktestReport,
    GateChainOrchestrator,
    StrategyDraft,
    StrategyHandoffOrchestrator,
)


class FakeCoder:
    def generate(self, hypothesis_id: str, context: dict[str, object]) -> StrategyDraft:
        return StrategyDraft(hypothesis_id=hypothesis_id, strategy_code="code", metadata=context)


class FakeJesse:
    def backtest(self, draft: StrategyDraft) -> BacktestReport:
        return BacktestReport(hypothesis_id=draft.hypothesis_id, passed=True, metrics={"sharpe": 1.2})


class PassGate:
    def evaluate(self, report: BacktestReport):
        return True, "ok"


class FailGate:
    def evaluate(self, report: BacktestReport):
        return False, "failed gate"


def test_strategy_handoff_runs_coder_then_backtest():
    orchestrator = StrategyHandoffOrchestrator(FakeCoder(), FakeJesse())
    report = orchestrator.run("hyp-1", {"symbol": "BTCUSDT"})

    assert report.hypothesis_id == "hyp-1"
    assert report.metrics["sharpe"] == 1.2


def test_gate_chain_stops_on_first_failure():
    draft = StrategyDraft(hypothesis_id="hyp-1", strategy_code="x", metadata={})
    report = BacktestReport(hypothesis_id="hyp-1", passed=True, metrics={})

    result = GateChainOrchestrator([PassGate(), FailGate(), PassGate()]).evaluate(draft, report)

    assert result.accepted is False
    assert result.reason == "failed gate"


def test_gate_chain_accepts_when_all_pass():
    draft = StrategyDraft(hypothesis_id="hyp-1", strategy_code="x", metadata={})
    report = BacktestReport(hypothesis_id="hyp-1", passed=True, metrics={})

    result = GateChainOrchestrator([PassGate(), PassGate()]).evaluate(draft, report)

    assert result.accepted is True
    assert result.reason == "all gates passed"
