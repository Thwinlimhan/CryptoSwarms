import os

from agents.research.camoufox_connector import CamoufoxNewsConnector
from agents.research.deerflow_pipeline import MinimalResearchPipeline
from memory.runtime_memory import AgentMemoryRecorder


class PrintQueue:
    def publish(self, payload: dict[str, object]) -> None:
        print(payload)


def main() -> None:
    base_url = os.getenv("CAMOUFOX_URL", "http://localhost:8080")
    targets = [
        "https://www.coindesk.com/",
        "https://cointelegraph.com/",
    ]
    connector = CamoufoxNewsConnector(base_url=base_url, targets=targets)
    pipeline = MinimalResearchPipeline(connector, PrintQueue(), memory_recorder=AgentMemoryRecorder("research_camoufox"))
    emitted = pipeline.run(symbol="BTCUSDT")
    print(f"Emitted signals: {len(emitted)}")


if __name__ == "__main__":
    main()
