from schemas.events import (
    EventEnvelope,
    EventType,
    HypothesisPayload,
    MarketSide,
    ResearchSignalPayload,
    ValidationResultPayload,
    ValidationStatus,
    ExecutionFillPayload,
    RiskHaltPayload,
    HaltSeverity,
)


def test_research_signal_envelope_roundtrip():
    envelope = EventEnvelope(
        event_type=EventType.RESEARCH_SIGNAL,
        producer="research-agent",
        payload=ResearchSignalPayload(
            symbol="BTCUSDT",
            timeframe="1h",
            signal_name="momentum_breakout",
            confidence=0.82,
            source="news+price",
            features={"rsi": 63.2},
        ).model_dump(),
    )

    raw = envelope.model_dump_json()
    rehydrated = EventEnvelope.model_validate_json(raw)

    assert rehydrated.event_type == EventType.RESEARCH_SIGNAL
    assert rehydrated.payload["symbol"] == "BTCUSDT"


def test_all_payloads_serialize():
    payloads = [
        HypothesisPayload(
            hypothesis_id="hyp-1",
            thesis="Vol expansion after Asia open",
            symbols=["ETHUSDT"],
            expected_horizon_hours=6,
            rationale=["historical clustering"],
        ),
        ValidationResultPayload(
            run_id="run-1",
            hypothesis_id="hyp-1",
            status=ValidationStatus.PASS,
            sharpe=1.8,
            max_drawdown_pct=7.2,
        ),
        ExecutionFillPayload(
            exchange="binance",
            order_id="abc123",
            symbol="ETHUSDT",
            side=MarketSide.BUY,
            price=2500.0,
            quantity=0.5,
            fee=0.2,
            filled_at="2026-01-01T00:00:00Z",
        ),
        RiskHaltPayload(
            reason="daily drawdown breached",
            severity=HaltSeverity.HARD_STOP,
            scope="portfolio",
            triggered_by="risk-agent",
            metrics={"drawdown_pct": 5.3},
        ),
    ]

    for payload in payloads:
        encoded = payload.model_dump_json()
        decoded = type(payload).model_validate_json(encoded)
        assert decoded == payload
