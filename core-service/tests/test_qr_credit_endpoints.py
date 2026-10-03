"""Security and Organization-isolation tests for QR-credit endpoints."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.endpoints.qr_credits import (
    add_admin_organization_credits,
    get_organization_credit_balance,
    get_organization_credit_ledger,
)
from app.dependencies import CurrentUser
from app.schemas.qr_credit import QRCreditAddRequest


def organization_user(organization_id):
    return CurrentUser(
        id=uuid4(),
        email="organization-user@example.com",
        organization_id=organization_id,
        user_type="user",
        permissions=["qr_product.read"],
    )


@pytest.mark.asyncio
async def test_balance_uses_authenticated_users_organization_only():
    own_organization_id = uuid4()
    another_organization_id = uuid4()
    user = organization_user(own_organization_id)

    with patch(
        "app.api.v1.endpoints.qr_credits.CreditService"
    ) as service_class:
        service_class.return_value.get_balance.return_value = None
        response = await get_organization_credit_balance(
            current_user=user,
            db=MagicMock(),
        )

    assert response.organization_id == own_organization_id
    assert response.organization_id != another_organization_id
    service_class.return_value.get_balance.assert_called_once_with(
        own_organization_id
    )


@pytest.mark.asyncio
async def test_ledger_uses_authenticated_users_organization_only():
    own_organization_id = uuid4()
    user = organization_user(own_organization_id)

    with patch(
        "app.api.v1.endpoints.qr_credits.CreditService"
    ) as service_class:
        service_class.return_value.list_ledger.return_value = (
            [],
            {
                "page": 1,
                "page_size": 20,
                "total_items": 0,
                "total_pages": 1,
                "has_next": False,
                "has_prev": False,
            },
        )
        response = await get_organization_credit_ledger(
            page=1,
            page_size=20,
            current_user=user,
            db=MagicMock(),
        )

    assert response.transactions == []
    service_class.return_value.list_ledger.assert_called_once_with(
        own_organization_id, 1, 20
    )


@pytest.mark.asyncio
async def test_system_admin_addition_records_admin_and_validates_organization():
    organization_id = uuid4()
    admin = CurrentUser(
        id=uuid4(),
        email="system-admin@example.com",
        organization_id=None,
        user_type="system_admin",
        permissions=["*.*"],
    )
    request = QRCreditAddRequest(
        amount=1000,
        reason="Annual QR credit package",
        reference_id=uuid4(),
    )
    balance = SimpleNamespace(
        organization_id=organization_id,
        total_credits=1000,
        used_credits=0,
        balance_credits=1000,
        updated_at=None,
    )

    with (
        patch(
            "app.api.v1.endpoints.qr_credits.AdminOrganizationService"
        ) as organization_service_class,
        patch(
            "app.api.v1.endpoints.qr_credits.CreditService"
        ) as credit_service_class,
    ):
        organization_service_class.return_value.get_organization = AsyncMock()
        credit_service_class.return_value.add_credits.return_value = balance

        response = await add_admin_organization_credits(
            organization_id=organization_id,
            data=request,
            credentials=HTTPAuthorizationCredentials(
                scheme="Bearer", credentials="admin-token"
            ),
            current_user=admin,
            db=MagicMock(),
        )

    organization_service_class.assert_called_once()
    organization_service_class.return_value.get_organization.assert_awaited_once_with(
        organization_id
    )
    credit_service_class.return_value.add_credits.assert_called_once_with(
        organization_id=organization_id,
        amount=1000,
        reason="Annual QR credit package",
        reference_id=request.reference_id,
        user_id=admin.id,
    )
    assert response.balance_credits == 1000
