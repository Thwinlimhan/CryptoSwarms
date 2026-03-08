from datetime import datetime, timezone

from cryptoswarms.macro_calendar import MacroEvent, in_macro_blackout


def test_in_macro_blackout_detects_window_match():
    now = datetime(2026, 3, 8, 12, 0, tzinfo=timezone.utc)
    blocked, name = in_macro_blackout(now, (MacroEvent(name="Fed", at=datetime(2026, 3, 8, 12, 20, tzinfo=timezone.utc)),), 30)
    assert blocked is True
    assert name == "Fed"


def test_in_macro_blackout_returns_false_outside_window():
    now = datetime(2026, 3, 8, 12, 0, tzinfo=timezone.utc)
    blocked, name = in_macro_blackout(now, (MacroEvent(name="NFP", at=datetime(2026, 3, 8, 13, 0, tzinfo=timezone.utc)),), 30)
    assert blocked is False
    assert name is None
