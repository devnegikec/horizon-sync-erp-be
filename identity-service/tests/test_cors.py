"""CORS policy regression tests."""

from fastapi.testclient import TestClient

from app.main import app


def test_local_angular_login_preflight_is_allowed():
    # Preflight is handled entirely by middleware, so no database-backed
    # application lifespan or fixtures are needed.
    client = TestClient(app)
    try:
        response = client.options(
            "/api/v1/identity/login",
            headers={
                "Origin": "http://localhost:4200",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )
    finally:
        client.close()

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4200"
    assert response.headers["access-control-allow-credentials"] == "true"
