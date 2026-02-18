"""Tests for default account configuration API endpoints"""

import pytest
from uuid import uuid4

from app.models.base import AccountType, AccountStatus
from app.models.chart_of_account import Account
from app.models.default_account import DefaultAccount
from app.models.system_config import SystemConfig


@pytest.fixture
def sample_accounts(db_session, mock_current_user):
    """Create sample accounts for testing"""
    accounts = []
    
    # Create accounts of different types
    account_data = [
        ("1000", "Cash", AccountType.ASSET),
        ("2000", "Accounts Payable", AccountType.LIABILITY),
        ("4000", "Sales Revenue", AccountType.INCOME),
        ("5000", "Cost of Goods Sold", AccountType.EXPENSE),
    ]
    
    for code, name, acc_type in account_data:
        account = Account(
            account_code=code,
            account_name=name,
            account_type=acc_type,
            organization_id=mock_current_user.organization_id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by=str(mock_current_user.id),
            updated_by=str(mock_current_user.id),
        )
        db_session.add(account)
        accounts.append(account)
    
    db_session.commit()
    
    for account in accounts:
        db_session.refresh(account)
    
    return accounts


class TestGetDefaultAccounts:
    """Tests for GET /api/v1/accounts/config/defaults"""
    
    def test_get_empty_defaults(self, client):
        """Test getting defaults when none are configured"""
        response = client.get(
            "/api/v1/accounts/config/defaults",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_all_defaults(
        self, 
        client, 
        db_session, 
        mock_current_user,
        sample_accounts,
    ):
        """Test getting all default accounts"""
        # Create some defaults
        defaults = [
            DefaultAccount(
                transaction_type="inventory_purchase",
                scenario=None,
                account_id=sample_accounts[0].id,
                organization_id=mock_current_user.organization_id,
            ),
            DefaultAccount(
                transaction_type="sales_revenue",
                scenario="domestic",
                account_id=sample_accounts[2].id,
                organization_id=mock_current_user.organization_id,
            ),
        ]
        
        for default in defaults:
            db_session.add(default)
        db_session.commit()
        
        response = client.get(
            "/api/v1/accounts/config/defaults",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Check first default
        assert data[0]["transaction_type"] == "inventory_purchase"
        assert data[0]["scenario"] is None
        assert data[0]["account_code"] == "1000"
        assert data[0]["account_name"] == "Cash"
        
        # Check second default
        assert data[1]["transaction_type"] == "sales_revenue"
        assert data[1]["scenario"] == "domestic"
        assert data[1]["account_code"] == "4000"
    
    def test_filter_by_transaction_type(
        self,
        client,
        db_session,
        mock_current_user,
        sample_accounts,
    ):
        """Test filtering defaults by transaction type"""
        # Create defaults
        defaults = [
            DefaultAccount(
                transaction_type="inventory_purchase",
                account_id=sample_accounts[0].id,
                organization_id=mock_current_user.organization_id,
            ),
            DefaultAccount(
                transaction_type="sales_revenue",
                account_id=sample_accounts[2].id,
                organization_id=mock_current_user.organization_id,
            ),
        ]
        
        for default in defaults:
            db_session.add(default)
        db_session.commit()
        
        response = client.get(
            "/api/v1/accounts/config/defaults?transaction_type=inventory_purchase",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["transaction_type"] == "inventory_purchase"


class TestUpdateDefaultAccounts:
    """Tests for PUT /api/v1/accounts/config/defaults"""
    
    def test_create_single_default(self, client, sample_accounts):
        """Test creating a single default account mapping"""
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    "account_id": str(sample_accounts[0].id),
                }
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["error_count"] == 0
        assert len(data["updated"]) == 1
        assert data["updated"][0]["transaction_type"] == "inventory_purchase"
    
    def test_create_multiple_defaults(self, client, sample_accounts):
        """Test creating multiple default account mappings"""
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    "account_id": str(sample_accounts[0].id),
                },
                {
                    "transaction_type": "sales_revenue",
                    "scenario": "domestic",
                    "account_id": str(sample_accounts[2].id),
                },
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 0
    
    def test_update_existing_default(
        self,
        client,
        db_session,
        mock_current_user,
        sample_accounts,
    ):
        """Test updating an existing default account mapping"""
        # Create initial default
        default = DefaultAccount(
            transaction_type="inventory_purchase",
            account_id=sample_accounts[0].id,
            organization_id=mock_current_user.organization_id,
        )
        db_session.add(default)
        db_session.commit()
        
        # Update to different account
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    "account_id": str(sample_accounts[3].id),  # Different account
                }
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["updated"][0]["account_id"] == str(sample_accounts[3].id)
    
    def test_invalid_account_type(self, client, sample_accounts):
        """Test that invalid account type for transaction type is rejected"""
        # Try to use LIABILITY account for sales_revenue (should be INCOME)
        payload = {
            "defaults": [
                {
                    "transaction_type": "sales_revenue",
                    "account_id": str(sample_accounts[1].id),  # Liability account
                }
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 0
        assert data["error_count"] == 1
        assert "not appropriate" in data["errors"][0]["error"].lower()
    
    def test_missing_required_fields(self, client):
        """Test that missing required fields are rejected"""
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    # Missing account_id
                }
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["error_count"] == 1
        assert "account_id" in data["errors"][0]["error"].lower()
    
    def test_invalid_account_id(self, client):
        """Test that invalid account ID is rejected"""
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    "account_id": "invalid-uuid",
                }
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["error_count"] == 1
        assert "invalid" in data["errors"][0]["error"].lower()
    
    def test_nonexistent_account(self, client):
        """Test that nonexistent account is rejected"""
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    "account_id": str(uuid4()),  # Random UUID
                }
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["error_count"] == 1
        assert "not found" in data["errors"][0]["error"].lower()
    
    def test_partial_success(self, client, sample_accounts):
        """Test that some defaults succeed while others fail"""
        payload = {
            "defaults": [
                {
                    "transaction_type": "inventory_purchase",
                    "account_id": str(sample_accounts[0].id),  # Valid
                },
                {
                    "transaction_type": "sales_revenue",
                    "account_id": str(uuid4()),  # Invalid - nonexistent
                },
            ]
        }
        
        response = client.put(
            "/api/v1/accounts/config/defaults",
            json=payload,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["error_count"] == 1


class TestGetAccountCodeFormat:
    """Tests for GET /api/v1/accounts/config/format"""
    
    def test_get_default_format(self, client):
        """Test getting default format when not configured"""
        response = client.get(
            "/api/v1/accounts/config/format",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "format_pattern" in data
        assert data["format_pattern"] == "^[0-9]{4}-[0-9]{2}$"
        assert data["example"] == "1000-01"
    
    def test_get_configured_format(self, client, db_session, mock_current_user):
        """Test getting configured format"""
        # Set custom format
        config = SystemConfig(
            key="account_code_format",
            value="^[0-9]{4}$",
            updated_by=str(mock_current_user.id),
        )
        db_session.add(config)
        db_session.commit()
        
        response = client.get(
            "/api/v1/accounts/config/format",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format_pattern"] == "^[0-9]{4}$"
        assert data["example"] == "1000"


class TestUpdateAccountCodeFormat:
    """Tests for PUT /api/v1/accounts/config/format"""
    
    def test_update_format(self, client):
        """Test updating account code format"""
        response = client.put(
            "/api/v1/accounts/config/format?format_pattern=^[0-9]{4}$",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format_pattern"] == "^[0-9]{4}$"
        assert "updated_at" in data
        assert "updated_by" in data
    
    def test_update_format_creates_if_not_exists(
        self,
        client,
        db_session,
    ):
        """Test that updating format creates config if it doesn't exist"""
        # Ensure no config exists
        db_session.query(SystemConfig).filter(
            SystemConfig.key == "account_code_format"
        ).delete()
        db_session.commit()
        
        response = client.put(
            "/api/v1/accounts/config/format?format_pattern=^[A-Z]{2}-[0-9]{4}$",
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["format_pattern"] == "^[A-Z]{2}-[0-9]{4}$"
        
        # Verify it was created in database
        config = db_session.query(SystemConfig).filter(
            SystemConfig.key == "account_code_format"
        ).first()
        assert config is not None
        assert config.value == "^[A-Z]{2}-[0-9]{4}$"
    
    def test_invalid_regex_pattern(self, client):
        """Test that invalid regex pattern is rejected"""
        response = client.put(
            "/api/v1/accounts/config/format?format_pattern=[invalid(regex",
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "invalid regex" in data["detail"].lower()
    
    def test_update_format_multiple_times(self, client):
        """Test updating format multiple times"""
        # First update
        response1 = client.put(
            "/api/v1/accounts/config/format?format_pattern=^[0-9]{4}$",
        )
        assert response1.status_code == 200
        
        # Second update
        response2 = client.put(
            "/api/v1/accounts/config/format?format_pattern=^[0-9]{6}$",
        )
        assert response2.status_code == 200
        data = response2.json()
        assert data["format_pattern"] == "^[0-9]{6}$"
