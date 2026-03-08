from cryptoswarms.trade_attribution import TradeAttribution, TradeAttributionError, attribution_payload, extract_trade_trace


def test_attribution_payload_requires_all_fields():
    valid = TradeAttribution(
        hypothesis_id="h-1",
        optimizer_run_id="opt-run-1",
        optimizer_candidate_id="cand-1",
        research_source="camoufox",
        strategy_id="phase1-btc-breakout-15m",
    )
    payload = attribution_payload(valid)
    assert payload["hypothesis_id"] == "h-1"


def test_extract_trade_trace_reads_metadata():
    row = {
        "id": "trade-1",
        "metadata": {
            "attribution": {
                "hypothesis_id": "h-1",
                "optimizer_run_id": "run-1",
                "optimizer_candidate_id": "cand-1",
                "research_source": "literature",
                "strategy_id": "s1",
                "attribution_version": "v1",
            }
        },
    }
    trace = extract_trade_trace(row)
    assert trace["trade_id"] == "trade-1"
    assert trace["optimizer_run_id"] == "run-1"


def test_attribution_payload_rejects_blank_field():
    bad = TradeAttribution(
        hypothesis_id="",
        optimizer_run_id="opt-run-1",
        optimizer_candidate_id="cand-1",
        research_source="camoufox",
        strategy_id="s1",
    )

    try:
        attribution_payload(bad)
        assert False, "expected TradeAttributionError"
    except TradeAttributionError:
        assert True
