"""MiroFish emergent swarm regime simulator.

Calls the MiroFish REST API to run a multi-agent market simulation and returns
a structured regime verdict with agent consensus metrics.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Protocol


class MiroFishTransport(Protocol):
    def post(self, url: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class SwarmRegimeVerdict:
    regime: str                   # "bullish" | "bearish" | "choppy" | "breakout"
    consensus_score: float        # 0.0–1.0, fraction of agents agreeing on regime
    momentum_agents_pct: float
    mean_revert_agents_pct: float
    noise_agents_pct: float
    whale_pressure: float         # net buy pressure from large-cap agents
    raw_response: dict[str, Any]


@dataclass(slots=True)
class MiroFishRegimeSimulator:
    """Wraps the MiroFish microservice to derive emergent regime verdicts.

    Args:
        base_url: URL of the running mirofish container, e.g. "http://mirofish:5001"
        transport: injectable HTTP transport (use requests-based impl in production)
        min_consensus: minimum agent consensus fraction to trust the regime label
        n_agents: number of simulated agents (overrides container default if sent)
    """
    base_url: str
    transport: MiroFishTransport
    min_consensus: float = 0.55
    n_agents: int = 2000

    def simulate(self, market_data: dict[str, Any]) -> SwarmRegimeVerdict:
        """Run a full swarm simulation against the supplied OHLCV market_data dict.

        market_data must contain at minimum:
          - "close": list[float]
          - "volume": list[float]
          - "high": list[float]   (optional but improves accuracy)
          - "low": list[float]    (optional but improves accuracy)
        """
        payload = {
            "candles": {
                "close": market_data.get("close", []),
                "volume": market_data.get("volume", []),
                "high": market_data.get("high", []),
                "low": market_data.get("low", []),
            },
            "n_agents": self.n_agents,
            "personality_mix": {
                "momentum": 0.35,
                "mean_revert": 0.30,
                "noise": 0.25,
                "whale": 0.10,
            },
        }
        resp = self.transport.post(
            self.base_url.rstrip("/") + "/simulate",
            payload,
        )
        return self._parse(resp)

    def _parse(self, resp: dict[str, Any]) -> SwarmRegimeVerdict:
        agents = resp.get("agent_breakdown", {})
        total = max(sum(agents.values()), 1)
        return SwarmRegimeVerdict(
            regime=resp.get("regime", "unknown"),
            consensus_score=float(resp.get("consensus_score", 0.0)),
            momentum_agents_pct=agents.get("momentum", 0) / total,
            mean_revert_agents_pct=agents.get("mean_revert", 0) / total,
            noise_agents_pct=agents.get("noise", 0) / total,
            whale_pressure=float(resp.get("whale_net_pressure", 0.0)),
            raw_response=resp,
        )

    def is_tradeable(self, verdict: SwarmRegimeVerdict) -> bool:
        """Return True if the swarm consensus is strong enough to trade."""
        return (
            verdict.consensus_score >= self.min_consensus
            and verdict.regime in ("bullish", "bearish", "breakout")
        )
