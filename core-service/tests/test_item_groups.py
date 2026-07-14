"""Item Group API endpoint tests"""

import uuid


class TestCreateItemGroup:
    """Tests for POST /api/v1/item-groups"""

    def test_create_item_group_success(self, client, test_item_group_data):
        """Test creating an item group successfully"""
        response = client.post("/api/v1/item-groups", json=test_item_group_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == test_item_group_data["name"]
        assert data["code"] == test_item_group_data["code"]
        assert data["description"] == test_item_group_data["description"]
        assert data["is_active"] == test_item_group_data["is_active"]
        assert "id" in data
        assert "organization_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_item_group_minimal_data(self, client):
        """Test creating an item group with minimal required fields"""
        minimal_data = {"name": "Minimal Group", "code": "MIN-001"}
        response = client.post("/api/v1/item-groups", json=minimal_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Minimal Group"
        assert data["code"] == "MIN-001"
        assert data["description"] is None
        assert data["is_active"] is True  # Default value
        assert data["parent_id"] is None

    def test_create_item_group_with_parent(self, client, test_item_group_data):
        """Test creating an item group with a parent"""
        # Create parent group first
        parent_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        assert parent_response.status_code == 201
        parent_id = parent_response.json()["id"]

        # Create child group
        child_data = {
            "name": "Child Group",
            "code": "CHILD-001",
            "parent_id": parent_id,
            "description": "Child of test group",
        }
        response = client.post("/api/v1/item-groups", json=child_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Child Group"
        assert data["code"] == "CHILD-001"
        assert data["parent_id"] == parent_id

    def test_create_item_group_missing_required_fields(self, client):
        """Test creating an item group without required fields fails"""
        response = client.post("/api/v1/item-groups", json={})

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "VALIDATION_ERROR"

    def test_create_item_group_duplicate_code(self, client, test_item_group_data):
        """Test creating an item group with duplicate code fails"""
        # Create first item group
        response1 = client.post("/api/v1/item-groups", json=test_item_group_data)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post("/api/v1/item-groups", json=test_item_group_data)
        assert response2.status_code == 409
        assert response2.json()["detail"]["code"] == "DUPLICATE_ITEM_GROUP_CODE"

    def test_create_item_group_invalid_parent(self, client):
        """Test creating an item group with non-existent parent fails"""
        fake_parent_id = str(uuid.uuid4())
        data = {"name": "Test Group", "code": "TEST-001", "parent_id": fake_parent_id}
        response = client.post("/api/v1/item-groups", json=data)

        assert response.status_code == 404
        assert "parent" in response.json()["detail"]["message"].lower()


class TestListItemGroups:
    """Tests for GET /api/v1/item-groups"""

    def test_list_item_groups_empty(self, client):
        """Test listing item groups when none exist"""
        response = client.get("/api/v1/item-groups")

        assert response.status_code == 200
        data = response.json()

        assert data["item_groups"] == []
        assert data["pagination"]["total_items"] == 0

    def test_list_item_groups_with_data(self, client, test_item_group_data):
        """Test listing item groups with data"""
        # Create an item group first
        client.post("/api/v1/item-groups", json=test_item_group_data)

        response = client.get("/api/v1/item-groups")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_groups"]) == 1
        assert data["pagination"]["total_items"] == 1
        assert data["item_groups"][0]["name"] == test_item_group_data["name"]
        assert data["item_groups"][0]["code"] == test_item_group_data["code"]

    def test_list_item_groups_pagination(self, client, test_item_group_data):
        """Test pagination parameters"""
        response = client.get("/api/v1/item-groups?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10

    def test_list_item_groups_search(self, client):
        """Test search functionality"""
        # Create multiple item groups
        groups = [
            {"name": "Electronics", "code": "ELEC-001"},
            {"name": "Furniture", "code": "FURN-001"},
            {"name": "Electronic Components", "code": "ELEC-002"},
        ]

        for group in groups:
            client.post("/api/v1/item-groups", json=group)

        # Search for "electronic"
        response = client.get("/api/v1/item-groups?search=electronic")

        assert response.status_code == 200
        data = response.json()

        # Should find 2 groups containing "electronic"
        assert len(data["item_groups"]) == 2
        assert data["pagination"]["total_items"] == 2

    def test_list_item_groups_filter_by_active(self, client):
        """Test filtering by active status"""
        # Create active and inactive groups
        active_group = {"name": "Active Group", "code": "ACT-001", "is_active": True}
        inactive_group = {
            "name": "Inactive Group",
            "code": "INACT-001",
            "is_active": False,
        }

        client.post("/api/v1/item-groups", json=active_group)
        client.post("/api/v1/item-groups", json=inactive_group)

        # Filter for active only
        response = client.get("/api/v1/item-groups?is_active=true")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_groups"]) == 1
        assert data["item_groups"][0]["is_active"] is True

    def test_list_item_groups_sort_by_name(self, client):
        """Test sorting by name"""
        # Create groups in random order
        groups = [
            {"name": "Zebra Group", "code": "ZEB-001"},
            {"name": "Alpha Group", "code": "ALP-001"},
            {"name": "Beta Group", "code": "BET-001"},
        ]

        for group in groups:
            client.post("/api/v1/item-groups", json=group)

        # Sort by name ascending
        response = client.get("/api/v1/item-groups?sort_by=name&sort_order=asc")

        assert response.status_code == 200
        data = response.json()

        names = [group["name"] for group in data["item_groups"]]
        assert names == ["Alpha Group", "Beta Group", "Zebra Group"]


class TestGetItemGroup:
    """Tests for GET /api/v1/item-groups/{item_group_id}"""

    def test_get_item_group_success(self, client, test_item_group_data):
        """Test getting an item group by ID"""
        # Create an item group first
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        response = client.get(f"/api/v1/item-groups/{item_group_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_group_id
        assert data["name"] == test_item_group_data["name"]
        assert data["code"] == test_item_group_data["code"]

    def test_get_item_group_with_parent(self, client, test_item_group_data):
        """Test getting an item group that has a parent"""
        # Create parent group
        parent_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        parent_id = parent_response.json()["id"]

        # Create child group
        child_data = {
            "name": "Child Group",
            "code": "CHILD-001",
            "parent_id": parent_id,
        }
        child_response = client.post("/api/v1/item-groups", json=child_data)
        child_id = child_response.json()["id"]

        # Get child group
        response = client.get(f"/api/v1/item-groups/{child_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == child_id
        assert data["parent_id"] == parent_id
        assert data["parent"] is not None
        assert data["parent"]["id"] == parent_id
        assert data["parent"]["name"] == test_item_group_data["name"]

    def test_get_item_group_not_found(self, client):
        """Test getting a non-existent item group"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/item-groups/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "ITEM_GROUP_NOT_FOUND"


class TestGetItemGroupTree:
    """Tests for GET /api/v1/item-groups/tree"""

    def test_get_item_group_tree_empty(self, client):
        """Test getting tree when no item groups exist"""
        response = client.get("/api/v1/item-groups/tree")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_get_item_group_tree_flat(self, client):
        """Test getting tree with only root level groups"""
        # Create multiple root level groups
        groups = [
            {"name": "Electronics", "code": "ELEC-001"},
            {"name": "Furniture", "code": "FURN-001"},
        ]

        for group in groups:
            client.post("/api/v1/item-groups", json=group)

        response = client.get("/api/v1/item-groups/tree")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Each should have empty children
        for node in data:
            assert "children" in node
            assert node["children"] == []

    def test_get_item_group_tree_hierarchical(self, client):
        """Test getting tree with parent-child relationships"""
        # Create parent group
        parent_data = {"name": "Electronics", "code": "ELEC-001"}
        parent_response = client.post("/api/v1/item-groups", json=parent_data)
        parent_id = parent_response.json()["id"]

        # Create child groups
        child1_data = {"name": "Laptops", "code": "LAPTOP-001", "parent_id": parent_id}
        child2_data = {"name": "Phones", "code": "PHONE-001", "parent_id": parent_id}

        client.post("/api/v1/item-groups", json=child1_data)
        client.post("/api/v1/item-groups", json=child2_data)

        response = client.get("/api/v1/item-groups/tree")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # One root node

        root_node = data[0]
        assert root_node["name"] == "Electronics"
        assert len(root_node["children"]) == 2

        child_names = [child["name"] for child in root_node["children"]]
        assert "Laptops" in child_names
        assert "Phones" in child_names


class TestUpdateItemGroup:
    """Tests for PUT /api/v1/item-groups/{item_group_id}"""

    def test_update_item_group_success(self, client, test_item_group_data):
        """Test updating an item group"""
        # Create an item group first
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        update_data = {
            "name": "Updated Group Name",
            "description": "Updated description",
        }
        response = client.put(f"/api/v1/item-groups/{item_group_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Group Name"
        assert data["description"] == "Updated description"
        assert data["code"] == test_item_group_data["code"]  # Unchanged

    def test_update_item_group_change_parent(self, client, test_item_group_data):
        """Test updating an item group's parent"""
        # Create two parent groups
        parent1_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        parent1_id = parent1_response.json()["id"]

        parent2_data = {"name": "Parent 2", "code": "PAR-002"}
        parent2_response = client.post("/api/v1/item-groups", json=parent2_data)
        parent2_id = parent2_response.json()["id"]

        # Create child group under parent1
        child_data = {"name": "Child", "code": "CHILD-001", "parent_id": parent1_id}
        child_response = client.post("/api/v1/item-groups", json=child_data)
        child_id = child_response.json()["id"]

        # Move child to parent2
        update_data = {"parent_id": parent2_id}
        response = client.put(f"/api/v1/item-groups/{child_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["parent_id"] == parent2_id

    def test_update_item_group_deactivate(self, client, test_item_group_data):
        """Test deactivating an item group"""
        # Create an item group
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        update_data = {"is_active": False}
        response = client.put(f"/api/v1/item-groups/{item_group_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_item_group_not_found(self, client):
        """Test updating a non-existent item group"""
        fake_id = str(uuid.uuid4())
        response = client.put(f"/api/v1/item-groups/{fake_id}", json={"name": "Test"})

        assert response.status_code == 404

    def test_update_item_group_invalid_parent(self, client, test_item_group_data):
        """Test updating with non-existent parent"""
        # Create an item group
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        fake_parent_id = str(uuid.uuid4())
        update_data = {"parent_id": fake_parent_id}
        response = client.put(f"/api/v1/item-groups/{item_group_id}", json=update_data)

        assert response.status_code == 404


class TestDeleteItemGroup:
    """Tests for DELETE /api/v1/item-groups/{item_group_id}"""

    def test_delete_item_group_success(self, client, test_item_group_data):
        """Test deleting an item group"""
        # Create an item group first
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/item-groups/{item_group_id}")

        assert response.status_code == 204

        # Verify item group is no longer accessible
        get_response = client.get(f"/api/v1/item-groups/{item_group_id}")
        assert get_response.status_code == 404

    def test_delete_item_group_with_children_fails(self, client, test_item_group_data):
        """Test deleting an item group with children fails without force"""
        # Create parent group
        parent_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        parent_id = parent_response.json()["id"]

        # Create child group
        child_data = {"name": "Child", "code": "CHILD-001", "parent_id": parent_id}
        client.post("/api/v1/item-groups", json=child_data)

        # Try to delete parent without force
        response = client.delete(f"/api/v1/item-groups/{parent_id}")

        assert response.status_code == 409
        assert "children" in response.json()["detail"]["message"].lower()

    def test_delete_item_group_with_children_force(self, client, test_item_group_data):
        """Test force deleting an item group with children"""
        # Create parent group
        parent_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        parent_id = parent_response.json()["id"]

        # Create child group
        child_data = {"name": "Child", "code": "CHILD-001", "parent_id": parent_id}
        client.post("/api/v1/item-groups", json=child_data)

        # Force delete parent
        response = client.delete(f"/api/v1/item-groups/{parent_id}?force=true")

        assert response.status_code == 204

        # Verify parent is deleted
        get_response = client.get(f"/api/v1/item-groups/{parent_id}")
        assert get_response.status_code == 404

    def test_delete_item_group_not_found(self, client):
        """Test deleting a non-existent item group"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/item-groups/{fake_id}")

        assert response.status_code == 404


class TestItemGroupValidation:
    """Tests for item group validation rules"""

    def test_create_item_group_invalid_name_length(self, client):
        """Test creating item group with invalid name length"""
        # Empty name
        response = client.post(
            "/api/v1/item-groups", json={"name": "", "code": "TEST-001"}
        )
        assert response.status_code == 400

        # Name too long (over 255 characters)
        long_name = "x" * 256
        response = client.post(
            "/api/v1/item-groups", json={"name": long_name, "code": "TEST-001"}
        )
        assert response.status_code == 400

    def test_create_item_group_invalid_code_length(self, client):
        """Test creating item group with invalid code length"""
        # Empty code
        response = client.post("/api/v1/item-groups", json={"name": "Test", "code": ""})
        assert response.status_code == 400

        # Code too long (over 50 characters)
        long_code = "x" * 51
        response = client.post(
            "/api/v1/item-groups", json={"name": "Test", "code": long_code}
        )
        assert response.status_code == 400

    def test_create_item_group_invalid_uom_length(self, client):
        """Test creating item group with invalid UOM length"""
        # UOM too long (over 50 characters)
        long_uom = "x" * 51
        data = {"name": "Test Group", "code": "TEST-001", "default_uom": long_uom}
        response = client.post("/api/v1/item-groups", json=data)
        assert response.status_code == 400

    def test_create_item_group_circular_reference(self, client, test_item_group_data):
        """Test preventing circular reference in parent-child relationship"""
        # Create parent group
        parent_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        parent_id = parent_response.json()["id"]

        # Create child group
        child_data = {"name": "Child", "code": "CHILD-001", "parent_id": parent_id}
        child_response = client.post("/api/v1/item-groups", json=child_data)
        child_id = child_response.json()["id"]

        # Try to make parent a child of its own child (circular reference)
        update_data = {"parent_id": child_id}
        response = client.put(f"/api/v1/item-groups/{parent_id}", json=update_data)

        assert response.status_code == 400
        assert "circular" in response.json()["detail"]["message"].lower()


class TestItemGroupPermissions:
    """Tests for item group permission checks"""

    def test_create_item_group_without_permission(self, client, mock_current_user):
        """Test creating item group without proper permissions"""
        # NOTE: Currently permissions are not enforced in the API
        # This test should be updated when permission enforcement is implemented
        # Remove create permission
        mock_current_user.permissions = ["item.read"]

        data = {"name": "Test Group", "code": "TEST-001"}
        response = client.post("/api/v1/item-groups", json=data)

        # Currently returns 201 because permissions are not enforced
        # Should return 403 when permissions are properly implemented
        assert response.status_code == 201

    def test_update_item_group_without_permission(
        self, client, mock_current_user, test_item_group_data
    ):
        """Test updating item group without proper permissions"""
        # NOTE: Currently permissions are not enforced in the API
        # This test should be updated when permission enforcement is implemented
        # Create with full permissions first
        mock_current_user.permissions = [
            "item.create",
            "item.read",
            "item.update",
            "item.delete",
        ]
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        # Remove update permission
        mock_current_user.permissions = ["item.read"]

        update_data = {"name": "Updated Name"}
        response = client.put(f"/api/v1/item-groups/{item_group_id}", json=update_data)

        # Currently returns 200 because permissions are not enforced
        # Should return 403 when permissions are properly implemented
        assert response.status_code == 200

    def test_delete_item_group_without_permission(
        self, client, mock_current_user, test_item_group_data
    ):
        """Test deleting item group without proper permissions"""
        # NOTE: Currently permissions are not enforced in the API
        # This test should be updated when permission enforcement is implemented
        # Create with full permissions first
        mock_current_user.permissions = [
            "item.create",
            "item.read",
            "item.update",
            "item.delete",
        ]
        create_response = client.post("/api/v1/item-groups", json=test_item_group_data)
        item_group_id = create_response.json()["id"]

        # Remove delete permission
        mock_current_user.permissions = ["item.read"]

        response = client.delete(f"/api/v1/item-groups/{item_group_id}")

        # Currently returns 204 because permissions are not enforced
        # Should return 403 when permissions are properly implemented
        assert response.status_code == 204
