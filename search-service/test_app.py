"""Simple test to verify FastAPI app works"""

import os
import sys

# Set environment variables
os.environ["DATABASE_URL"] = "sqlite:///test.db"
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint"""
    print("Testing health check endpoint...")
    response = client.get("/health")
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "search-service"
    print("✓ Health check works")


if __name__ == "__main__":
    print("Running FastAPI app tests...\n")
    try:
        test_health_check()
        print("\n✅ All tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
