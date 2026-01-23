"""Test health check endpoint"""

def test_health_check(client):
    """Test that health check endpoint returns 200"""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "identity-service"
    assert "version" in data
    assert "timestamp" in data
