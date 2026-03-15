"""Base strategy interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from schemas.strategy import StrategyConfig


class BaseStrategy(ABC):
    """Abstract base for all swarm strategies."""
    
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    @abstractmethod
    async def evaluate(self, signal: dict[str, Any], context: dict[str, Any]) -> dict[str, Any] | None:
        """
        Evaluate a signal within the given context.
        Returns a 'Strategic Decision' dict if triggered, else None.
        """
        pass
