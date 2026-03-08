from pathlib import Path

from cryptoswarms.immutable_audit import ImmutableJsonlAuditLog


def test_immutable_audit_chain_roundtrip(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    log = ImmutableJsonlAuditLog(path)

    log.append(agent="scanner", action="emit", run_id="r1", metadata={"n": 1})
    log.append(agent="execution", action="fill", run_id="r1", metadata={"symbol": "BTCUSDT"})

    ok, reason = log.verify_chain()
    assert ok is True
    assert reason == "ok"


def test_immutable_audit_chain_detects_tampering(tmp_path: Path):
    path = tmp_path / "audit.jsonl"
    log = ImmutableJsonlAuditLog(path)
    log.append(agent="scanner", action="emit", run_id="r1", metadata={"n": 1})

    content = path.read_text(encoding="utf-8")
    path.write_text(content.replace('"n":1', '"n":999'), encoding="utf-8")

    ok, reason = log.verify_chain()
    assert ok is False
    assert "hash mismatch" in reason
