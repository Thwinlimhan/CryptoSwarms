# agents/research/funding_rate_connector.py
"""
Hyperliquid funding rate connector and predictor.
Uses Hyperliquid's free, no-auth API.
Builds AR(12) funding rate predictor in-house.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Protocol


class HttpTransport(Protocol):
    def post(self, url: str, payload: dict) -> dict: ...


@dataclass(frozen=True)
class FundingPrediction:
    symbol: str
    current_funding_rate: float      # current 8h funding rate (bps)
    predicted_funding_rate: float    # 30-min ahead prediction (bps)
    predicted_flip_in_minutes: int | None   # None if no flip predicted
    confidence: float               # Confidence 0.0–1.0
    yield_opportunity_score: float  # composite yield score 0.0–1.0
    venue: str = "hyperliquid"


@dataclass(slots=True)
class HyperliquidFundingConnector:
    """Fetches funding history and predicts future rates."""
    transport: HttpTransport
    base_url: str = "https://api.hyperliquid.xyz/info"

    def fetch_funding_history(self, symbol: str) -> list[float]:
        """Fetch 1-hour funding rates from Hyperliquid. No API key required."""
        resp = self.transport.post(self.base_url, {
            "type": "fundingHistory",
            "coin": symbol,
        })
        # Hyperliquid returns a list of funding events
        return [float(x.get("fundingRate", 0)) * 10000 for x in resp if "fundingRate" in x]

    def predict_funding_flip(self, history: list[float]) -> tuple[float, int | None]:
        """AR(12) model predicting next funding rate and flip timing.
        Returns (predicted_rate_bps, flip_in_periods | None)."""
        if len(history) < 12:
            return (history[-1] if history else 0.0, None)
        
        # Implement proper AR(12) autoregressive model
        # AR(12): X_t = c + φ₁X_{t-1} + φ₂X_{t-2} + ... + φ₁₂X_{t-12} + ε_t
        
        import numpy as np
        from sklearn.linear_model import LinearRegression
        
        # Prepare training data for AR(12)
        X = []  # Features: [X_{t-1}, X_{t-2}, ..., X_{t-12}]
        y = []  # Target: X_t
        
        for i in range(12, len(history)):
            X.append(history[i-12:i])  # Last 12 values as features
            y.append(history[i])       # Current value as target
        
        if len(X) < 12:  # Not enough data for AR(12)
            # Fall back to simple linear extrapolation
            last_3 = history[-3:]
            slope = (last_3[-1] - last_3[0]) / 2.0
            predicted = last_3[-1] + slope
        else:
            # Fit AR(12) model
            X = np.array(X)
            y = np.array(y)
            
            model = LinearRegression()
            model.fit(X, y)
            
            # Predict next value using last 12 observations
            last_12 = np.array(history[-12:]).reshape(1, -1)
            predicted = model.predict(last_12)[0]
        
        # Detect sign flip
        flip_in = None
        current = history[-1]
        if (predicted > 0) != (current > 0) and abs(predicted - current) > 1.0:
            # Sign flip predicted with significant magnitude change
            flip_in = 60  # 60 minutes (1 hour) since Hyperliquid uses 1h funding
            
        return (predicted, flip_in)

    def fetch_funding_prediction(self, symbol: str) -> FundingPrediction:
        history = self.fetch_funding_history(symbol)
        if not history:
            return FundingPrediction(symbol, 0.0, 0.0, None, 0.0, 0.0)
        
        current = history[-1]
        predicted, flip_in = self.predict_funding_flip(history)
        
        # Composite score based on absolute funding magnitude
        yield_score = min(1.0, abs(current) / 10.0) # 10 bps is a "high" yield
        
        return FundingPrediction(
            symbol=symbol,
            current_funding_rate=current,
            predicted_funding_rate=predicted,
            predicted_flip_in_minutes=flip_in,
            confidence=0.7, # Static for now
            yield_opportunity_score=yield_score,
        )
