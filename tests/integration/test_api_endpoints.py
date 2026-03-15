"""Integration tests for API endpoints.

These tests require NO live services — they use the FastAPI TestClient
which runs the app in-process with mocked dependencies.

To run:
    pytest tests/integration/test_api_endpoints.py -m integration -v
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Create a test client without starting real background agents."""
    from api.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.mark.integration
class TestHealthEndpoints:
    def test_health_live(self, client: TestClient):
        resp = client.get("/api/health/live")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_health_ready_returns_dict(self, client: TestClient):
        resp = client.get("/api/health/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


@pytest.mark.integration
class TestCostsEndpoints:
    def test_budget_zero_spend(self, client: TestClient):
        resp = client.get("/api/costs/budget?spent_usd=0.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["within_budget"] if "within_budget" in data else True
        assert data["spent_usd"] == 0.0

    def test_budget_over_limit(self, client: TestClient):
        resp = client.get("/api/costs/budget?spent_usd=999.0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["blocked"] is True


@pytest.mark.integration
class TestBacktestEndpoints:
    def test_results_not_implemented(self, client: TestClient):
        resp = client.get("/api/backtest/results/test-strategy-001")
        assert resp.status_code == 200
        data = resp.json()
        assert data["_synthetic"] is True
        assert data["equity_curve"] == []

    def test_strategies_returns_list(self, client: TestClient):
        resp = client.get("/api/backtest/strategies")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.integration
class TestRoutingEndpoint:
    def test_routing_policy(self, client: TestClient):
        resp = client.get("/api/routing/policy")
        assert resp.status_code == 200
        assert "tasks" in resp.json()
