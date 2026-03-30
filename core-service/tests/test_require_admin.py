"""Tests for the core-service require_admin dependency."""

from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.dependencies import CurrentUser, require_admin


def _make_user(user_type: str) -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="test@example.com",
        organization_id=uuid4(),
        user_type=user_type,
        permissions=["item.read"],
    )


@pytest.mark.asyncio
async def test_require_admin_allows_system_admin():
    """System admin users should pass through unchanged."""
    admin_user = _make_user("system_admin")
    result = await require_admin(current_user=admin_user)
    assert result is admin_user


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    """Regular users should get a 403."""
    user = _make_user("user")
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_rejects_org_admin():
    """Organization admins should get a 403."""
    user = _make_user("org_admin")
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_preserves_user_data():
    """The returned user should have all original fields intact."""
    admin_user = _make_user("system_admin")
    result = await require_admin(current_user=admin_user)
    assert result.id == admin_user.id
    assert result.email == admin_user.email
    assert result.organization_id == admin_user.organization_id
    assert result.user_type == "system_admin"
    assert result.permissions == admin_user.permissions
