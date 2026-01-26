"""Health check endpoint tests"""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch


def test_health_check(client):
    """Test the health check endpoint returns healthy status"""
    # Create a mock connection that works as a context manager
    mock_conn = MagicMock()
    mock_conn.execute = MagicMock(return_value=None)

    @contextmanager
    def mock_connect():
        yield mock_conn

    # Mock the database engine's connect method
    with patch("app.main.engine.connect", side_effect=mock_connect):
        response = client.get("/health")

        # Should return 200 OK
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "core-service"
        assert data["status"] == "healthy"
        assert "version" in data
        assert "timestamp" in data
        assert data["database"] == "connected"
