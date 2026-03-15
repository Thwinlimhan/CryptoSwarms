from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class StrategyConfig(BaseModel):
    """Configuration schema for a swarm strategy."""
    id: str
    name: str
    description: str | None = None
    
    # Universe selection
    universe: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    
    # Timing
    interval: str = "1h"
    cooldown_cycles: int = 12
    
    # Thresholds
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    priority_threshold: float = Field(default=0.8, ge=0.0, le=1.0)
    
    # Strategy specific params
    parameters: dict[str, Any] = Field(default_factory=dict)
    
    # Risk controls
    max_position_size_usd: float | None = None
    stop_loss_pct: float | None = None
