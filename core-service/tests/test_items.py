"""Item API endpoint tests"""

import uuid


class TestCreateItem:
    """Tests for POST /api/v1/items"""

    def test_create_item_success(self, client, test_item_data):
        """Test creating an item successfully"""
        response = client.post("/api/v1/items", json=test_item_data)

        assert response.status_code == 201
        data = response.json()

        assert data["item_code"] == test_item_data["item_code"]
        assert data["item_name"] == test_item_data["item_name"]
        assert data["item_type"] == test_item_data["item_type"]
        assert data["uom"] == test_item_data["uom"]
        assert "id" in data
        assert "created_at" in data

    def test_create_item_missing_required_fields(self, client):
        """Test creating an item without required fields fails"""
        response = client.post("/api/v1/items", json={})

        assert response.status_code == 400  # Validation error
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "details" in data  # FastAPI returns validation errors in 'details'

    def test_create_item_duplicate_code(self, client, test_item_data):
        """Test creating an item with duplicate code fails"""
        # Create first item
        response1 = client.post("/api/v1/items", json=test_item_data)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post("/api/v1/items", json=test_item_data)
        assert response2.status_code == 409
        assert response2.json()["error"] == "DUPLICATE_ITEM_CODE"


class TestListItems:
    """Tests for GET /api/v1/items"""

    def test_list_items_empty(self, client):
        """Test listing items when none exist"""
        response = client.get("/api/v1/items")

        assert response.status_code == 200
        data = response.json()

        assert data["items"] == []
        assert data["pagination"]["total_items"] == 0

    def test_list_items_with_data(self, client, test_item_data):
        """Test listing items with data"""
        # Create an item first
        client.post("/api/v1/items", json=test_item_data)

        response = client.get("/api/v1/items")

        assert response.status_code == 200
        data = response.json()

        assert len(data["items"]) == 1
        assert data["pagination"]["total_items"] == 1

    def test_list_items_pagination(self, client, test_item_data):
        """Test pagination parameters"""
        response = client.get("/api/v1/items?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10


class TestGetItem:
    """Tests for GET /api/v1/items/{item_id}"""

    def test_get_item_success(self, client, test_item_data):
        """Test getting an item by ID"""
        # Create an item first
        create_response = client.post("/api/v1/items", json=test_item_data)
        item_id = create_response.json()["id"]

        response = client.get(f"/api/v1/items/{item_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_id
        assert data["item_code"] == test_item_data["item_code"]

    def test_get_item_not_found(self, client):
        """Test getting a non-existent item"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/items/{fake_id}")

        assert response.status_code == 404
        assert response.json()["error"] == "ITEM_NOT_FOUND"


class TestUpdateItem:
    """Tests for PUT /api/v1/items/{item_id}"""

    def test_update_item_success(self, client, test_item_data):
        """Test updating an item"""
        # Create an item first
        create_response = client.post("/api/v1/items", json=test_item_data)
        item_id = create_response.json()["id"]

        update_data = {"item_name": "Updated Item Name"}
        response = client.put(f"/api/v1/items/{item_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["item_name"] == "Updated Item Name"
        assert data["item_code"] == test_item_data["item_code"]  # Unchanged

    def test_update_item_not_found(self, client):
        """Test updating a non-existent item"""
        fake_id = str(uuid.uuid4())
        response = client.put(f"/api/v1/items/{fake_id}", json={"item_name": "Test"})

        assert response.status_code == 404


class TestDeleteItem:
    """Tests for DELETE /api/v1/items/{item_id}"""

    def test_delete_item_success(self, client, test_item_data):
        """Test deleting an item"""
        # Create an item first
        create_response = client.post("/api/v1/items", json=test_item_data)
        item_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/items/{item_id}")

        assert response.status_code == 204

        # Verify item is no longer accessible
        get_response = client.get(f"/api/v1/items/{item_id}")
        assert get_response.status_code == 404

    def test_delete_item_not_found(self, client):
        """Test deleting a non-existent item"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/items/{fake_id}")

        assert response.status_code == 404
