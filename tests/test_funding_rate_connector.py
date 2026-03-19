"""Tests for funding rate connector and AR(12) predictor."""

import pytest
from unittest.mock import MagicMock
import numpy as np

from agents.research.funding_rate_connector import (
    HyperliquidFundingConnector,
    FundingPrediction,
)


class MockTransport:
    def __init__(self):
        self.post_responses = {}
        
    def post(self, url: str, payload: dict) -> dict:
        return self.post_responses.get(url, [])


@pytest.fixture
def mock_transport():
    return MockTransport()


@pytest.fixture
def funding_connector(mock_transport):
    return HyperliquidFundingConnector(transport=mock_transport)


def test_fetch_funding_history_success(funding_connector, mock_transport):
    """Test successful funding history fetching."""
    mock_transport.post_responses["https://api.hyperliquid.xyz/info"] = [
        {"fundingRate": 0.0005},  # 5 bps
        {"fundingRate": 0.0008},  # 8 bps
        {"fundingRate": 0.0003},  # 3 bps
    ]
    
    history = funding_connector.fetch_funding_history("BTC")
    
    # Should convert to basis points (* 10000)
    expected = [5.0, 8.0, 3.0]
    assert len(history) == len(expected)
    for actual, exp in zip(history, expected):
        assert abs(actual - exp) < 1e-10  # Use approximate comparison for floating point


def test_predict_funding_flip_ar12_model(funding_connector):
    """Test AR(12) model prediction with sufficient data."""
    # Create synthetic funding rate history with trend
    np.random.seed(42)  # For reproducible tests
    base_rate = 5.0
    trend = 0.1
    noise = np.random.normal(0, 0.5, 20)
    history = [base_rate + i * trend + noise[i] for i in range(20)]
    
    predicted, flip_in = funding_connector.predict_funding_flip(history)
    
    assert isinstance(predicted, float)
    # Should predict continuation of trend
    assert predicted > history[-1] - 2.0  # Reasonable range
    assert predicted < history[-1] + 2.0


def test_fetch_funding_prediction_integration(funding_connector, mock_transport):
    """Test full funding prediction integration."""
    # Mock funding history response
    mock_funding_data = [{"fundingRate": 0.0008 + i * 0.0001} for i in range(15)]
    mock_transport.post_responses["https://api.hyperliquid.xyz/info"] = mock_funding_data
    
    prediction = funding_connector.fetch_funding_prediction("BTC")
    
    assert isinstance(prediction, FundingPrediction)
    assert prediction.symbol == "BTC"
    assert prediction.venue == "hyperliquid"
    assert isinstance(prediction.current_funding_rate, float)
    assert isinstance(prediction.predicted_funding_rate, float)
    assert 0.0 <= prediction.confidence <= 1.0
    assert 0.0 <= prediction.yield_opportunity_score <= 1.0