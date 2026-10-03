"""CORS policy regression tests."""

from app.config import settings


def test_local_angular_dashboard_origin_is_allowed():
    assert "http://localhost:4200" in settings.cors_origins_list
