def test_get_health_returns_healthy_when_database_connected(client):
    """GET /api/v1/health returns 200 with status healthy when database is up."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "environment" in data
    assert "version" in data
