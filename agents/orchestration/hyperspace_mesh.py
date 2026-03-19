"""
HyperspaceAI Prometheus P2P mesh client for decentralized agent consensus.

Connects to the Hyperspace network to:
1. Gossip validation results to peer nodes
2. Fetch AgentRank consensus scores
3. Participate in CRDT leaderboard updates
4. Share strategy performance across the mesh
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from agents.backtest.models import GateResult


class HyperspaceTransport(Protocol):
    def post(self, url: str, payload: dict) -> dict: ...
    def get(self, url: str, params: dict | None = None) -> dict: ...


@dataclass(frozen=True)
class AgentRankScore:
    agent_id: str
    rank_score: float        # 0.0-1.0, higher = more trusted
    validation_count: int    # number of validations this agent has performed
    consensus_weight: float  # voting weight in mesh decisions
    last_active: datetime


@dataclass(frozen=True)
class MeshConsensus:
    strategy_id: str
    consensus_score: float   # 0.0-1.0, fraction of mesh agreeing
    participating_nodes: int
    rank_weighted_score: float  # consensus weighted by AgentRank
    dissenting_nodes: list[str]  # nodes that disagreed
    timestamp: datetime


@dataclass(slots=True)
class HyperspaceMeshClient:
    """
    Client for HyperspaceAI Prometheus P2P mesh network.
    
    Args:
        node_url: URL of local Hyperspace node, e.g. "http://localhost:8545"
        agent_id: unique identifier for this CryptoSwarms instance
        transport: injectable HTTP transport for testing
        mesh_timeout: timeout for mesh consensus operations (seconds)
    """
    node_url: str
    agent_id: str
    transport: HyperspaceTransport
    mesh_timeout: float = 30.0

    def gossip_validation_result(
        self,
        strategy_id: str,
        gate_results: list[GateResult],
        final_score: float,
    ) -> bool:
        """
        Gossip a validation result to the mesh network.
        Returns True if successfully propagated to at least one peer.
        """
        payload = {
            "type": "validation_result",
            "agent_id": self.agent_id,
            "strategy_id": strategy_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "final_score": final_score,
            "gate_results": [
                {
                    "gate_number": gr.gate_number,
                    "gate_name": gr.gate_name,
                    "status": gr.status.name,
                    "score": gr.score,
                    "details": gr.details,
                }
                for gr in gate_results
            ],
        }
        
        try:
            resp = self.transport.post(
                f"{self.node_url.rstrip('/')}/gossip/validation",
                payload,
            )
            return resp.get("propagated", False)
        except Exception:
            return False

    def fetch_agent_rank(self, agent_id: str | None = None) -> AgentRankScore:
        """
        Fetch AgentRank score for an agent (defaults to self).
        Returns cached score if mesh is unreachable.
        """
        target_id = agent_id or self.agent_id
        try:
            resp = self.transport.get(
                f"{self.node_url.rstrip('/')}/agentrank/{target_id}"
            )
            return AgentRankScore(
                agent_id=target_id,
                rank_score=float(resp.get("rank_score", 0.0)),
                validation_count=int(resp.get("validation_count", 0)),
                consensus_weight=float(resp.get("consensus_weight", 0.1)),
                last_active=datetime.fromisoformat(
                    resp.get("last_active", datetime.now(timezone.utc).isoformat())
                ),
            )
        except Exception:
            # Return default score if mesh is unreachable
            return AgentRankScore(
                agent_id=target_id,
                rank_score=0.5,
                validation_count=0,
                consensus_weight=0.1,
                last_active=datetime.now(timezone.utc),
            )

    def fetch_mesh_consensus(self, strategy_id: str) -> MeshConsensus:
        """
        Fetch mesh consensus for a strategy validation.
        Blocks until consensus is reached or timeout.
        """
        try:
            resp = self.transport.get(
                f"{self.node_url.rstrip('/')}/consensus/{strategy_id}",
                {"timeout": self.mesh_timeout},
            )
            return MeshConsensus(
                strategy_id=strategy_id,
                consensus_score=float(resp.get("consensus_score", 0.0)),
                participating_nodes=int(resp.get("participating_nodes", 0)),
                rank_weighted_score=float(resp.get("rank_weighted_score", 0.0)),
                dissenting_nodes=resp.get("dissenting_nodes", []),
                timestamp=datetime.fromisoformat(
                    resp.get("timestamp", datetime.now(timezone.utc).isoformat())
                ),
            )
        except Exception:
            # Return neutral consensus if mesh is unreachable
            return MeshConsensus(
                strategy_id=strategy_id,
                consensus_score=0.5,
                participating_nodes=0,
                rank_weighted_score=0.5,
                dissenting_nodes=[],
                timestamp=datetime.now(timezone.utc),
            )

    def gossip_chub_annotations(self, annotations: dict[str, str]) -> bool:
        """
        Share Chub API annotations with the mesh for collective learning.
        
        Args:
            annotations: dict of {api_endpoint: workaround_note}
        """
        payload = {
            "type": "chub_annotations",
            "agent_id": self.agent_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "annotations": annotations,
        }
        
        try:
            resp = self.transport.post(
                f"{self.node_url.rstrip('/')}/gossip/chub",
                payload,
            )
            return resp.get("propagated", False)
        except Exception:
            return False

    def join_mesh(self) -> bool:
        """
        Join the Hyperspace mesh network.
        Should be called once at startup.
        """
        payload = {
            "agent_id": self.agent_id,
            "agent_type": "cryptoswarms_validator",
            "capabilities": [
                "strategy_validation",
                "gate_execution", 
                "code_evolution",
                "microstructure_analysis",
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        try:
            resp = self.transport.post(
                f"{self.node_url.rstrip('/')}/mesh/join",
                payload,
            )
            return resp.get("joined", False)
        except Exception:
            return False

    def leave_mesh(self) -> bool:
        """
        Leave the mesh network gracefully.
        Should be called at shutdown.
        """
        try:
            resp = self.transport.post(
                f"{self.node_url.rstrip('/')}/mesh/leave",
                {"agent_id": self.agent_id},
            )
            return resp.get("left", False)
        except Exception:
            return False

    async def start_consensus_listener(self, callback: callable) -> None:
        """
        Start listening for mesh consensus events.
        Calls callback(consensus: MeshConsensus) when consensus is reached.
        """
        # In production, this would use WebSocket or Server-Sent Events
        # For now, implement as polling loop
        while True:
            try:
                resp = self.transport.get(
                    f"{self.node_url.rstrip('/')}/consensus/events",
                    {"agent_id": self.agent_id, "since": "last_poll"},
                )
                
                for event in resp.get("events", []):
                    if event.get("type") == "consensus_reached":
                        consensus = MeshConsensus(
                            strategy_id=event["strategy_id"],
                            consensus_score=event["consensus_score"],
                            participating_nodes=event["participating_nodes"],
                            rank_weighted_score=event["rank_weighted_score"],
                            dissenting_nodes=event.get("dissenting_nodes", []),
                            timestamp=datetime.fromisoformat(event["timestamp"]),
                        )
                        await callback(consensus)
                        
            except Exception:
                pass  # Continue polling even if individual requests fail
                
            await asyncio.sleep(5.0)  # Poll every 5 seconds