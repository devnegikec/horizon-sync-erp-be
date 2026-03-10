"""Integration tests for invoice confirmation endpoint

Tests the POST /api/v1/invoices/{invoice_id}/confirm endpoint
"""

import uuid
from datetime import datetime, UTC
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.base import AccountStatus, AccountType
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.invoice import Invoice
from app.dependencies import CurrentUser


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Provide a test user ID"""
    return uuid.uuid4()


@pytest.fixture
def mock_user_with_invoice_permissions(organization_id, user_id):
    """Create a mock user with invoice permissions"""
    return CurrentUser(
        id=user_id,
        email="test@example.com",
        organization_id=organization_id,
        user_type="user",
        permissions=["invoice.create", "invoice.read", "invoice.update", "invoice.delete"],
    )


@pytest.fixture
def mock_user_without_permissions(organization_id):
    """Create a mock user without invoice permissions"""
    return CurrentUser(
        id=uuid.uuid4(),
        email="noperm@example.com",
        organization_id=organization_id,
        user_type="user",
        permissions=["invoice.read"],  # Only read permission, no update
    )


@pytest.fixture
def client_with_permissions(db_session, mock_user_with_invoice_permissions):
    """Create a test client with invoice permissions"""
    from app.database import get_db
    from app.dependencies import get_current_active_user

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_user():
        return mock_user_with_invoice_permissions

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def client_without_permissions(db_session, mock_user_without_permissions):
    """Create a test client without invoice update permissions"""
    from app.database import get_db
    from app.dependencies import get_current_active_user

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def override_get_current_user():
        return mock_user_without_permissions

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def accounts_receivable_account(db_session, organization_id):
    """Create accounts receivable account"""
    account = Account(
        organization_id=organization_id,
        account_code="1100",
        account_name="Accounts Receivable",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sales_revenue_account(db_session, organization_id):
    """Create sales revenue account"""
    account = Account(
        organization_id=organization_id,
        account_code="4000",
        account_name="Sales Revenue",
        account_type=AccountType.REVENUE,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        created_by="test_user",
        updated_by="test_user",
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def sales_default_accounts(
    db_session,
    organization_id,
    accounts_receivable_account,
    sales_revenue_account,
):
    """Create default accounts for sales invoices"""
    ar_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="accounts_receivable",
        account_id=accounts_receivable_account.id,
    )
    revenue_default = DefaultAccount(
        organization_id=organization_id,
        transaction_type="sales_revenue",
        account_id=sales_revenue_account.id,
    )
    db_session.add(ar_default)
    db_session.add(revenue_default)
    db_session.commit()
    return {
        "accounts_receivable": ar_default,
        "sales_revenue": revenue_default,
    }


@pytest.fixture
def draft_sales_invoice(db_session, organization_id, user_id):
    """Create a draft sales invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-SALES-DRAFT-001",
        invoice_type="Sales",
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="draft",
        grand_total=Decimal("1000.00"),
        currency="USD",
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


@pytest.fixture
def submitted_invoice(db_session, organization_id, user_id):
    """Create an already-submitted invoice"""
    invoice = Invoice(
        organization_id=organization_id,
        invoice_no="INV-SUBMITTED-001",
        invoice_type="Sales",
        party_id=uuid.uuid4(),
        party_type="Customer",
        posting_date=datetime.now(UTC),
        status="submitted",
        grand_total=Decimal("1000.00"),
        outstanding_amount=Decimal("1000.00"),
        currency="USD",
        submitted_at=datetime.now(UTC),
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)
    return invoice


class TestInvoiceConfirmationEndpointSuccess:
    """Tests for successful invoice confirmation via API endpoint
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    def test_confirm_invoice_success(
        self,
        client_with_permissions,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test POST /api/v1/invoices/{invoice_id}/confirm success
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        # Confirm the invoice via API
        response = client_with_permissions.post(
            f"/api/v1/invoices/{draft_sales_invoice.id}/confirm"
        )
        
        # Verify response status code
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        
        # Verify response data
        data = response.json()
        assert data["id"] == str(draft_sales_invoice.id)
        assert data["status"] == "submitted"
        assert data["submitted_at"] is not None
        assert data["outstanding_amount"] == "1000.00"
        assert data["grand_total"] == "1000.00"


class TestInvoiceConfirmationEndpointValidation:
    """Tests for invoice confirmation endpoint validation
    
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
    """

    def test_confirm_with_invalid_invoice_id(
        self,
        client_with_permissions,
    ):
        """Test confirmation with invalid invoice_id returns 404
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        # Attempt to confirm non-existent invoice
        nonexistent_id = uuid.uuid4()
        response = client_with_permissions.post(
            f"/api/v1/invoices/{nonexistent_id}/confirm"
        )
        
        # Verify 404 response
        assert response.status_code == 404, f"Expected 404, got {response.status_code}: {response.text}"
        
        # Verify error message
        data = response.json()
        # The error response may have different formats, check both
        error_message = data.get("detail", data.get("message", ""))
        assert "not found" in str(error_message).lower() or str(nonexistent_id) in str(error_message)

    def test_confirm_already_submitted_invoice(
        self,
        client_with_permissions,
        submitted_invoice,
        sales_default_accounts,
    ):
        """Test confirmation with already-submitted invoice returns 400
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        # Attempt to confirm already-submitted invoice
        response = client_with_permissions.post(
            f"/api/v1/invoices/{submitted_invoice.id}/confirm"
        )
        
        # Verify 400 response
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Verify error message mentions status
        data = response.json()
        error_message = data.get("detail", data.get("message", ""))
        assert "draft" in str(error_message).lower() or "submitted" in str(error_message).lower()

    def test_confirm_without_default_accounts(
        self,
        client_with_permissions,
        draft_sales_invoice,
    ):
        """Test confirmation without default accounts returns 400
        
        **Validates: Requirements 2.1, 2.2**
        """
        # Attempt to confirm invoice without default accounts configured
        response = client_with_permissions.post(
            f"/api/v1/invoices/{draft_sales_invoice.id}/confirm"
        )
        
        # Verify 400 response
        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        
        # Verify error message mentions missing accounts or configuration
        data = response.json()
        error_message = data.get("detail", data.get("message", ""))
        assert "not configured" in str(error_message).lower() or "required" in str(error_message).lower() or "default account" in str(error_message).lower()

    def test_confirm_without_proper_permissions(
        self,
        client_without_permissions,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test confirmation without proper permissions returns 403
        
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**
        """
        # Attempt to confirm invoice without update permission
        response = client_without_permissions.post(
            f"/api/v1/invoices/{draft_sales_invoice.id}/confirm"
        )
        
        # Verify 403 response
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        
        # Verify error message mentions permission
        data = response.json()
        assert "permission" in data["detail"].lower() or "forbidden" in data["detail"].lower()


class TestInvoiceConfirmationEndpointResponseStructure:
    """Tests for invoice confirmation endpoint response structure"""

    def test_confirm_response_includes_all_fields(
        self,
        client_with_permissions,
        draft_sales_invoice,
        sales_default_accounts,
    ):
        """Test that confirmation response includes all required fields"""
        # Confirm the invoice via API
        response = client_with_permissions.post(
            f"/api/v1/invoices/{draft_sales_invoice.id}/confirm"
        )
        
        # Verify response status code
        assert response.status_code == 200
        
        # Verify response includes all required fields
        data = response.json()
        assert "id" in data
        assert "invoice_no" in data
        assert "status" in data
        assert "submitted_at" in data
        assert "outstanding_amount" in data
        assert "grand_total" in data
        assert "invoice_type" in data
        assert "party_id" in data
        assert "posting_date" in data
        assert "currency" in data
        
        # Verify submitted_at is not None
        assert data["submitted_at"] is not None
        
        # Verify outstanding_amount equals grand_total
        assert data["outstanding_amount"] == data["grand_total"]
