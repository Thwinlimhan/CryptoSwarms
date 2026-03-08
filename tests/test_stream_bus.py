from __future__ import annotations

import json
from collections import defaultdict
from typing import Any

from agents.common import streams
from agents.common.stream_bus import StreamBus
from schemas.events import EventEnvelope, EventType, ResearchSignalPayload


class FakeRedis:
    def __init__(self) -> None:
        self._ids = 0
        self.data: dict[str, list[tuple[str, dict[str, Any]]]] = defaultdict(list)
        self.acks: list[tuple[str, str, tuple[str, ...]]] = []

    def xadd(self, name: str, fields: dict[str, Any], id: str = "*") -> str:
        self._ids += 1
        message_id = f"{self._ids}-0"
        self.data[name].append((message_id, fields))
        return message_id

    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 1,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, Any]]]]]:
        batches = []
        for stream_name in streams:
            if self.data[stream_name]:
                batches.append((stream_name, self.data[stream_name][:count]))
        return batches

    def xack(self, name: str, groupname: str, *ids: str) -> int:
        self.acks.append((name, groupname, ids))
        return len(ids)


def _sample_event() -> EventEnvelope:
    return EventEnvelope(
        event_type=EventType.RESEARCH_SIGNAL,
        producer="research-agent",
        payload=ResearchSignalPayload(
            symbol="BTCUSDT",
            timeframe="5m",
            signal_name="breakout",
            confidence=0.9,
            source="model",
        ).model_dump(),
    )


def test_publish_and_consume_roundtrip():
    redis = FakeRedis()
    bus = StreamBus(redis, group="research", consumer="worker-1")

    bus.xadd(streams.RESEARCH_SIGNALS, _sample_event())
    messages = bus.xreadgroup([streams.RESEARCH_SIGNALS], count=1)

    assert len(messages) == 1
    assert messages[0].envelope.payload["signal_name"] == "breakout"


def test_retry_then_dead_letter_on_max_attempts():
    redis = FakeRedis()
    bus = StreamBus(redis, group="validation", consumer="worker-1")

    message_id = bus.xadd(streams.VALIDATION_RESULTS, _sample_event())
    message = bus.xreadgroup([streams.VALIDATION_RESULTS])[0]

    def failing_handler(_: Any) -> None:
        raise RuntimeError("bad parse")

    bus.process_with_retry(message, failing_handler, max_attempts=2)

    retry_message = redis.data[streams.VALIDATION_RESULTS][-1]
    retry_payload = json.loads(retry_message[1]["event"])
    assert retry_payload["metadata"]["attempts"] == 1

    retried = bus.xreadgroup([streams.VALIDATION_RESULTS], count=2)[1]
    bus.process_with_retry(retried, failing_handler, max_attempts=2)

    dlq_name = streams.dead_letter(streams.VALIDATION_RESULTS)
    assert redis.data[dlq_name]
    assert (streams.VALIDATION_RESULTS, "validation", (message_id,)) in redis.acks
