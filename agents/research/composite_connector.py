from __future__ import annotations

from dataclasses import dataclass

from agents.research.deerflow_pipeline import NewsSourceConnector, ResearchItem


@dataclass(slots=True)
class CompositeNewsConnector:
    connectors: list[NewsSourceConnector]

    def fetch_latest(self) -> list[ResearchItem]:
        merged: list[ResearchItem] = []
        seen: set[tuple[str, str]] = set()

        for connector in self.connectors:
            for item in connector.fetch_latest():
                key = (item.source, item.url)
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)

        return merged
