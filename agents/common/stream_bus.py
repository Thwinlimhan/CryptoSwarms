from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Protocol, Sequence

from schemas.events import EventEnvelope
from agents.common import streams


class RedisStreamClient(Protocol):
    def xadd(self, name: str, fields: dict[str, Any], id: str = "*") -> str: ...

    def xreadgroup(
        self,
        groupname: str,
        consumername: str,
        streams: dict[str, str],
        count: int = 1,
        block: int | None = None,
    ) -> list[tuple[str, list[tuple[str, dict[str, Any]]]]]: ...

    def xack(self, name: str, groupname: str, *ids: str) -> int: ...


@dataclass(slots=True)
class StreamMessage:
    stream: str
    message_id: str
    envelope: EventEnvelope


class StreamBus:
    def __init__(self, redis: RedisStreamClient, group: str, consumer: str):
        self.redis = redis
        self.group = group
        self.consumer = consumer

    def xadd(self, stream: str, envelope: EventEnvelope) -> str:
        return self.redis.xadd(stream, {"event": envelope.model_dump_json()})

    def xreadgroup(
        self,
        stream_names: Sequence[str],
        count: int = 10,
        block_ms: int | None = None,
    ) -> list[StreamMessage]:
        raw_batches = self.redis.xreadgroup(
            groupname=self.group,
            consumername=self.consumer,
            streams={name: ">" for name in stream_names},
            count=count,
            block=block_ms,
        )
        messages: list[StreamMessage] = []
        for stream_name, entries in raw_batches:
            for message_id, fields in entries:
                event_blob = fields["event"]
                if isinstance(event_blob, bytes):
                    event_blob = event_blob.decode("utf-8")
                envelope = EventEnvelope.model_validate_json(event_blob)
                messages.append(StreamMessage(stream=stream_name, message_id=message_id, envelope=envelope))
        return messages

    def ack(self, stream: str, message_id: str) -> int:
        return self.redis.xack(stream, self.group, message_id)

    def retry(self, message: StreamMessage, error: Exception | None = None) -> str:
        payload = message.envelope.model_dump(mode="json")
        meta = payload.setdefault("metadata", {})
        attempts = int(meta.get("attempts", 0)) + 1
        meta["attempts"] = attempts
        if error is not None:
            meta["last_error"] = str(error)

        retry_id = self.redis.xadd(message.stream, {"event": json.dumps(payload)})
        self.ack(message.stream, message.message_id)
        return retry_id

    def dead_letter(self, message: StreamMessage, error: Exception) -> str:
        payload = message.envelope.model_dump(mode="json")
        meta = payload.setdefault("metadata", {})
        meta["last_error"] = str(error)
        meta["dead_lettered"] = True

        dlq_stream = streams.dead_letter(message.stream)
        dlq_id = self.redis.xadd(dlq_stream, {"event": json.dumps(payload)})
        self.ack(message.stream, message.message_id)
        return dlq_id

    def process_with_retry(
        self,
        message: StreamMessage,
        handler: Callable[[StreamMessage], None],
        max_attempts: int = 3,
    ) -> None:
        attempts = self._attempt_count(message)
        try:
            handler(message)
            self.ack(message.stream, message.message_id)
        except Exception as exc:  # noqa: BLE001
            if attempts + 1 >= max_attempts:
                self.dead_letter(message, exc)
            else:
                self.retry(message, exc)

    @staticmethod
    def _attempt_count(message: StreamMessage) -> int:
        return int(message.envelope.metadata.get("attempts", 0))
