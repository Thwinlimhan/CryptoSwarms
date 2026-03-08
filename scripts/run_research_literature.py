from __future__ import annotations

from agents.research.deerflow_pipeline import MinimalResearchPipeline
from agents.research.literature_connector import LiteratureConnector, sample_literature_feed
from memory.runtime_memory import AgentMemoryRecorder


class PrintQueue:
    def publish(self, payload: dict[str, object]) -> None:
        print(payload)


def main() -> None:
    connector = LiteratureConnector(fetch_fn=sample_literature_feed)
    pipeline = MinimalResearchPipeline(connector, PrintQueue(), memory_recorder=AgentMemoryRecorder("research_literature"))
    emitted = pipeline.run(symbol="BTCUSDT")
    print(f"Literature emitted signals: {len(emitted)}")


if __name__ == "__main__":
    main()
