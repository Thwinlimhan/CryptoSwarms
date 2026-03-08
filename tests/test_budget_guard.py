from cryptoswarms.budget_guard import BudgetConfig, evaluate_budget


def test_budget_alert_threshold_and_blocking():
    cfg = BudgetConfig(daily_budget_usd=10.0, alert_threshold_ratio=0.7)

    status_alert = evaluate_budget(7.1, cfg)
    assert status_alert.alert is True
    assert status_alert.blocked is False

    status_blocked = evaluate_budget(10.1, cfg)
    assert status_blocked.blocked is True
