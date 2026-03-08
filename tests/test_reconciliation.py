from cryptoswarms.reconciliation import FillReconciliationMonitor, FillRecord, OrderRecord


def test_reconciliation_reports_missing_and_mismatch():
    monitor = FillReconciliationMonitor()
    result = monitor.reconcile(
        orders=[OrderRecord("o1", "BTCUSDT", 1.0), OrderRecord("o2", "ETHUSDT", 2.0)],
        fills=[FillRecord("o1", 0.5)],
    )

    assert result.matched == 0
    assert result.qty_mismatches == ["o1"]
    assert result.missing_fills == ["o2"]
