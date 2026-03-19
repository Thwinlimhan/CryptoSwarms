"""Tests for HyperspaceMeshClient P2P consensus functionality."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from agents.orchestration.hyperspace_mesh import (
    HyperspaceMeshClient,
    AgentRankScore,
    MeshConsensus,
)
from agents.backtest.models import GateResult, GateStatus


class MockTransport:
    def __init__(self):
        self.post_responses = {}
        self.get_responses = {}
        self.should_raise_exception = False
        
    def post(self, url: str, payload: dict) -> dict:
        if self.should_raise_exception:
            raise ConnectionError("Mock network error")
        return self.post_responses.get(url, {"success": True})
        
    def get(self, url: str, params: dict | None = None) -> dict:
        if self.should_raise_exception:
            raise ConnectionError("Mock network error")
        return self.get_responses.get(url, {})


@pytest.fixture
def mock_transport():
    return MockTransport()


@pytest.fixture
def mesh_client(mock_transport):
    return HyperspaceMeshClient(
        node_url="http://localhost:8545",
        agent_id="test-agent",
        transport=mock_transport,
    )


def test_gossip_validation_result_success(mesh_client, mock_transport):
    """Test successful gossip of validation results."""
    mock_transport.post_responses["http://localhost:8545/gossip/validation"] = {
        "propagated": True
    }
    
    gate_results = [
        GateResult(
            gate_number=1,
            gate_name="syntax_check",
            status=GateStatus.PASS,
            score=1.0,
            details={"syntax": "ok"},
        )
    ]
    
    result = mesh_client.gossip_validation_result(
        strategy_id="test-strategy",
        gate_results=gate_results,
        final_score=0.85,
    )
    
    assert result is True


def test_gossip_validation_result_failure(mesh_client, mock_transport):
    """Test gossip failure handling."""
    # Simulate network error by not setting response
    result = mesh_client.gossip_validation_result(
        strategy_id="test-strategy",
        gate_results=[],
        final_score=0.85,
    )
    
    assert result is False


def test_fetch_agent_rank_success(mesh_client, mock_transport):
    """Test successful AgentRank score fetching."""
    mock_transport.get_responses["http://localhost:8545/agentrank/test-agent"] = {
        "rank_score": 0.75,
        "validation_count": 42,
        "consensus_weight": 0.8,
        "last_active": "2026-03-18T15:30:00+00:00",
    }
    
    rank = mesh_client.fetch_agent_rank()
    
    assert rank.agent_id == "test-agent"
    assert rank.rank_score == 0.75
    assert rank.validation_count == 42
    assert rank.consensus_weight == 0.8


def test_fetch_agent_rank_fallback(mesh_client, mock_transport):
    """Test AgentRank fallback when mesh is unreachable."""
    # Trigger exception to test fallback
    mock_transport.should_raise_exception = True
    
    rank = mesh_client.fetch_agent_rank()
    
    assert rank.agent_id == "test-agent"
    assert rank.rank_score == 0.5  # default fallback
    assert rank.validation_count == 0
    assert rank.consensus_weight == 0.1


def test_fetch_mesh_consensus_success(mesh_client, mock_transport):
    """Test successful mesh consensus fetching."""
    mock_transport.get_responses["http://localhost:8545/consensus/test-strategy"] = {
        "consensus_score": 0.85,
        "participating_nodes": 5,
        "rank_weighted_score": 0.82,
        "dissenting_nodes": ["node-3"],
        "timestamp": "2026-03-18T15:30:00+00:00",
    }
    
    consensus = mesh_client.fetch_mesh_consensus("test-strategy")
    
    assert consensus.strategy_id == "test-strategy"
    assert consensus.consensus_score == 0.85
    assert consensus.participating_nodes == 5
    assert consensus.rank_weighted_score == 0.82
    assert consensus.dissenting_nodes == ["node-3"]


def test_fetch_mesh_consensus_fallback(mesh_client, mock_transport):
    """Test mesh consensus fallback when mesh is unreachable."""
    # Trigger exception to test fallback
    mock_transport.should_raise_exception = True
    
    consensus = mesh_client.fetch_mesh_consensus("test-strategy")
    
    assert consensus.strategy_id == "test-strategy"
    assert consensus.consensus_score == 0.5  # neutral fallback
    assert consensus.participating_nodes == 0
    assert consensus.rank_weighted_score == 0.5


def test_join_mesh_success(mesh_client, mock_transport):
    """Test successful mesh joining."""
    mock_transport.post_responses["http://localhost:8545/mesh/join"] = {
        "joined": True
    }
    
    result = mesh_client.join_mesh()
    assert result is True


def test_leave_mesh_success(mesh_client, mock_transport):
    """Test successful mesh leaving."""
    mock_transport.post_responses["http://localhost:8545/mesh/leave"] = {
        "left": True
    }
    
    result = mesh_client.leave_mesh()
    assert result is True


def test_gossip_chub_annotations(mesh_client, mock_transport):
    """Test Chub annotations gossip."""
    mock_transport.post_responses["http://localhost:8545/gossip/chub"] = {
        "propagated": True
    }
    
    annotations = {
        "jesse/backtest": "Use --full-reports flag for complete metrics",
        "hyperliquid/api": "Rate limit is 100 req/min per IP",
    }
    
    result = mesh_client.gossip_chub_annotations(annotations)
    assert result is True