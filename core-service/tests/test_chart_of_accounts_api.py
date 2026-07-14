"""Unit tests for Chart of Accounts API endpoints"""

import uuid

import pytest
from fastapi import status


@pytest.fixture
def test_account_data():
    """Sample account data for testing"""
    return {
        "account_code": "1000-01",
        "account_name": "Cash Account",
        "account_type": "asset",
    }


@pytest.fixture
def test_parent_account_data():
    """Sample parent account data for testing"""
    return {
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
        assert "already exists" in response2.json()["detail"]["message"].lower()

    def test_create_account_missing_required_fields(self, client):
        """Test validation error for missing required fields"""
        invalid_data = {
            "account_name": "Test Account",
            # Missing account_code and account_type
        }
        response = client.post("/api/v1/chart-of-accounts", json=invalid_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_account_empty_code(self, client, test_account_data):
        """Test validation error for empty account code"""
        test_account_data["account_code"] = ""
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_account_empty_name(self, client, test_account_data):
        """Test validation error for empty account name"""
        test_account_data["account_name"] = ""
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_account_whitespace_only_code(self, client, test_account_data):
        """Test validation error for whitespace-only account code"""
        test_account_data["account_code"] = "   "
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_account_code_too_long(self, client, test_account_data):
        """Test validation error for account code exceeding 50 characters"""
        test_account_data["account_code"] = "A" * 51
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_account_name_too_long(self, client, test_account_data):
        """Test validation error for account name exceeding 200 characters"""
        test_account_data["account_name"] = "A" * 201
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

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
        assert (
            data["parent"]["account_code"] == test_parent_account_data["account_code"]
        )


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
            "status": "inactive",
            "is_posting_account": False,
        }
        response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}", json=update_data
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["account_name"] == "Updated Name"
        assert data["status"] == "inactive"
        assert data["is_posting_account"] is False

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
        assert response.status_code == status.HTTP_400_BAD_REQUEST


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
        assert response.status_code == status.HTTP_409_CONFLICT
        assert "child" in response.json()["detail"]["message"].lower()

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
        response = client.delete(f"/api/v1/chart-of-accounts/{parent_id}?force=true")
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
            account_data["account_code"] = f"1000-0{i + 1}"
            account_data["account_name"] = f"Account {i + 1}"
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
            account_data["account_code"] = f"1000-0{i + 1}"
            account_data["account_name"] = f"Account {i + 1}"
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
        active_data["status"] = "active"
        client.post("/api/v1/chart-of-accounts", json=active_data)

        # Create inactive account
        inactive_data = test_account_data.copy()
        inactive_data["account_code"] = "1000-02"
        inactive_data["account_name"] = "Inactive Account"
        inactive_data["status"] = "inactive"
        client.post("/api/v1/chart-of-accounts", json=inactive_data)

        # Filter by active status
        response = client.get("/api/v1/chart-of-accounts?is_active=true")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["chart_of_accounts"]) == 1
        assert data["chart_of_accounts"][0]["status"] == "active"

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
        response = client.get(
            "/api/v1/chart-of-accounts?sort_by=account_code&sort_order=asc"
        )

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
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
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
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
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
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
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
        create_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        account_id = create_response.json()["id"]
        assert create_response.json()["status"] == "active"

        # Deactivate
        deactivate_response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}/deactivate"
        )
        assert deactivate_response.json()["status"] == "inactive"

        # Reactivate
        activate_response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}/activate"
        )
        assert activate_response.json()["status"] == "active"

        # Archive
        archive_response = client.put(f"/api/v1/chart-of-accounts/{account_id}/archive")
        assert archive_response.json()["status"] == "archived"

        # Can reactivate from archived
        reactivate_response = client.put(
            f"/api/v1/chart-of-accounts/{account_id}/activate"
        )
        assert reactivate_response.json()["status"] == "active"


class TestHierarchyEndpoints:
    """Tests for hierarchy API endpoints"""

    def test_get_account_hierarchy(
        self, client, test_parent_account_data, test_account_data
    ):
        """Test GET /api/v1/chart-of-accounts/:id/hierarchy"""
        # Create parent account
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        # Create child account
        test_account_data["parent_account_id"] = parent_id
        child_response = client.post(
            "/api/v1/chart-of-accounts", json=test_account_data
        )
        assert child_response.status_code == status.HTTP_201_CREATED
        child_id = child_response.json()["id"]

        # Get hierarchy for child account
        response = client.get(f"/api/v1/chart-of-accounts/{child_id}/hierarchy")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "account" in data
        assert "ancestors" in data
        assert "children" in data
        assert "descendants_count" in data
        assert data["account"]["id"] == child_id
        assert len(data["ancestors"]) == 1
        assert data["ancestors"][0]["id"] == parent_id

    def test_get_children(self, client, test_parent_account_data, test_account_data):
        """Test GET /api/v1/chart-of-accounts/:id/children"""
        # Create parent account
        parent_response = client.post(
            "/api/v1/chart-of-accounts", json=test_parent_account_data
        )
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        # Create child accounts
        child_ids = []
        for i in range(3):
            child_data = test_account_data.copy()
            child_data["account_code"] = f"1000-0{i + 1}"
            child_data["account_name"] = f"Child Account {i + 1}"
            child_data["parent_account_id"] = parent_id

            child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
            assert child_response.status_code == status.HTTP_201_CREATED
            child_ids.append(child_response.json()["id"])

        # Get children
        response = client.get(f"/api/v1/chart-of-accounts/{parent_id}/children")
        assert response.status_code == status.HTTP_200_OK

        children = response.json()
        assert len(children) == 3
        returned_ids = [child["id"] for child in children]
        for child_id in child_ids:
            assert child_id in returned_ids

    def test_get_ancestors(self, client, mock_current_user):
        """Test GET /api/v1/chart-of-accounts/:id/ancestors"""
        # Create 3-level hierarchy: grandparent -> parent -> child
        grandparent_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1000",
            "account_name": "Assets",
            "account_type": "asset",
        }
        grandparent_response = client.post(
            "/api/v1/chart-of-accounts", json=grandparent_data
        )
        assert grandparent_response.status_code == status.HTTP_201_CREATED
        grandparent_id = grandparent_response.json()["id"]

        parent_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1100",
            "account_name": "Current Assets",
            "account_type": "asset",
            "parent_account_id": grandparent_id,
        }
        parent_response = client.post("/api/v1/chart-of-accounts", json=parent_data)
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        child_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1110",
            "account_name": "Cash",
            "account_type": "asset",
            "parent_account_id": parent_id,
        }
        child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
        assert child_response.status_code == status.HTTP_201_CREATED
        child_id = child_response.json()["id"]

        # Get ancestors of child
        response = client.get(f"/api/v1/chart-of-accounts/{child_id}/ancestors")
        assert response.status_code == status.HTTP_200_OK

        ancestors = response.json()
        assert len(ancestors) == 2
        # Ancestors should be ordered from immediate parent to root
        assert ancestors[0]["id"] == parent_id
        assert ancestors[1]["id"] == grandparent_id

    def test_get_descendants(self, client, mock_current_user):
        """Test GET /api/v1/chart-of-accounts/:id/descendants"""
        # Create hierarchy: parent -> child -> grandchild
        parent_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1000",
            "account_name": "Assets",
            "account_type": "asset",
        }
        parent_response = client.post("/api/v1/chart-of-accounts", json=parent_data)
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        child_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1100",
            "account_name": "Current Assets",
            "account_type": "asset",
            "parent_account_id": parent_id,
        }
        child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
        assert child_response.status_code == status.HTTP_201_CREATED
        child_id = child_response.json()["id"]

        grandchild_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1110",
            "account_name": "Cash",
            "account_type": "asset",
            "parent_account_id": child_id,
        }
        grandchild_response = client.post(
            "/api/v1/chart-of-accounts", json=grandchild_data
        )
        assert grandchild_response.status_code == status.HTTP_201_CREATED
        grandchild_id = grandchild_response.json()["id"]

        # Get descendants of parent
        response = client.get(f"/api/v1/chart-of-accounts/{parent_id}/descendants")
        assert response.status_code == status.HTTP_200_OK

        descendants = response.json()
        assert len(descendants) == 2
        descendant_ids = [d["id"] for d in descendants]
        assert child_id in descendant_ids
        assert grandchild_id in descendant_ids

    def test_move_account_to_new_parent(self, client, mock_current_user):
        """Test PUT /api/v1/chart-of-accounts/:id/parent"""
        # Create two parent accounts
        parent1_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1000",
            "account_name": "Current Assets",
            "account_type": "asset",
        }
        parent1_response = client.post("/api/v1/chart-of-accounts", json=parent1_data)
        assert parent1_response.status_code == status.HTTP_201_CREATED
        parent1_id = parent1_response.json()["id"]

        parent2_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1200",
            "account_name": "Fixed Assets",
            "account_type": "asset",
        }
        parent2_response = client.post("/api/v1/chart-of-accounts", json=parent2_data)
        assert parent2_response.status_code == status.HTTP_201_CREATED
        parent2_id = parent2_response.json()["id"]

        # Create child under parent1
        child_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1100",
            "account_name": "Cash",
            "account_type": "asset",
            "parent_account_id": parent1_id,
        }
        child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
        assert child_response.status_code == status.HTTP_201_CREATED
        child_id = child_response.json()["id"]

        # Move child to parent2
        move_data = {"new_parent_id": parent2_id}
        response = client.put(
            f"/api/v1/chart-of-accounts/{child_id}/parent", json=move_data
        )
        assert response.status_code == status.HTTP_200_OK

        updated_account = response.json()
        assert updated_account["parent_account_id"] == parent2_id

        # Verify the move by checking children of both parents
        parent1_children = client.get(
            f"/api/v1/chart-of-accounts/{parent1_id}/children"
        )
        assert len(parent1_children.json()) == 0

        parent2_children = client.get(
            f"/api/v1/chart-of-accounts/{parent2_id}/children"
        )
        assert len(parent2_children.json()) == 1
        assert parent2_children.json()[0]["id"] == child_id

    def test_move_account_circular_reference(self, client, mock_current_user):
        """Test that moving account to create circular reference is rejected"""
        # Create parent -> child hierarchy
        parent_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1000",
            "account_name": "Assets",
            "account_type": "asset",
        }
        parent_response = client.post("/api/v1/chart-of-accounts", json=parent_data)
        assert parent_response.status_code == status.HTTP_201_CREATED
        parent_id = parent_response.json()["id"]

        child_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1100",
            "account_name": "Current Assets",
            "account_type": "asset",
            "parent_account_id": parent_id,
        }
        child_response = client.post("/api/v1/chart-of-accounts", json=child_data)
        assert child_response.status_code == status.HTTP_201_CREATED
        child_id = child_response.json()["id"]

        # Try to move parent under child (would create circular reference)
        move_data = {"new_parent_id": child_id}
        response = client.put(
            f"/api/v1/chart-of-accounts/{parent_id}/parent", json=move_data
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        # The error message should contain "circular"
        error_message = str(response_data).lower()
        assert "circular" in error_message

    def test_move_account_type_mismatch(self, client, mock_current_user):
        """Test that moving account to parent with different type is rejected"""
        # Create asset parent
        asset_parent_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "1000",
            "account_name": "Assets",
            "account_type": "asset",
        }
        asset_parent_response = client.post(
            "/api/v1/chart-of-accounts", json=asset_parent_data
        )
        assert asset_parent_response.status_code == status.HTTP_201_CREATED
        asset_parent_id = asset_parent_response.json()["id"]

        # Create liability account
        liability_data = {
            "organization_id": str(mock_current_user.organization_id),
            "account_code": "2000",
            "account_name": "Accounts Payable",
            "account_type": "liability",
        }
        liability_response = client.post(
            "/api/v1/chart-of-accounts", json=liability_data
        )
        assert liability_response.status_code == status.HTTP_201_CREATED
        liability_id = liability_response.json()["id"]

        # Try to move liability under asset parent
        move_data = {"new_parent_id": asset_parent_id}
        response = client.put(
            f"/api/v1/chart-of-accounts/{liability_id}/parent", json=move_data
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        # The error message should contain "type"
        error_message = str(response_data).lower()
        assert "type" in error_message

    def test_get_hierarchy_nonexistent_account(self, client):
        """Test hierarchy endpoint with nonexistent account"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/chart-of-accounts/{fake_id}/hierarchy")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_children_no_children(self, client, test_account_data):
        """Test getting children of account with no children"""
        # Create account without children
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_201_CREATED
        account_id = response.json()["id"]

        # Get children
        children_response = client.get(
            f"/api/v1/chart-of-accounts/{account_id}/children"
        )
        assert children_response.status_code == status.HTTP_200_OK
        assert len(children_response.json()) == 0

    def test_get_ancestors_root_account(self, client, test_account_data):
        """Test getting ancestors of root account (should be empty)"""
        # Create root account
        response = client.post("/api/v1/chart-of-accounts", json=test_account_data)
        assert response.status_code == status.HTTP_201_CREATED
        account_id = response.json()["id"]

        # Get ancestors
        ancestors_response = client.get(
            f"/api/v1/chart-of-accounts/{account_id}/ancestors"
        )
        assert ancestors_response.status_code == status.HTTP_200_OK
        assert len(ancestors_response.json()) == 0
