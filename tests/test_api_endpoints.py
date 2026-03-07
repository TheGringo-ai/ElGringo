"""
Tests for Fred API endpoints
"""

import pytest
from unittest.mock import patch

# Import the app for testing
try:
    from fastapi.testclient import TestClient
    from products.fred_api.server import app
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False


@pytest.fixture
def client():
    """Create a test client with no API key requirement."""
    with patch.dict("os.environ", {"FRED_API_KEYS": ""}, clear=False):
        from products.fred_api.server import FRED_API_KEYS
        FRED_API_KEYS.clear()  # No auth for tests
        return TestClient(app)


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI not available")
class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_has_version(self, client):
        resp = client.get("/v1/health")
        assert "version" in resp.json()


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI not available")
class TestAgentsEndpoint:
    def test_list_agents(self, client):
        resp = client.get("/v1/agents")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            assert "name" in data[0]
            assert "capabilities" in data[0]


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI not available")
class TestMemoryEndpoints:
    def test_memory_stats(self, client):
        resp = client.get("/v1/memory/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_interactions" in data
        assert "total_solutions" in data
        assert "total_mistakes" in data

    def test_memory_search_solutions(self, client):
        resp = client.post("/v1/memory/search", json={
            "query": "database", "search_type": "solutions", "limit": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "solutions" in data

    def test_memory_search_mistakes(self, client):
        resp = client.post("/v1/memory/search", json={
            "query": "security", "search_type": "mistakes", "limit": 3,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "mistakes" in data

    def test_memory_search_all(self, client):
        resp = client.post("/v1/memory/search", json={
            "query": "auth", "search_type": "all",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "solutions" in data
        assert "mistakes" in data

    def test_memory_store_solution(self, client):
        resp = client.post("/v1/memory/store", json={
            "type": "solution",
            "problem": "Test problem from API test",
            "solution_steps": ["Step 1", "Step 2"],
            "tags": ["test"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stored"] == "solution"
        assert "id" in data

    def test_memory_store_mistake(self, client):
        resp = client.post("/v1/memory/store", json={
            "type": "mistake",
            "description": "Test mistake from API test",
            "mistake_type": "code_error",
            "severity": "low",
            "prevention": "Don't do this",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["stored"] == "mistake"

    def test_memory_store_invalid_type(self, client):
        resp = client.post("/v1/memory/store", json={
            "type": "invalid",
        })
        assert resp.status_code == 400


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI not available")
class TestCostsEndpoint:
    def test_costs(self, client):
        resp = client.get("/v1/costs")
        assert resp.status_code == 200
        data = resp.json()
        assert "statistics" in data
        assert "budget" in data
        assert "per_model" in data


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI not available")
class TestVerifyEndpoint:
    def test_verify_valid_python(self, client):
        resp = client.post("/v1/verify", json={
            "code": "x = 1\nprint(x)\n",
            "language": "python",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["valid"] is True
        assert data["language"] == "python"

    def test_verify_security_issue(self, client):
        resp = client.post("/v1/verify", json={
            "code": "result = eval(user_input)\n",
            "language": "python",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["warnings"]) > 0

    def test_verify_auto_detect(self, client):
        resp = client.post("/v1/verify", json={
            "code": "import os\ndef foo():\n    pass\n",
        })
        assert resp.status_code == 200
        assert resp.json()["language"] == "python"


@pytest.mark.skipif(not API_AVAILABLE, reason="FastAPI not available")
class TestDocsEndpoint:
    def test_docs_available(self, client):
        resp = client.get("/v1/docs")
        assert resp.status_code == 200

    def test_redoc_available(self, client):
        resp = client.get("/v1/redoc")
        assert resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
