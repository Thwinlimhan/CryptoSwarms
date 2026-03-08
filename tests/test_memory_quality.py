from datetime import datetime, timedelta, timezone

from memory.quality import MemoryItem, assess_memory_quality, enforce_retention


def test_enforce_retention_filters_old_items():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    kept = MemoryItem("new", "signal", "scanner", "run-1", now - timedelta(days=2))
    dropped = MemoryItem("old", "signal", "scanner", "run-2", now - timedelta(days=20))

    result = enforce_retention([kept, dropped], now=now, max_age_days=7)
    assert [i.memory_id for i in result] == ["new"]


def test_assess_memory_quality_flags_duplicate_stale_and_missing_traceability():
    now = datetime(2026, 3, 8, tzinfo=timezone.utc)
    items = [
        MemoryItem("m1", "BTC breakout", "scanner", "run-1", now),
        MemoryItem("m2", "btc breakout", "scanner", "run-2", now),
        MemoryItem("m3", "old fact", "", "", now - timedelta(days=40)),
    ]

    report = assess_memory_quality(items, now=now)
    assert report.duplicate_ids == ["m2"]
    assert report.stale_ids == ["m3"]
    assert report.missing_traceability_ids == ["m3"]
