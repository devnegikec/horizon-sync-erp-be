"""Tests for integration API endpoints"""

import pytest
from uuid import uuid4
from fastapi import status

from app.models.base import AccountType, AccountStatus


class TestIntegrationAPI:
    """Test integration API endpoints for other ERP modules"""

    def test_validate_posting_by_query_param_success(
        self, client, auth_headers, sample_account
    ):
        """Test validating a posting account using query parameter"""
        response = client.post(
            "/api/v1/accounts/validate-posting",
            params={"account_id": str(sample_account.id)},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_validate_posting_by_query_param_inactive_account(
        self, client, auth_headers, sample_account, db_session
    ):
        """Test validating an inactive account fails"""
        # Deactivate the account
        sample_account.status = AccountStatus.INACTIVE
        db_session.commit()

        response = client.post(
            "/api/v1/accounts/validate-posting",
            params={"account_id": str(sample_account.id)},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_posting_by_query_param_parent_account(
        self, client, auth_headers, sample_parent_account, db_session
    ):
        """Test validating a parent account fails"""
        response = client.post(
            "/api/v1/accounts/validate-posting",
            params={"account_id": str(sample_parent_account.id)},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_validate_posting_by_query_param_not_found(
        self, client, auth_headers
    ):
        """Test validating a non-existent account"""
        fake_id = uuid4()
        response = client.post(
            "/api/v1/accounts/validate-posting",
            params={"account_id": str(fake_id)},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_bulk_validate_posting_accounts(
        self, client, auth_headers, sample_account, sample_parent_account, db_session, mock_current_user
    ):
        """Test bulk validation of multiple accounts"""
        # Create another valid account
        from app.models.chart_of_account import Account
        
        valid_account2 = Account(
            account_code="2000-02",
            account_name="Valid Account 2",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=sample_account.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(valid_account2)
        db_session.commit()

        # Test with mix of valid and invalid accounts
        account_ids = [
            str(sample_account.id),  # Valid
            str(valid_account2.id),  # Valid
            str(sample_parent_account.id),  # Invalid (parent)
            str(uuid4()),  # Invalid (not found)
        ]

        response = client.post(
            "/api/v1/accounts/validate-posting/bulk",
            params={"account_ids": account_ids},
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["valid_count"] == 2
        assert data["invalid_count"] == 2
        assert str(sample_account.id) in data["valid"]
        assert str(valid_account2.id) in data["valid"]
        assert len(data["invalid"]) == 2

    def test_get_account_by_code_success(
        self, client, auth_headers, sample_account
    ):
        """Test getting account by code"""
        response = client.get(
            f"/api/v1/accounts/by-code/{sample_account.account_code}",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["account_code"] == sample_account.account_code
        assert data["account_name"] == sample_account.account_name
        assert data["id"] == str(sample_account.id)

    def test_get_account_by_code_not_found(
        self, client, auth_headers
    ):
        """Test getting account by non-existent code"""
        response = client.get(
            "/api/v1/accounts/by-code/NONEXISTENT",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    def test_get_default_account_success(
        self, client, auth_headers, sample_account, db_session
    ):
        """Test getting default account for transaction type"""
        from app.models.default_account import DefaultAccount
        
        # Create a default account mapping
        default = DefaultAccount(
            transaction_type="inventory_purchase",
            account_id=sample_account.id,
            organization_id=sample_account.organization_id,
        )
        db_session.add(default)
        db_session.commit()

        response = client.post(
            "/api/v1/accounts/default/inventory_purchase",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_account.id)
        assert data["account_code"] == sample_account.account_code

    def test_get_default_account_with_scenario(
        self, client, auth_headers, sample_account, db_session, mock_current_user
    ):
        """Test getting default account with scenario"""
        from app.models.default_account import DefaultAccount
        
        # Create default accounts for different scenarios
        default_domestic = DefaultAccount(
            transaction_type="sales_revenue",
            scenario="domestic",
            account_id=sample_account.id,
            organization_id=sample_account.organization_id,
        )
        db_session.add(default_domestic)
        
        # Create another account for international
        from app.models.chart_of_account import Account
        intl_account = Account(
            account_code="4000-02",
            account_name="International Sales",
            account_type=AccountType.INCOME,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=sample_account.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(intl_account)
        db_session.flush()
        
        default_intl = DefaultAccount(
            transaction_type="sales_revenue",
            scenario="international",
            account_id=intl_account.id,
            organization_id=sample_account.organization_id,
        )
        db_session.add(default_intl)
        db_session.commit()

        # Test domestic scenario
        response = client.post(
            "/api/v1/accounts/default/sales_revenue",
            params={"scenario": "domestic"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(sample_account.id)

        # Test international scenario
        response = client.post(
            "/api/v1/accounts/default/sales_revenue",
            params={"scenario": "international"},
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["id"] == str(intl_account.id)

    def test_get_default_account_not_configured(
        self, client, auth_headers
    ):
        """Test getting default account when not configured"""
        response = client.post(
            "/api/v1/accounts/default/unconfigured_type",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        detail = response.json()["detail"].lower()
        assert "default account" in detail and "configured" in detail

    def test_get_default_account_invalid_account(
        self, client, auth_headers, db_session, mock_current_user
    ):
        """Test getting default account when configured account is deleted"""
        from app.models.default_account import DefaultAccount
        
        # Create a default account mapping with non-existent account
        fake_account_id = uuid4()
        default = DefaultAccount(
            transaction_type="test_type",
            account_id=fake_account_id,
            organization_id=mock_current_user.organization_id,
        )
        db_session.add(default)
        db_session.commit()

        response = client.post(
            "/api/v1/accounts/default/test_type",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "not found" in response.json()["detail"].lower()

    def test_deprecated_validate_posting_endpoint(
        self, client, auth_headers, sample_account
    ):
        """Test the deprecated validate posting endpoint still works"""
        response = client.post(
            f"/api/v1/accounts/{sample_account.id}/validate-posting",
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestIntegrationAPIEdgeCases:
    """Test edge cases for integration API"""

    def test_bulk_validate_empty_list(
        self, client, auth_headers
    ):
        """Test bulk validation with empty list"""
        response = client.post(
            "/api/v1/accounts/validate-posting/bulk",
            params={"account_ids": []},
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid_count"] == 0
        assert data["invalid_count"] == 0

    def test_bulk_validate_large_list(
        self, client, auth_headers, sample_account, db_session, mock_current_user
    ):
        """Test bulk validation with many accounts"""
        from app.models.chart_of_account import Account
        
        # Create 50 valid accounts
        accounts = []
        for i in range(50):
            account = Account(
                account_code=f"TEST-{i:04d}",
                account_name=f"Test Account {i}",
                account_type=AccountType.ASSET,
                currency="USD",
                status=AccountStatus.ACTIVE,
                is_posting_account=True,
                organization_id=sample_account.organization_id,
                created_by=str(mock_current_user.id),
                updated_by=str(mock_current_user.id),
            )
            accounts.append(account)
            db_session.add(account)
        
        db_session.commit()
        
        account_ids = [str(acc.id) for acc in accounts]
        
        response = client.post(
            "/api/v1/accounts/validate-posting/bulk",
            params={"account_ids": account_ids},
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid_count"] == 50
        assert data["invalid_count"] == 0

    def test_get_account_by_code_special_characters(
        self, client, auth_headers, db_session, mock_current_user
    ):
        """Test getting account by code with special characters"""
        from app.models.chart_of_account import Account
        
        # Create account with dash and underscore (common special characters)
        account = Account(
            account_code="1000-A_B",
            account_name="Special Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            organization_id=mock_current_user.organization_id,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        db_session.commit()

        response = client.get(
            f"/api/v1/accounts/by-code/1000-A_B",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["account_code"] == "1000-A_B"

    def test_get_default_account_case_sensitivity(
        self, client, auth_headers, sample_account, db_session
    ):
        """Test that transaction type is case-sensitive"""
        from app.models.default_account import DefaultAccount
        
        # Create default with lowercase
        default = DefaultAccount(
            transaction_type="inventory_purchase",
            account_id=sample_account.id,
            organization_id=sample_account.organization_id,
        )
        db_session.add(default)
        db_session.commit()

        # Try with uppercase - should not find it
        response = client.post(
            "/api/v1/accounts/default/INVENTORY_PURCHASE",
            headers=auth_headers,
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
