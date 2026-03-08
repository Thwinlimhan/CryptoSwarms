from __future__ import annotations

from agents.research.deerflow_pipeline import MinimalResearchPipeline
from agents.research.onchain_connector import WhaleFlowConnector, sample_whale_feed
from memory.runtime_memory import AgentMemoryRecorder


class PrintQueue:
    def publish(self, payload: dict[str, object]) -> None:
        print(payload)


def main() -> None:
    connector = WhaleFlowConnector(fetch_fn=sample_whale_feed)
    pipeline = MinimalResearchPipeline(connector, PrintQueue(), memory_recorder=AgentMemoryRecorder("research_onchain"))
    emitted = pipeline.run(symbol="BTCUSDT")
    print(f"On-chain emitted signals: {len(emitted)}")


if __name__ == "__main__":
    main()
