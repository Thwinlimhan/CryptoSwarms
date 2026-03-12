import asyncio
from datetime import datetime, timezone

import api.main as main
from cryptoswarms.dashboard_insights import DashboardInsightInput
from cryptoswarms.memory_dag import MemoryDag


def test_dashboard_insights_endpoint():
    async def fake_fetch(_: int) -> DashboardInsightInput:
        return DashboardInsightInput(
            trade_rows=[{"realised_pnl": 5.0, "slippage_bps": 2.0}],
            validation_rows=[{"passed": True}],
            signal_rows=[{"confidence": 0.7, "acted_on": True}],
            attribution_rows=[{"hypothesis_id": "h1", "optimizer_run_id": "run1", "optimizer_candidate_id": "cand1"}],
            regime={"regime": "trending_up", "confidence": 0.8},
            risk_event={"level": 1, "trigger": "none", "portfolio_heat": 0.2, "daily_dd": 0.01, "time": datetime(2026, 3, 8, tzinfo=timezone.utc)},
        )

    original = main._DASHBOARD_REPO.fetch_dashboard_insight_inputs
    main._DASHBOARD_REPO.fetch_dashboard_insight_inputs = fake_fetch
    try:
        payload = asyncio.run(main.dashboard_insights(lookback_hours=24))
    finally:
        main._DASHBOARD_REPO.fetch_dashboard_insight_inputs = original

    assert payload["trade_stats"]["total_pnl_usd"] == 5.0
    assert payload["regime"]["name"] == "trending_up"
    assert payload["attribution_stats"]["coverage_ratio"] == 1.0


def test_dashboard_page_renders_html():
    html = asyncio.run(main.dashboard_page())
    assert "CryptoSwarms Operator Deck" in html


def test_uvicorn_run_kwargs_enable_https_only_when_both_tls_files_are_set():
    original_cert = main.settings.ssl_certfile
    original_key = main.settings.ssl_keyfile
    original_host = main.settings.api_host
    original_port = main.settings.api_port
    try:
        main.settings.api_host = "127.0.0.1"
        main.settings.api_port = 8443
        main.settings.ssl_certfile = "certs/localhost.pem"
        main.settings.ssl_keyfile = "certs/localhost-key.pem"

        kwargs = main._uvicorn_run_kwargs()

        assert kwargs["host"] == "127.0.0.1"
        assert kwargs["port"] == 8443
        assert kwargs["ssl_certfile"] == "certs/localhost.pem"
        assert kwargs["ssl_keyfile"] == "certs/localhost-key.pem"
    finally:
        main.settings.ssl_certfile = original_cert
        main.settings.ssl_keyfile = original_key
        main.settings.api_host = original_host
        main.settings.api_port = original_port



def test_uvicorn_run_kwargs_reject_partial_tls_config():
    original_cert = main.settings.ssl_certfile
    original_key = main.settings.ssl_keyfile
    try:
        main.settings.ssl_certfile = "certs/localhost.pem"
        main.settings.ssl_keyfile = ""

        try:
            main._uvicorn_run_kwargs()
            assert False, "expected ValueError for partial TLS config"
        except ValueError as exc:
            assert "SSL_CERTFILE and SSL_KEYFILE" in str(exc)
    finally:
        main.settings.ssl_certfile = original_cert
        main.settings.ssl_keyfile = original_key

def test_dashboard_fetchers_do_not_fabricate_operator_data():
    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    original_connect = main.asyncpg.connect
    main.asyncpg.connect = boom
    try:
        equity = asyncio.run(main._DASHBOARD_REPO.fetch_equity_curve(lookback_hours=24))
        regime = asyncio.run(main._DASHBOARD_REPO.fetch_current_regime())
        payload = asyncio.run(main._DASHBOARD_REPO.fetch_dashboard_insight_inputs(lookback_hours=24))
    finally:
        main.asyncpg.connect = original_connect

    assert equity == []
    assert regime["regime"] == "unknown"
    assert regime["confidence"] == 0.0
    assert payload.trade_rows == []
    assert payload.validation_rows == []
    assert payload.signal_rows == []


def test_decision_debate_preview_endpoint():
    payload = asyncio.run(
        main.debate_preview(
            scorecard_eligible=True,
            institutional_gate_ok=True,
            attribution_ready=True,
            risk_halt_active=False,
            strategy_count_ok=True,
            expected_value_after_costs_usd=18.0,
            posterior_probability=0.7,
            project_id="default",
        )
    )

    assert payload["decision"] in {"go", "hold"}
    assert payload["project_id"] == "default"
    assert "aggregate" in payload
    assert "rounds" in payload


def test_dag_preview_endpoint_has_shape():
    payload = asyncio.run(
        main.dag_preview(
            topic="phase1-btc-breakout-15m",
            lookback_hours=72,
            max_nodes=8,
            token_budget=800,
            project_id="default",
        )
    )

    assert payload["topic"] == "phase1-btc-breakout-15m"
    assert payload["project_id"] == "default"
    assert "nodes" in payload
    assert "token_estimate" in payload


def test_dag_stats_endpoint_has_shape_and_metrics():
    original_dag = main._DECISION_MEMORY_DAG
    try:
        dag = MemoryDag()
        a = dag.add_node(node_type="decision_checkpoint", topic="s1", content="a", created_at=datetime(2026, 3, 8, tzinfo=timezone.utc))
        b = dag.add_node(node_type="research_hypothesis", topic="s1", content="b", created_at=datetime(2026, 3, 9, tzinfo=timezone.utc))
        dag.add_edge(from_node_id=a.node_id, to_node_id=b.node_id)
        main._DECISION_MEMORY_DAG = dag

        payload = asyncio.run(main.dag_stats())
        assert payload["node_count"] == 2
        assert payload["edge_count"] == 1
        assert payload["topic_count"] == 1
        assert payload["recall_hit_rate"] == 1.0
    finally:
        main._DECISION_MEMORY_DAG = original_dag


def test_dashboard_overview_includes_dag_memory():
    async def fake_ready() -> dict[str, object]:
        return {"ok": True, "checks": {"redis": True}}

    async def fake_status() -> dict[str, dict[str, object]]:
        return {
            "market_scanner": {"status": "healthy", "signals_today": 2},
            "validation_pipeline": {"status": "healthy", "signals_today": 1},
        }

    original_ready = main.readiness_checks
    original_status = main.agents_status
    original_dag = main._DECISION_MEMORY_DAG
    try:
        dag = MemoryDag()
        dag.add_node(node_type="decision_checkpoint", topic="s1", content="a")
        main._DECISION_MEMORY_DAG = dag
        main.readiness_checks = fake_ready
        main.agents_status = fake_status
        payload = asyncio.run(main.dashboard_overview())
    finally:
        main.readiness_checks = original_ready
        main.agents_status = original_status
        main._DECISION_MEMORY_DAG = original_dag

    assert "dag_memory" in payload
    assert payload["dag_memory"]["node_count"] == 1
    assert "attribution_lineage" in payload
    assert payload["signals_today"] == 3




def test_attribution_lineage_endpoint_returns_summary():
    async def fake_traces(limit: int = 200, strategy_id: str | None = None):
        _ = (limit, strategy_id)
        return [
            {
                "trade_id": "t1",
                "strategy_id": "s1",
                "hypothesis_id": "h1",
                "optimizer_run_id": "r1",
                "optimizer_candidate_id": "c1",
                "research_source": "news",
                "attribution_version": "v1",
            }
        ]

    original = main._DASHBOARD_REPO.fetch_live_trade_traces
    main._DASHBOARD_REPO.fetch_live_trade_traces = fake_traces
    try:
        payload = asyncio.run(main.attribution_lineage(strategy_id="s1", limit=100))
    finally:
        main._DASHBOARD_REPO.fetch_live_trade_traces = original

    assert payload["summary"]["strategy_id"] == "s1"
    assert payload["summary"]["coverage_ratio"] == 1.0
    assert len(payload["traces"]) == 1





def test_runtime_preview_endpoint_reports_stages():
    payload = asyncio.run(
        main.runtime_preview(
            scope_ok=True,
            input_ok=True,
            tool_ok=True,
            governor_ok=True,
        )
    )

    assert payload["ok"] is True
    assert "scope" in payload["stages"]
    assert "governor" in payload["stages"]


def test_subagents_preview_endpoint_returns_execution_report():
    payload = asyncio.run(main.subagents_preview(tasks=3, force_timeout=False))
    assert payload["total_tasks"] == 3
    assert payload["max_parallelism"] == 3
    assert payload["queued_tasks"] == 0
    assert payload["estimated_waves"] == 1
    assert payload["queue_pressure_ratio"] == 1.0
    assert payload["saturation"] is False
    assert "timeout_rate" in payload
    assert "error_rate" in payload
    assert len(payload["results"]) == 3
