from datetime import datetime, timezone

from cryptoswarms.observability import AgentAuditEvent, AgentAuditLog, evaluate_alerts


def test_audit_log_query_filters_by_agent_and_run():
    log = AgentAuditLog()
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    log.append(AgentAuditEvent(now, "scanner", "emit", "r1", {}))
    log.append(AgentAuditEvent(now, "execution", "fill", "r2", {}))

    assert len(log.query(agent="scanner")) == 1
    assert len(log.query(run_id="r2")) == 1


def test_alert_evaluation_triggers_expected_flags():
    state = evaluate_alerts(llm_spent_usd=11.0, llm_budget_usd=10.0, pipeline_halted=True, exchange_errors=3)
    assert state.budget_breach is True
    assert state.pipeline_halt is True
    assert state.exchange_error_spike is True
