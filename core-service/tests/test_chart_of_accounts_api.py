"""Unit tests for Chart of Accounts API endpoints"""

import uuid
from decimal import Decimal

import pytest
from fastapi import status


@pytest.fixture
def test_account_data(mock_current_user):
    """Sample account data for testing"""
    return {
        "organization_id": str(mock_current_user.organization_id),
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": "asset",
    }


@pytest.fixture
def test_parent_account_data(mock_current_user):
    """Sample parent account data for testing"""
    return {
        "organization_id": str(mock_current_user.organization_id),
        "account_code": "1000",
        "account_name": "Current Assets",
        "account_type": "asset",
    }


class TestCreateAccount:
    """Tests for POST /api/v1/chart-of-accounts"""

    def test_create_account_success(self, client, test_account_data):
        """Test successful account creation"""
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["account_code"] == test_account_data["account_code"]
        assert data["account_name"] == test_account_data["account_name"]
        assert data["account_type"] == test_account_data["account_type"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_account_duplicate_code(self, client, test_account_data):
        """Test duplicate account code rejection"""
        # Create first account
        response1 = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create duplicate
        response2 = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response2.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response2.json()["detail"].lower()

    def test_create_account_missing_required_fields(self, client):
        """Test validation error for missing required fields"""
        invalid_data = {
            "account_name": "Test Account",
            # Missing account_code and account_type
        }
        response = client.post("/api/v1/chart-of-accounts", json=invalid_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_account_empty_code(self, client, test_account_data):
        """Test validation error for empty account code"""
        test_account_data["account_code"] = ""
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_account_empty_name(self, client, test_account_data):
        """Test validation error for empty account name"""
        test_account_data["account_name"] = ""
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_account_whitespace_only_code(self, client, test_account_data):
        """Test validation error for whitespace-only account code"""
        test_account_data["account_code"] = "   "
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_account_code_too_long(self, client, test_account_data):
        """Test validation error for account code exceeding 50 characters"""
        test_account_data["account_code"] = "A" * 51
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_account_name_too_long(self, client, test_account_data):
        """Test validation error for account name exceeding 200 characters"""
        test_account_data["account_name"] = "A" * 201
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_create_account_with_parent(
        self, client, test_parent_account_data, test_account_data
    ):
        """Test creating account with parent relationship"""
        # Create parent account
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        # Create child account
        test_account_data["parent_account_id"] = parent_id
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["parent_account_id"] == parent_id


class TestGetAccount:
    """Tests for GET /api/v1/chart-of-accounts/:id"""

    def test_get_account_success(self, client, test_account_data):
        """Test successful account retrieval"""
        # Create account
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        account_id = create_response.json()["id"]

        # Get account
        response = client.get(f"/api/v1/chart-of-accounts/{account_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == account_id
        assert data["account_code"] == test_account_data["account_code"]
        assert data["account_name"] == test_account_data["account_name"]

    def test_get_account_not_found(self, client):
        """Test 404 error for non-existent account"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/chart-of-accounts/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_account_with_parent_info(
        self, client, test_parent_account_data, test_account_data
    ):
        """Test account retrieval includes parent information"""
        # Create parent
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        parent_id = parent_response.json()["id"]

        # Create child
        test_account_data["parent_account_id"] = parent_id
        child_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        child_id = child_response.json()["id"]

        # Get child account
        response = client.get(f"/api/v1/chart-of-accounts/{child_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["parent_account_id"] == parent_id
        assert data["parent"] is not None
        assert data["parent"]["id"] == parent_id
        assert data["parent"]["account_code"] == test_parent_account_data["account_code"]


class TestUpdateAccount:
    """Tests for PUT /api/v1/chart-of-accounts/:id"""

    def test_update_account_success(self, client, test_account_data):
        """Test successful account update"""
        # Create account
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        account_id = create_response.json()["id"]

        # Update account
        update_data = {"account_name": "Updated Cash Account"}
        response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["account_name"] == "Updated Cash Account"
        assert data["account_code"] == test_account_data["account_code"]  # Unchanged

    def test_update_account_not_found(self, client):
        """Test 404 error when updating non-existent account"""
        fake_id = str(uuid.uuid4())
        update_data = {"account_name": "Updated Name"}
        response = client.put(f"/api/v1/chart-of-accounts/{fake_id}", json=update_data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_account_multiple_fields(self, client, test_account_data):
        """Test updating multiple fields at once"""
        # Create account
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        account_id = create_response.json()["id"]

        # Update multiple fields
        update_data = {
            "account_name": "Updated Name",
            "is_active": False,
            "opening_balance": 1000.50,
        }
        response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["account_name"] == "Updated Name"
        assert data["is_active"] is False
        assert float(data["opening_balance"]) == 1000.50

    def test_update_account_name_too_long(self, client, test_account_data):
        """Test validation error for name exceeding 200 characters"""
        # Create account
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        account_id = create_response.json()["id"]

        # Try to update with too long name
        update_data = {"account_name": "A" * 201}
        response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}", json=update_data
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestDeleteAccount:
    """Tests for DELETE /api/v1/chart-of-accounts/:id"""

    def test_delete_account_success(self, client, test_account_data):
        """Test successful account deletion"""
        # Create account
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        account_id = create_response.json()["id"]

        # Delete account
        response = client.delete(f"/api/v1/chart-of-accounts/{account_id}")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify account is deleted
        get_response = client.get(f"/api/v1/chart-of-accounts/{account_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_account_not_found(self, client):
        """Test 404 error when deleting non-existent account"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/chart-of-accounts/{fake_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_account_with_children_fails(
        self, client, test_parent_account_data, test_account_data
    ):
        """Test deletion fails when account has children"""
        # Create parent account
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        parent_id = parent_response.json()["id"]

        # Create child account
        test_account_data["parent_account_id"] = parent_id
        client.post("/api/v1/chart-of-accounts", json=test_account_data)

        # Try to delete parent
        response = client.delete(f"/api/v1/chart-of-accounts/{parent_id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "child" in response.json()["detail"].lower()

    def test_delete_account_with_children_force(
        self, client, test_parent_account_data, test_account_data
    ):
        """Test force deletion of account with children"""
        # Create parent account
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        parent_id = parent_response.json()["id"]

        # Create child account
        test_account_data["parent_account_id"] = parent_id
        client.post("/api/v1/chart-of-accounts", json=test_account_data)

        # Force delete parent
        response = client.delete(
            f"/api/v1/chart-of-accounts/{parent_id}?force=true"
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class TestListAccounts:
    """Tests for GET /api/v1/chart-of-accounts"""

    def test_list_accounts_empty(self, client):
        """Test listing accounts when none exist"""
        response = client.get("/api/v1/chart-of-accounts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "chart_of_accounts" in data
        assert "pagination" in data
        assert len(data["chart_of_accounts"]) == 0

    def test_list_accounts_with_data(self, client, test_account_data):
        """Test listing accounts with data"""
        # Create multiple accounts
        for i in range(3):
            account_data = test_account_data.copy()
            account_data["account_code"] = f"1000-0{i+1}"
            account_data["account_name"] = f"Account {i+1}"
            client.post("/api/v1/chart-of-accounts", json=account_data)

        # List accounts
        response = client.get("/api/v1/chart-of-accounts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chart_of_accounts"]) == 3
        assert data["pagination"]["total"] == 3
        assert data["pagination"]["page"] == 1

    def test_list_accounts_pagination(self, client, test_account_data):
        """Test account list pagination"""
        # Create 5 accounts
        for i in range(5):
            account_data = test_account_data.copy()
            account_data["account_code"] = f"1000-0{i+1}"
            account_data["account_name"] = f"Account {i+1}"
            client.post("/api/v1/chart-of-accounts", json=account_data)

        # Get first page with 2 items
        response = client.get("/api/v1/chart-of-accounts?page=1&page_size=2")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chart_of_accounts"]) == 2
        assert data["pagination"]["total"] == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 2
        assert data["pagination"]["total_pages"] == 3

    def test_list_accounts_filter_by_type(self, client, test_account_data):
        """Test filtering accounts by type"""
        # Create asset account
        asset_data = test_account_data.copy()
        asset_data["account_code"] = "1000-01"
        asset_data["account_type"] = "asset"
        client.post("/api/v1/chart-of-accounts", json=asset_data)

        # Create liability account
        liability_data = test_account_data.copy()
        liability_data["account_code"] = "2000-01"
        liability_data["account_name"] = "Liability Account"
        liability_data["account_type"] = "liability"
        client.post("/api/v1/chart-of-accounts", json=liability_data)

        # Filter by asset type
        response = client.get("/api/v1/chart-of-accounts?account_type=asset")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chart_of_accounts"]) == 1
        assert data["chart_of_accounts"][0]["account_type"] == "asset"

    def test_list_accounts_filter_by_status(self, client, test_account_data):
        """Test filtering accounts by active status"""
        # Create active account
        active_data = test_account_data.copy()
        active_data["account_code"] = "1000-01"
        active_data["is_active"] = True
        client.post("/api/v1/chart-of-accounts", json=active_data)

        # Create inactive account
        inactive_data = test_account_data.copy()
        inactive_data["account_code"] = "1000-02"
        inactive_data["account_name"] = "Inactive Account"
        inactive_data["is_active"] = False
        client.post("/api/v1/chart-of-accounts", json=inactive_data)

        # Filter by active status
        response = client.get("/api/v1/chart-of-accounts?is_active=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chart_of_accounts"]) == 1
        assert data["chart_of_accounts"][0]["is_active"] is True

    def test_list_accounts_search(self, client, test_account_data):
        """Test searching accounts by code or name"""
        # Create accounts
        account1 = test_account_data.copy()
        account1["account_code"] = "1000-01"
        account1["account_name"] = "Cash in Hand"
        client.post("/api/v1/chart-of-accounts", json=account1)

        account2 = test_account_data.copy()
        account2["account_code"] = "1000-02"
        account2["account_name"] = "Bank Account"
        client.post("/api/v1/chart-of-accounts", json=account2)

        # Search for "Cash"
        response = client.get("/api/v1/chart-of-accounts?search=Cash")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chart_of_accounts"]) == 1
        assert "Cash" in data["chart_of_accounts"][0]["account_name"]

    def test_list_accounts_sort_by_code(self, client, test_account_data):
        """Test sorting accounts by code"""
        # Create accounts in random order
        codes = ["1000-03", "1000-01", "1000-02"]
        for code in codes:
            account_data = test_account_data.copy()
            account_data["account_code"] = code
            account_data["account_name"] = f"Account {code}"
            client.post("/api/v1/chart-of-accounts", json=account_data)

        # Get sorted list
        response = client.get("/api/v1/chart-of-accounts?sort_by=account_code&sort_order=asc")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        codes_returned = [acc["account_code"] for acc in data["chart_of_accounts"]]
        assert codes_returned == sorted(codes)


class TestGetAccountTree:
    """Tests for GET /api/v1/chart-of-accounts/tree"""

    def test_get_tree_empty(self, client):
        """Test getting tree when no accounts exist"""
        response = client.get("/api/v1/chart-of-accounts/tree")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_tree_with_hierarchy(
        self, client, test_parent_account_data, test_account_data
    ):
        """Test getting tree with parent-child relationships"""
        # Create parent
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        parent_id = parent_response.json()["id"]

        # Create child
        test_account_data["parent_account_id"] = parent_id
        child_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        child_id = child_response.json()["id"]

        # Get tree
        response = client.get("/api/v1/chart-of-accounts/tree")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1  # One root node
        assert data[0]["id"] == parent_id
        assert len(data[0]["children"]) == 1
        assert data[0]["children"][0]["id"] == child_id


class TestAccountStatusManagement:
    """Tests for account status management endpoints"""

    def test_activate_account(self, client, test_account_data):
        """Test activating an account"""
        # Create account
        create_response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        account_id = create_response.json()["id"]

        # Deactivate first
        client.put(f"/api/v1/chart-of-accounts/{account_id}/deactivate")

        # Activate account
        response = client.put(f"/api/v1/chart-of-accounts/{account_id}/activate")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == account_id
        assert data["status"] == "active"

    def test_deactivate_account(self, client, test_account_data):
        """Test deactivating an account"""
        # Create account
        create_response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        account_id = create_response.json()["id"]

        # Deactivate account
        response = client.put(f"/api/v1/chart-of-accounts/{account_id}/deactivate")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == account_id
        assert data["status"] == "inactive"

    def test_archive_account(self, client, test_account_data):
        """Test archiving an account"""
        # Create account
        create_response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        account_id = create_response.json()["id"]

        # Archive account
        response = client.put(f"/api/v1/chart-of-accounts/{account_id}/archive")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == account_id
        assert data["status"] == "archived"

    def test_activate_nonexistent_account(self, client):
        """Test activating a non-existent account"""
        fake_id = str(uuid.uuid4())
        response = client.put(f"/api/v1/chart-of-accounts/{fake_id}/activate")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_deactivate_nonexistent_account(self, client):
        """Test deactivating a non-existent account"""
        fake_id = str(uuid.uuid4())
        response = client.put(f"/api/v1/chart-of-accounts/{fake_id}/deactivate")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_archive_nonexistent_account(self, client):
        """Test archiving a non-existent account"""
        fake_id = str(uuid.uuid4())
        response = client.put(f"/api/v1/chart-of-accounts/{fake_id}/archive")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_status_transitions(self, client, test_account_data):
        """Test multiple status transitions"""
        # Create account (starts as active)
        create_response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        account_id = create_response.json()["id"]
        assert create_response.json()["status"] == "active"

        # Deactivate
        deactivate_response = client.put(f"/api/v1/chart-of-accounts/{account_id}/deactivate")
        assert deactivate_response.json()["status"] == "inactive"

        # Reactivate
        activate_response = client.put(f"/api/v1/chart-of-accounts/{account_id}/activate")
        assert activate_response.json()["status"] == "active"

        # Archive
        archive_response = client.put(f"/api/v1/chart-of-accounts/{account_id}/archive")
        assert archive_response.json()["status"] == "archived"

        # Can reactivate from archived
        reactivate_response = client.put(f"/api/v1/chart-of-accounts/{account_id}/activate")
        assert reactivate_response.json()["status"] == "active"
