import json

from cryptoswarms.phase1_runtime import RedisStreamSignalSink


class FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def xadd(self, stream: str, payload: dict[str, str]) -> str:
        self.calls.append((stream, payload))
        return "1-0"


def test_redis_stream_signal_sink_writes_event_json():
    fake = FakeRedis()
    sink = RedisStreamSignalSink(fake, stream_name="research:signals")
    sink.publish("research:signals", {"symbol": "BTCUSDT", "confidence": 0.9})

    assert len(fake.calls) == 1
    stream, payload = fake.calls[0]
    assert stream == "research:signals"
    event = json.loads(payload["event"])
    assert event["topic"] == "research:signals"
    assert event["payload"]["symbol"] == "BTCUSDT"
