from fastapi.testclient import TestClient
from services.api.main import app

client = TestClient(app)


def test_api_benchmark_endpoint():
    response = client.get("/api/benchmarks/summary")
    assert response.status_code == 200
    data = response.json()
    assert "benchmark_id" in data
    assert "results" in data
    assert len(data["results"]) == 3
    assert data["status"] == "SIMULATED"
    assert "ranked_by_mae" in data
