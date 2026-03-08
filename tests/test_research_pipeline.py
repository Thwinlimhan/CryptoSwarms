from agents.research.deerflow_pipeline import MinimalResearchPipeline, StaticNewsConnector, score_sentiment


class InMemoryQueue:
    def __init__(self) -> None:
        self.items: list[dict[str, object]] = []

    def publish(self, payload: dict[str, object]) -> None:
        self.items.append(payload)


class InMemoryMemory:
    def __init__(self) -> None:
        self.records: list[tuple[str, bool]] = []

    def remember(self, text: str, important: bool = False) -> None:
        self.records.append((text, important))


def test_score_sentiment_positive_signal():
    result = score_sentiment("Bullish breakout and strong inflow")
    assert result.label == "positive"
    assert result.score > 0


def test_research_pipeline_publishes_with_provenance():
    queue = InMemoryQueue()
    pipeline = MinimalResearchPipeline(StaticNewsConnector(), queue)

    emitted = pipeline.run(symbol="BTCUSDT")

    assert len(emitted) >= 1
    assert len(queue.items) == len(emitted)
    assert "provenance" in queue.items[0]
    assert "url" in queue.items[0]["provenance"]


def test_research_pipeline_writes_memory_records():
    queue = InMemoryQueue()
    memory = InMemoryMemory()
    pipeline = MinimalResearchPipeline(StaticNewsConnector(), queue, memory_recorder=memory)

    emitted = pipeline.run(symbol="BTCUSDT")

    assert len(memory.records) == len(emitted)
    assert any("research-" in text for text, _ in memory.records)
