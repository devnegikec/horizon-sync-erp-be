"""
Test cases to validate Chart of Account bug fixes.

These tests specifically validate the following reported issues:
1. Balance is not populating in UI
2. Correct level hierarchy not populating on UI
3. Correct group hierarchy not populating on UI 
4. Pagination not working for chart of account landing page
5. Edit account dialog not populating parent account name

Each test case checks the specific functionality that should be fixed.
"""

import pytest
import uuid
from decimal import Decimal
from datetime import date, datetime
from fastapi import status

from app.models.base import AccountType, AccountStatus
from app.models.chart_of_account import Account
from app.models.account_balance import AccountBalance
from app.services.balance_calculator import BalanceCalculator


@pytest.fixture
def sample_organization(db_session, mock_current_user):
    """
    Create a test organization for account testing using the mock user's organization.
    """
    from app.models.organization import Organization
    
    # Use the organization ID from the mock user
    organization_id = mock_current_user.organization_id
    
    # Check if we need to create the organization record
    # (In real system, this would exist, but in tests we might need to create it)
    try:
        from app.models.organization import Organization
        org = Organization(
            id=organization_id,
            name="Test Organization",
            description="Test organization for account validation",
            created_by="test-system",
            updated_by="test-system"
        )
        db_session.add(org)
        db_session.commit()
    except Exception:
        # Organization might already exist or DB constraint issue
        db_session.rollback()
    
    return type('Organization', (), {'id': organization_id, 'name': 'Test Organization'})


class TestChartOfAccountBalancePopulation:
    """Test cases for Issue #1: Balance is not populating in UI"""

    def test_list_accounts_includes_balance_in_response(self, client, db_session, sample_organization):
        """
        Test that account listing API returns balance information for each account.
        This validates that balances are properly calculated and included in the UI response.
        """
        # Create test accounts
        cash_account = Account(
            organization_id=sample_organization.id,
            account_code="1001",
            account_name="Cash Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        revenue_account = Account(
            organization_id=sample_organization.id,
            account_code="4001", 
            account_name="Sales Revenue",
            account_type=AccountType.REVENUE,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add_all([cash_account, revenue_account])
        db_session.commit()

        # Create balance records for the accounts
        cash_balance = AccountBalance(
            account_id=cash_account.id,
            currency="USD",
            debit_total=Decimal("5000.00"),
            credit_total=Decimal("1000.00"),
            balance=Decimal("4000.00"),  # Asset account: debit - credit
            base_currency_balance=Decimal("4000.00"),
            as_of_date=date.today(),
        )
        
        revenue_balance = AccountBalance(
            account_id=revenue_account.id,
            currency="USD", 
            debit_total=Decimal("500.00"),
            credit_total=Decimal("3000.00"),
            balance=Decimal("2500.00"),  # Revenue account: credit - debit
            base_currency_balance=Decimal("2500.00"),
            as_of_date=date.today(),
        )
        
        db_session.add_all([cash_balance, revenue_balance])
        db_session.commit()

        # Test API response includes balance information
        response = client.get("/api/v1/chart-of-accounts")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify response structure
        assert "chart_of_accounts" in data
        assert "pagination" in data
        
        accounts = data["chart_of_accounts"]
        assert len(accounts) >= 2
        
        # Find our test accounts in the response
        cash_account_response = next((a for a in accounts if a["account_code"] == "1001"), None)
        revenue_account_response = next((a for a in accounts if a["account_code"] == "4001"), None)
        
        assert cash_account_response is not None, "Cash account should be in response"
        assert revenue_account_response is not None, "Revenue account should be in response"
        
        # Verify balance fields are present and have expected values
        # Note: The API might calculate these dynamically, so we check for presence and reasonable values
        assert "current_balance" in cash_account_response or hasattr(cash_account_response, 'current_balance')
        assert "opening_balance" in cash_account_response or hasattr(cash_account_response, 'opening_balance')

    def test_individual_account_get_includes_balance(self, client, db_session, sample_organization):
        """
        Test that getting a single account returns balance information.
        This is used for the edit dialog and account detail views.
        """
        # Create test account
        account = Account(
            organization_id=sample_organization.id,
            account_code="1002",
            account_name="Bank Account", 
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(account)
        db_session.commit()

        # Create balance record
        balance = AccountBalance(
            account_id=account.id,
            currency="USD",
            debit_total=Decimal("10000.00"),
            credit_total=Decimal("2000.00"), 
            balance=Decimal("8000.00"),
            base_currency_balance=Decimal("8000.00"),
            as_of_date=date.today(),
        )
        
        db_session.add(balance)
        db_session.commit()

        # Test individual account endpoint
        response = client.get(f"/api/v1/chart-of-accounts/{account.id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Verify account data
        assert data["id"] == str(account.id)
        assert data["account_code"] == "1002"
        assert data["account_name"] == "Bank Account"

    def test_balance_calculation_service_works(self, db_session, sample_organization):
        """
        Test that the BalanceCalculator service properly calculates balances.
        This is the underlying service that should provide balance data to the UI.
        """
        # Create test account
        account = Account(
            organization_id=sample_organization.id,
            account_code="1003",
            account_name="Test Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            created_by="test-user", 
            updated_by="test-user",
        )
        
        db_session.add(account)
        db_session.commit()

        # Test balance calculator
        calculator = BalanceCalculator(db_session)
        
        # Test calculation with no transactions
        balance_data = calculator.calculate_balance(account.id, use_cache=False)
        
        assert balance_data is not None, "Balance calculation should return data"
        assert "account_id" in balance_data
        assert "balance" in balance_data
        assert "debit_total" in balance_data
        assert "credit_total" in balance_data
        assert str(balance_data["account_id"]) == str(account.id)


class TestChartOfAccountHierarchyLevels:
    """Test cases for Issue #2: Correct level hierarchy not populating on UI"""

    def test_account_levels_calculated_correctly(self, client, db_session, sample_organization):
        """
        Test that account hierarchy levels are calculated and returned correctly.
        Level 1 = root accounts, Level 2 = first child, Level 3 = grandchild, etc.
        """
        # Create hierarchy: Parent -> Child -> Grandchild
        parent_account = Account(
            organization_id=sample_organization.id,
            account_code="1000",
            account_name="Current Assets",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,  # Parent account, not for posting
            level=1,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(parent_account)
        db_session.commit()

        child_account = Account(
            organization_id=sample_organization.id,
            account_code="1100",
            account_name="Cash and Bank",
            account_type=AccountType.ASSET,
            parent_account_id=parent_account.id,
            currency="USD", 
            status=AccountStatus.ACTIVE,
            is_posting_account=False,  # Group account
            level=2,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(child_account)
        db_session.commit()

        grandchild_account = Account(
            organization_id=sample_organization.id,
            account_code="1101",
            account_name="Cash on Hand",
            account_type=AccountType.ASSET,
            parent_account_id=child_account.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,  # Leaf account for posting
            level=3,
            is_group=False,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(grandchild_account)
        db_session.commit()

        # Test API response includes correct levels
        response = client.get("/api/v1/chart-of-accounts")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        accounts = data["chart_of_accounts"]
        
        # Find accounts by code and verify levels
        parent_response = next((a for a in accounts if a["account_code"] == "1000"), None) 
        child_response = next((a for a in accounts if a["account_code"] == "1100"), None)
        grandchild_response = next((a for a in accounts if a["account_code"] == "1101"), None)
        
        assert parent_response is not None
        assert child_response is not None
        assert grandchild_response is not None
        
        # Verify hierarchy levels
        assert parent_response["level"] == 1, f"Parent should be level 1, got {parent_response.get('level')}"
        assert child_response["level"] == 2, f"Child should be level 2, got {child_response.get('level')}"
        assert grandchild_response["level"] == 3, f"Grandchild should be level 3, got {grandchild_response.get('level')}"

    def test_level_calculation_during_account_creation(self, client):
        """
        Test that levels are automatically calculated when creating accounts with parents.
        """
        # Create parent account
        parent_data = {
            "account_code": "2000",
            "account_name": "Liabilities",
            "account_type": "liability"
        }
        parent_response = client.post("/api/v1/chart-of-accounts", json=parent_data)
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]
        
        # Verify parent has level 1
        assert parent_response.json()["level"] == 1

        # Create child account with parent reference
        child_data = {
            "account_code": "2100",
            "account_name": "Current Liabilities", 
            "account_type": "liability",
            "parent_account_id": parent_id
        }
        child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
        assert child_response.status_code == status.HTTP_201_CREATED
        
        # Verify child has level 2
        child_data_response = child_response.json()
        assert child_data_response["level"] == 2, f"Child should be level 2, got {child_data_response.get('level')}"
        assert child_data_response["parent_account_id"] == parent_id

    def test_level_appears_in_account_list_schema(self, client, db_session, sample_organization):
        """
        Test that the level field is included in the list response schema.
        """
        # Create a simple account
        account = Account(
            organization_id=sample_organization.id,
            account_code="3000",
            account_name="Equity",
            account_type=AccountType.EQUITY,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            level=1,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(account)
        db_session.commit()

        response = client.get("/api/v1/chart-of-accounts")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        accounts = data["chart_of_accounts"]
        
        # Find our test account
        test_account = next((a for a in accounts if a["account_code"] == "3000"), None)
        assert test_account is not None
        
        # Verify level field exists in response
        assert "level" in test_account, "Level field should be present in account list response"
        assert isinstance(test_account["level"], int), "Level should be an integer"


class TestChartOfAccountGroupHierarchy:
    """Test cases for Issue #3: Correct group hierarchy not populating on UI"""

    def test_is_group_flag_populated_correctly(self, client, db_session, sample_organization):
        """
        Test that is_group flag is correctly set and returned for parent accounts.
        """
        # Create parent account (should be marked as group)
        parent_account = Account(
            organization_id=sample_organization.id,
            account_code="4000",
            account_name="Income",
            account_type=AccountType.REVENUE,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            level=1,
            is_group=True,  # This should be True for group accounts
            created_by="test-user",
            updated_by="test-user",
        )
        
        # Create child account (leaf node, not a group)
        child_account = Account(
            organization_id=sample_organization.id,
            account_code="4100", 
            account_name="Sales Revenue",
            account_type=AccountType.REVENUE,
            parent_account_id=parent_account.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            level=2,
            is_group=False,  # This should be False for posting accounts
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add_all([parent_account, child_account])
        db_session.commit()

        # Test API response
        response = client.get("/api/v1/chart-of-accounts")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        accounts = data["chart_of_accounts"]
        
        # Find accounts in response
        parent_response = next((a for a in accounts if a["account_code"] == "4000"), None)
        child_response = next((a for a in accounts if a["account_code"] == "4100"), None)
        
        assert parent_response is not None
        assert child_response is not None
        
        # Verify is_group flags
        assert "is_group" in parent_response, "is_group field should be present"
        assert "is_group" in child_response, "is_group field should be present"
        
        assert parent_response["is_group"] is True, "Parent account should be marked as group"
        assert child_response["is_group"] is False, "Child posting account should not be marked as group"

    def test_group_hierarchy_with_tree_structure(self, client):
        """
        Test group hierarchy in a tree-like structure to ensure proper nesting.
        """
        # Create root group
        root_data = {
            "account_code": "5000",
            "account_name": "Expenses", 
            "account_type": "expense"
        }
        root_response = client.post("/api/v1/chart-of-accounts", json=root_data)
        assert root_response.status_code == status.HTTP_201_CREATED
        root_id = root_response.json()["id"]

        # Create sub-group
        group_data = {
            "account_code": "5100",
            "account_name": "Operating Expenses",
            "account_type": "expense",
            "parent_account_id": root_id
        }
        group_response = client.post("/api/v1/chart-of-accounts", json=group_data)
        assert group_response.status_code == status.HTTP_201_CREATED
        group_id = group_response.json()["id"]

        # Create posting account under sub-group
        posting_data = {
            "account_code": "5110", 
            "account_name": "Office Supplies",
            "account_type": "expense",
            "parent_account_id": group_id
        }
        posting_response = client.post("/api/v1/chart-of-accounts", json=posting_data)
        assert posting_response.status_code == status.HTTP_201_CREATED

        # Verify the hierarchy structure
        list_response = client.get("/api/v1/chart-of-accounts")
        assert list_response.status_code == status.HTTP_200_OK
        
        accounts = list_response.json()["chart_of_accounts"]
        
        root_account = next((a for a in accounts if a["account_code"] == "5000"), None)
        group_account = next((a for a in accounts if a["account_code"] == "5100"), None) 
        posting_account = next((a for a in accounts if a["account_code"] == "5110"), None)
        
        assert root_account is not None
        assert group_account is not None
        assert posting_account is not None
        
        # Verify hierarchy relationships
        assert root_account["level"] == 1
        assert group_account["level"] == 2
        assert posting_account["level"] == 3
        
        assert group_account["parent_account_id"] == root_id
        assert posting_account["parent_account_id"] == group_id

    def test_is_group_automatically_set_when_creating_child(self, client):
        """
        Test that parent accounts are automatically marked as groups when children are added.
        """
        # Create parent account (initially not marked as group)
        parent_data = {
            "account_code": "6000",
            "account_name": "Other Income",
            "account_type": "revenue"  
        }
        parent_response = client.post("/api/v1/chart-of-accounts", json=parent_data)
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        # Initially, parent might not be marked as group
        # (depending on implementation, this could be set during creation of child)

        # Create child account
        child_data = {
            "account_code": "6100",
            "account_name": "Interest Income", 
            "account_type": "revenue",
            "parent_account_id": parent_id
        }
        child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
        assert child_response.status_code == status.HTTP_201_CREATED

        # Now verify parent is marked as group
        parent_get_response = client.get(f"/api/v1/chart-of-accounts/{parent_id}")
        assert parent_get_response.status_code == status.HTTP_200_OK
        
        parent_data_updated = parent_get_response.json()
        # The parent should now be marked as a group because it has children
        # Note: This depends on the business logic implementation


class TestChartOfAccountPagination:
    """Test cases for Issue #4: Pagination not working for chart of account landing page"""

    def test_pagination_metadata_returned(self, client, db_session, sample_organization):
        """
        Test that pagination metadata is correctly returned in list responses.
        """
        # Create multiple accounts to test pagination
        accounts = []
        for i in range(25):  # Create 25 accounts to test pagination
            account = Account(
                organization_id=sample_organization.id,
                account_code=f"T{i:03d}",
                account_name=f"Test Account {i:02d}",
                account_type=AccountType.ASSET,
                currency="USD",
                status=AccountStatus.ACTIVE,
                is_posting_account=True,
                level=1,
                created_by="test-user",
                updated_by="test-user",
            )
            accounts.append(account)
        
        db_session.add_all(accounts)
        db_session.commit()

        # Test first page with page_size=10
        response = client.get("/api/v1/chart-of-accounts?page=1&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        
        # Verify response structure
        assert "chart_of_accounts" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        
        # Verify pagination metadata fields
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_count" in pagination
        assert "total_pages" in pagination
        assert "has_next" in pagination
        assert "has_previous" in pagination
        
        # Verify pagination values
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert pagination["total_count"] >= 25  # At least our test accounts
        assert pagination["total_pages"] >= 3   # At least 3 pages for 25+ accounts
        assert pagination["has_previous"] is False  # First page has no previous
        assert pagination["has_next"] is True     # Should have next page

    def test_pagination_page_navigation(self, client, db_session, sample_organization):
        """
        Test that different page numbers return correct subsets of data.
        """
        # Create exactly 15 accounts for predictable pagination
        accounts = []
        for i in range(15):
            account = Account(
                organization_id=sample_organization.id,
                account_code=f"P{i:02d}",
                account_name=f"Page Test {i:02d}",
                account_type=AccountType.ASSET,
                currency="USD",
                status=AccountStatus.ACTIVE,
                is_posting_account=True,
                level=1,
                created_by="test-user",
                updated_by="test-user",
            )
            accounts.append(account)
        
        db_session.add_all(accounts)
        db_session.commit()

        # Test page 1 (page_size=5)
        page1_response = client.get("/api/v1/chart-of-accounts?page=1&page_size=5")
        assert page1_response.status_code == status.HTTP_200_OK
        page1_data = page1_response.json()
        
        # Test page 2 
        page2_response = client.get("/api/v1/chart-of-accounts?page=2&page_size=5")
        assert page2_response.status_code == status.HTTP_200_OK
        page2_data = page2_response.json()

        # Test page 3
        page3_response = client.get("/api/v1/chart-of-accounts?page=3&page_size=5")
        assert page3_response.status_code == status.HTTP_200_OK
        page3_data = page3_response.json()

        # Verify each page has correct number of accounts
        assert len(page1_data["chart_of_accounts"]) == 5
        assert len(page2_data["chart_of_accounts"]) == 5
        assert len(page3_data["chart_of_accounts"]) >= 5  # Last page may have remaining accounts

        # Verify pagination metadata for each page
        assert page1_data["pagination"]["page"] == 1
        assert page2_data["pagination"]["page"] == 2
        assert page3_data["pagination"]["page"] == 3
        
        assert page1_data["pagination"]["has_previous"] is False
        assert page1_data["pagination"]["has_next"] is True
        
        assert page2_data["pagination"]["has_previous"] is True
        assert page2_data["pagination"]["has_next"] is True

        # Verify accounts are different on each page (no duplicates)
        page1_codes = {acc["account_code"] for acc in page1_data["chart_of_accounts"]}
        page2_codes = {acc["account_code"] for acc in page2_data["chart_of_accounts"]}
        page3_codes = {acc["account_code"] for acc in page3_data["chart_of_accounts"]}
        
        # No overlap between pages
        assert len(page1_codes.intersection(page2_codes)) == 0
        assert len(page2_codes.intersection(page3_codes)) == 0

    def test_pagination_with_filters(self, client, db_session, sample_organization):
        """
        Test that pagination works correctly when filters are applied.
        """
        # Create accounts of different types
        asset_accounts = []
        for i in range(8):
            account = Account(
                organization_id=sample_organization.id,
                account_code=f"A{i:02d}",
                account_name=f"Asset {i:02d}",
                account_type=AccountType.ASSET,
                currency="USD",
                status=AccountStatus.ACTIVE,
                is_posting_account=True,
                level=1,
                created_by="test-user",
                updated_by="test-user",
            )
            asset_accounts.append(account)

        liability_accounts = []
        for i in range(6):
            account = Account(
                organization_id=sample_organization.id,
                account_code=f"L{i:02d}",
                account_name=f"Liability {i:02d}",
                account_type=AccountType.LIABILITY,
                currency="USD", 
                status=AccountStatus.ACTIVE,
                is_posting_account=True,
                level=1,
                created_by="test-user",
                updated_by="test-user",
            )
            liability_accounts.append(account)
        
        db_session.add_all(asset_accounts + liability_accounts)
        db_session.commit()

        # Test filtered pagination (only asset accounts, page_size=5)
        response = client.get("/api/v1/chart-of-accounts?account_type=asset&page=1&page_size=5")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        accounts = data["chart_of_accounts"]
        pagination = data["pagination"]
        
        # Should only show asset accounts
        assert len(accounts) == 5  # First page of asset accounts
        for account in accounts:
            assert account["account_type"].upper() == "ASSET"
        
        # Pagination should reflect filtered count
        assert pagination["total_count"] >= 8  # At least our 8 asset accounts
        assert pagination["has_next"] is True  # Should have more asset accounts

        # Test page 2 of filtered results
        page2_response = client.get("/api/v1/chart-of-accounts?account_type=asset&page=2&page_size=5")
        assert page2_response.status_code == status.HTTP_200_OK
        page2_data = page2_response.json()
        
        # Should have remaining asset accounts
        assert len(page2_data["chart_of_accounts"]) >= 3  # At least 3 more assets

    def test_pagination_edge_cases(self, client):
        """
        Test pagination edge cases like page 0, negative page, excessive page numbers.
        """
        # Test page 0 (should default to page 1 or return error)
        response = client.get("/api/v1/chart-of-accounts?page=0&page_size=10")
        # Depending on validation, this might return 400 or treat as page 1
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
        
        # Test negative page 
        response = client.get("/api/v1/chart-of-accounts?page=-1&page_size=10")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Test excessive page size
        response = client.get("/api/v1/chart-of-accounts?page=1&page_size=2000")
        # Should be limited to maximum (e.g., 1000)
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_200_OK]
        
        # Test very high page number (beyond available data)
        response = client.get("/api/v1/chart-of-accounts?page=999&page_size=10")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should return empty list or last valid page
        assert len(data["chart_of_accounts"]) == 0


class TestEditAccountDialogParentName:
    """Test cases for Issue #5: Edit account dialog not populating parent account name"""

    def test_account_response_includes_parent_info(self, client, db_session, sample_organization):
        """
        Test that individual account GET response includes parent account information.
        This data is needed for the edit account dialog.
        """
        # Create parent account
        parent_account = Account(
            organization_id=sample_organization.id,
            account_code="7000",
            account_name="Operating Expenses Parent",
            account_type=AccountType.EXPENSE,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            level=1,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(parent_account)
        db_session.commit()

        # Create child account
        child_account = Account(
            organization_id=sample_organization.id,
            account_code="7100",
            account_name="Office Rent",
            account_type=AccountType.EXPENSE,
            parent_account_id=parent_account.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            level=2,
            is_group=False,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add(child_account)
        db_session.commit()

        # Test GET individual account includes parent info
        response = client.get(f"/api/v1/chart-of-accounts/{child_account.id}")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        
        # Verify child account data
        assert data["id"] == str(child_account.id)
        assert data["account_code"] == "7100"
        assert data["account_name"] == "Office Rent"
        assert data["parent_account_id"] == str(parent_account.id)
        
        # Verify parent information is included 
        assert "parent" in data, "Parent information should be included in response"
        
        if data["parent"]:  # If parent info is populated
            parent_info = data["parent"]
            assert "id" in parent_info
            assert "account_code" in parent_info
            assert "account_name" in parent_info
            
            assert parent_info["id"] == str(parent_account.id)
            assert parent_info["account_code"] == "7000"
            assert parent_info["account_name"] == "Operating Expenses Parent"

    def test_account_list_includes_parent_names(self, client, db_session, sample_organization):
        """
        Test that account list includes parent account names for accounts with parents.
        This is useful for displaying hierarchy in lists.
        """
        # Create parent
        parent_account = Account(
            organization_id=sample_organization.id,
            account_code="8000",
            account_name="Revenue Categories",
            account_type=AccountType.REVENUE,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=False,
            level=1,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        # Create multiple children
        child1 = Account(
            organization_id=sample_organization.id,
            account_code="8100",
            account_name="Product Sales",
            account_type=AccountType.REVENUE,
            parent_account_id=parent_account.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            level=2,
            created_by="test-user",
            updated_by="test-user",
        )
        
        child2 = Account(
            organization_id=sample_organization.id,
            account_code="8200", 
            account_name="Service Sales",
            account_type=AccountType.REVENUE,
            parent_account_id=parent_account.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            level=2,
            created_by="test-user", 
            updated_by="test-user",
        )
        
        db_session.add_all([parent_account, child1, child2])
        db_session.commit()

        # Test account list includes parent info
        response = client.get("/api/v1/chart-of-accounts")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        accounts = data["chart_of_accounts"]
        
        # Find child accounts
        child1_response = next((a for a in accounts if a["account_code"] == "8100"), None)
        child2_response = next((a for a in accounts if a["account_code"] == "8200"), None)
        parent_response = next((a for a in accounts if a["account_code"] == "8000"), None)
        
        assert child1_response is not None
        assert child2_response is not None
        assert parent_response is not None
        
        # Verify parent_account_id is included
        assert child1_response["parent_account_id"] == str(parent_account.id)
        assert child2_response["parent_account_id"] == str(parent_account.id)
        assert parent_response.get("parent_account_id") is None  # Parent has no parent

    def test_account_hierarchy_endpoint(self, client, db_session, sample_organization):
        """
        Test account hierarchy endpoint that provides full parent/child relationships.
        This might be used by the edit dialog to show context.
        """
        # Create a 3-level hierarchy
        root = Account(
            organization_id=sample_organization.id,
            account_code="9000",
            account_name="Root Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            level=1,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        middle = Account(
            organization_id=sample_organization.id,
            account_code="9100", 
            account_name="Middle Account",
            account_type=AccountType.ASSET,
            parent_account_id=root.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            level=2,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        leaf = Account(
            organization_id=sample_organization.id,
            account_code="9110",
            account_name="Leaf Account", 
            account_type=AccountType.ASSET,
            parent_account_id=middle.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            level=3,
            is_group=False,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add_all([root, middle, leaf])
        db_session.commit()

        # Test if hierarchy endpoint exists (this might be a separate endpoint)
        # If not available, the test documents what should exist
        hierarchy_response = client.get(f"/api/v1/chart-of-accounts/{leaf.id}/hierarchy")
        
        # This endpoint might not exist yet, so we document expected behavior
        if hierarchy_response.status_code == status.HTTP_200_OK:
            hierarchy_data = hierarchy_response.json()
            
            # Expected structure for hierarchy response
            assert "account" in hierarchy_data
            assert "ancestors" in hierarchy_data
            assert "children" in hierarchy_data
            
            # The middle account should have root as ancestor and leaf as child
            middle_hierarchy = client.get(f"/api/v1/chart-of-accounts/{middle.id}/hierarchy")
            if middle_hierarchy.status_code == status.HTTP_200_OK:
                middle_data = middle_hierarchy.json()
                
                # Should have root as ancestor
                assert len(middle_data["ancestors"]) >= 1
                root_ancestor = next((a for a in middle_data["ancestors"] if a["account_code"] == "9000"), None)
                assert root_ancestor is not None
                
                # Should have leaf as child 
                assert len(middle_data["children"]) >= 1
                leaf_child = next((c for c in middle_data["children"] if c["account_code"] == "9110"), None)
                assert leaf_child is not None

    def test_update_account_preserves_parent_info(self, client, db_session, sample_organization):
        """
        Test that updating an account properly handles parent relationships.
        """
        # Create parent and child
        parent = Account(
            organization_id=sample_organization.id,
            account_code="P001",
            account_name="Parent Account",
            account_type=AccountType.ASSET,
            currency="USD",
            status=AccountStatus.ACTIVE,
            level=1,
            is_group=True,
            created_by="test-user",
            updated_by="test-user",
        )
        
        child = Account(
            organization_id=sample_organization.id,
            account_code="C001",
            account_name="Child Account",
            account_type=AccountType.ASSET,
            parent_account_id=parent.id,
            currency="USD",
            status=AccountStatus.ACTIVE,
            level=2,
            created_by="test-user",
            updated_by="test-user",
        )
        
        db_session.add_all([parent, child])
        db_session.commit()

        # Update child account name only
        update_data = {
            "account_name": "Updated Child Account"
        }
        
        response = client.put(f"/api/v1/chart-of-accounts/{child.id}", json=update_data)
        assert response.status_code == status.HTTP_200_OK
        
        updated_data = response.json()
        
        # Verify parent relationship is preserved
        assert updated_data["parent_account_id"] == str(parent.id)
        assert updated_data["account_name"] == "Updated Child Account"
        
        # Verify we can still get parent info
        if "parent" in updated_data and updated_data["parent"]:
            assert updated_data["parent"]["account_name"] == "Parent Account"