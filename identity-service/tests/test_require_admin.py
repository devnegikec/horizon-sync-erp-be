"""Tests for the require_admin dependency."""

import pytest
from uuid import uuid4

from fastapi import HTTPException

from app.dependencies import CurrentUser, require_admin
from app.models.base import UserType, UserStatus


def _make_user(user_type: UserType) -> CurrentUser:
    """Create a CurrentUser with the given user_type."""
    return CurrentUser(
        id=uuid4(),
        email="test@example.com",
        first_name="Test",
        last_name="User",
        display_name="Test User",
        user_type=user_type,
        status=UserStatus.ACTIVE,
        is_active=True,
        permissions=["some:permission"],
    )


@pytest.mark.asyncio
async def test_require_admin_allows_system_admin():
    """System admin users should pass through unchanged."""
    admin_user = _make_user(UserType.SYSTEM_ADMIN)
    result = await require_admin(current_user=admin_user)
    assert result is admin_user


@pytest.mark.asyncio
async def test_require_admin_rejects_regular_user():
    """Regular users should get a 403."""
    user = _make_user(UserType.USER)
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_rejects_org_admin():
    """Organization admins should get a 403."""
    user = _make_user(UserType.ORGANIZATION_ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_rejects_guest():
    """Guest users should get a 403."""
    user = _make_user(UserType.GUEST)
    with pytest.raises(HTTPException) as exc_info:
        await require_admin(current_user=user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
async def test_require_admin_preserves_user_data():
    """The returned user should have all original fields intact."""
    admin_user = _make_user(UserType.SYSTEM_ADMIN)
    result = await require_admin(current_user=admin_user)
    assert result.id == admin_user.id
    assert result.email == admin_user.email
    assert result.user_type == UserType.SYSTEM_ADMIN
    assert result.permissions == admin_user.permissions
