"""Health check endpoint tests"""


def test_health_check(client):
    """Test the health check endpoint returns healthy status"""
    response = client.get("/health")

    # Should return 200 OK
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "core-service"
    assert "version" in data
    assert "timestamp" in data
