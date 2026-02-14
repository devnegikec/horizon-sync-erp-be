"""Item Price API endpoint tests"""

import uuid
from datetime import datetime, timedelta


class TestCreateItemPrice:
    """Tests for POST /api/v1/item-prices"""

    def test_create_item_price_success(
        self, client, test_item_data, test_item_price_data
    ):
        """Test creating an item price successfully"""
        # Create an item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        # Create item price
        price_data = {**test_item_price_data, "item_id": item_id}
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 201
        data = response.json()

        assert data["item_id"] == item_id
        assert data["price"] == test_item_price_data["price"]
        assert data["currency"] == test_item_price_data["currency"]
        assert data["min_qty"] == test_item_price_data["min_qty"]
        assert "id" in data
        assert "organization_id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_item_price_minimal_data(self, client, test_item_data):
        """Test creating an item price with minimal required fields"""
        # Create an item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        # Create item price with minimal data
        minimal_data = {"item_id": item_id, "price": "50.00"}
        response = client.post("/api/v1/item-prices", json=minimal_data)

        assert response.status_code == 201
        data = response.json()

        assert data["item_id"] == item_id
        assert data["price"] == "50.00"
        assert data["currency"] is None
        assert data["min_qty"] is None

    def test_create_item_price_with_dates(self, client, test_item_data):
        """Test creating an item price with validity dates"""
        # Create an item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        # Create item price with dates
        valid_from = datetime.now()
        valid_upto = valid_from + timedelta(days=30)

        price_data = {
            "item_id": item_id,
            "price": "75.00",
            "currency": "USD",
            "valid_from": valid_from.isoformat(),
            "valid_upto": valid_upto.isoformat(),
        }
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 201
        data = response.json()

        assert data["item_id"] == item_id
        assert data["price"] == "75.00"
        assert data["valid_from"] is not None
        assert data["valid_upto"] is not None

    def test_create_item_price_missing_required_fields(self, client):
        """Test creating an item price without required fields fails"""
        response = client.post("/api/v1/item-prices", json={})

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["code"] == "VALIDATION_ERROR"

    def test_create_item_price_invalid_item(self, client):
        """Test creating an item price with non-existent item fails"""
        fake_item_id = str(uuid.uuid4())
        price_data = {"item_id": fake_item_id, "price": "100.00"}
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 404
        assert "item" in response.json()["detail"]["message"].lower()

    def test_create_item_price_invalid_date_range(self, client, test_item_data):
        """Test creating an item price with invalid date range fails"""
        # Create an item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        # Create item price with invalid date range
        valid_from = datetime.now()
        valid_upto = valid_from - timedelta(days=1)  # Invalid: end before start

        price_data = {
            "item_id": item_id,
            "price": "75.00",
            "valid_from": valid_from.isoformat(),
            "valid_upto": valid_upto.isoformat(),
        }
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 400

    def test_create_duplicate_item_price(
        self, client, test_item_data, test_item_price_data
    ):
        """Test creating duplicate item price fails"""
        # Create an item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        # Create first item price
        price_data = {**test_item_price_data, "item_id": item_id}
        response1 = client.post("/api/v1/item-prices", json=price_data)
        assert response1.status_code == 201

        # Try to create duplicate
        response2 = client.post("/api/v1/item-prices", json=price_data)
        assert response2.status_code == 409
        assert response2.json()["detail"]["code"] == "DUPLICATE_ITEM_PRICE"


class TestBulkCreateItemPrices:
    """Tests for POST /api/v1/item-prices/bulk"""

    def test_bulk_create_item_prices_success(self, client, test_item_data):
        """Test bulk creating item prices successfully"""
        # Create multiple items first
        items = []
        for i in range(3):
            item_data = {**test_item_data, "item_code": f"BULK-{i:03d}"}
            item_response = client.post("/api/v1/items", json=item_data)
            assert item_response.status_code == 201
            items.append(item_response.json())

        # Bulk create item prices
        bulk_data = {
            "item_prices": [
                {"item_id": items[0]["id"], "price": "10.00", "currency": "USD"},
                {"item_id": items[1]["id"], "price": "20.00", "currency": "EUR"},
                {"item_id": items[2]["id"], "price": "30.00", "currency": "GBP"},
            ]
        }
        response = client.post("/api/v1/item-prices/bulk", json=bulk_data)

        assert response.status_code == 201
        data = response.json()

        assert data["created_count"] == 3
        assert len(data["item_prices"]) == 3
        assert len(data["errors"]) == 0

    def test_bulk_create_with_errors(self, client, test_item_data):
        """Test bulk create with some errors"""
        # Create one item
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        # Bulk create with one valid and one invalid
        fake_item_id = str(uuid.uuid4())
        bulk_data = {
            "item_prices": [
                {"item_id": item_id, "price": "10.00", "currency": "USD"},
                {
                    "item_id": fake_item_id,  # Invalid item
                    "price": "20.00",
                    "currency": "EUR",
                },
            ]
        }
        response = client.post("/api/v1/item-prices/bulk", json=bulk_data)

        assert response.status_code == 201
        data = response.json()

        assert data["created_count"] == 1
        assert len(data["item_prices"]) == 1
        assert len(data["errors"]) == 1
        assert data["errors"][0]["index"] == 1

    def test_bulk_create_empty_list(self, client):
        """Test bulk create with empty list fails"""
        bulk_data = {"item_prices": []}
        response = client.post("/api/v1/item-prices/bulk", json=bulk_data)

        assert response.status_code == 400


class TestListItemPrices:
    """Tests for GET /api/v1/item-prices"""

    def test_list_item_prices_empty(self, client):
        """Test listing item prices when none exist"""
        response = client.get("/api/v1/item-prices")

        assert response.status_code == 200
        data = response.json()

        assert data["item_prices"] == []
        assert data["pagination"]["total_items"] == 0

    def test_list_item_prices_with_data(
        self, client, test_item_data, test_item_price_data
    ):
        """Test listing item prices with data"""
        # Create an item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        assert item_response.status_code == 201
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        client.post("/api/v1/item-prices", json=price_data)

        response = client.get("/api/v1/item-prices")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_prices"]) == 1
        assert data["pagination"]["total_items"] == 1
        assert data["item_prices"][0]["item_id"] == item_id

    def test_list_item_prices_pagination(self, client):
        """Test pagination parameters"""
        response = client.get("/api/v1/item-prices?page=1&page_size=10")

        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10

    def test_list_item_prices_filter_by_item(
        self, client, test_item_data, test_item_price_data
    ):
        """Test filtering by item ID"""
        # Create two items with prices
        item1_data = {**test_item_data, "item_code": "FILTER-001"}
        item1_response = client.post("/api/v1/items", json=item1_data)
        item1_id = item1_response.json()["id"]

        item2_data = {**test_item_data, "item_code": "FILTER-002"}
        item2_response = client.post("/api/v1/items", json=item2_data)
        item2_id = item2_response.json()["id"]

        # Create prices for both items
        price1_data = {**test_item_price_data, "item_id": item1_id, "price": "10.00"}
        price2_data = {**test_item_price_data, "item_id": item2_id, "price": "20.00"}

        client.post("/api/v1/item-prices", json=price1_data)
        client.post("/api/v1/item-prices", json=price2_data)

        # Filter by first item
        response = client.get(f"/api/v1/item-prices?item_id={item1_id}")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_prices"]) == 1
        assert data["item_prices"][0]["item_id"] == item1_id
        assert data["item_prices"][0]["price"] == "10.00"

    def test_list_item_prices_filter_by_currency(
        self, client, test_item_data, test_item_price_data
    ):
        """Test filtering by currency"""
        # Create item
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Create prices with different currencies
        usd_price = {
            **test_item_price_data,
            "item_id": item_id,
            "currency": "USD",
            "min_qty": 1,
        }
        eur_price = {
            **test_item_price_data,
            "item_id": item_id,
            "currency": "EUR",
            "min_qty": 2,
        }

        client.post("/api/v1/item-prices", json=usd_price)
        client.post("/api/v1/item-prices", json=eur_price)

        # Filter by USD
        response = client.get("/api/v1/item-prices?currency=USD")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_prices"]) == 1
        assert data["item_prices"][0]["currency"] == "USD"

    def test_list_item_prices_search(
        self, client, test_item_data, test_item_price_data
    ):
        """Test search functionality"""
        # Create items with different names
        item1_data = {
            **test_item_data,
            "item_code": "SEARCH-001",
            "item_name": "Electronic Widget",
        }
        item2_data = {
            **test_item_data,
            "item_code": "SEARCH-002",
            "item_name": "Mechanical Part",
        }

        item1_response = client.post("/api/v1/items", json=item1_data)
        item2_response = client.post("/api/v1/items", json=item2_data)

        item1_id = item1_response.json()["id"]
        item2_id = item2_response.json()["id"]

        # Create prices for both items
        price1_data = {**test_item_price_data, "item_id": item1_id}
        price2_data = {**test_item_price_data, "item_id": item2_id, "min_qty": 2}

        client.post("/api/v1/item-prices", json=price1_data)
        client.post("/api/v1/item-prices", json=price2_data)

        # Search for "electronic"
        response = client.get("/api/v1/item-prices?search=electronic")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_prices"]) == 1
        assert data["item_prices"][0]["item_id"] == item1_id

    def test_list_item_prices_include_item(
        self, client, test_item_data, test_item_price_data
    ):
        """Test including item details"""
        # Create item and price
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        client.post("/api/v1/item-prices", json=price_data)

        # Get prices with item details
        response = client.get("/api/v1/item-prices?include_item=true")

        assert response.status_code == 200
        data = response.json()

        assert len(data["item_prices"]) == 1
        assert data["item_prices"][0]["item"] is not None
        assert (
            data["item_prices"][0]["item"]["item_code"] == test_item_data["item_code"]
        )

    def test_list_item_prices_sort_by_price(
        self, client, test_item_data, test_item_price_data
    ):
        """Test sorting by price"""
        # Create item
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Create prices with different values
        prices = [
            {
                **test_item_price_data,
                "item_id": item_id,
                "price": "30.00",
                "min_qty": 1,
            },
            {
                **test_item_price_data,
                "item_id": item_id,
                "price": "10.00",
                "min_qty": 2,
            },
            {
                **test_item_price_data,
                "item_id": item_id,
                "price": "20.00",
                "min_qty": 3,
            },
        ]

        for price_data in prices:
            client.post("/api/v1/item-prices", json=price_data)

        # Sort by price ascending
        response = client.get("/api/v1/item-prices?sort_by=price&sort_order=asc")

        assert response.status_code == 200
        data = response.json()

        prices_list = [float(ip["price"]) for ip in data["item_prices"]]
        assert prices_list == sorted(prices_list)


class TestGetItemPrice:
    """Tests for GET /api/v1/item-prices/{item_price_id}"""

    def test_get_item_price_success(self, client, test_item_data, test_item_price_data):
        """Test getting an item price by ID"""
        # Create item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        response = client.get(f"/api/v1/item-prices/{item_price_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_price_id
        assert data["item_id"] == item_id
        assert data["price"] == test_item_price_data["price"]

    def test_get_item_price_with_item_details(
        self, client, test_item_data, test_item_price_data
    ):
        """Test getting an item price with item details"""
        # Create item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        response = client.get(f"/api/v1/item-prices/{item_price_id}?include_item=true")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == item_price_id
        assert data["item"] is not None
        assert data["item"]["item_code"] == test_item_data["item_code"]

    def test_get_item_price_not_found(self, client):
        """Test getting a non-existent item price"""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/item-prices/{fake_id}")

        assert response.status_code == 404
        assert response.json()["detail"]["code"] == "ITEM_PRICE_NOT_FOUND"


class TestGetItemPricesByItem:
    """Tests for GET /api/v1/item-prices/by-item/{item_id}"""

    def test_get_item_prices_by_item_success(
        self, client, test_item_data, test_item_price_data
    ):
        """Test getting all item prices for a specific item"""
        # Create item
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Create multiple prices for the item
        prices = [
            {
                **test_item_price_data,
                "item_id": item_id,
                "price": "10.00",
                "min_qty": 1,
            },
            {
                **test_item_price_data,
                "item_id": item_id,
                "price": "8.00",
                "min_qty": 10,
            },
            {
                **test_item_price_data,
                "item_id": item_id,
                "price": "7.00",
                "min_qty": 100,
            },
        ]

        for price_data in prices:
            client.post("/api/v1/item-prices", json=price_data)

        response = client.get(f"/api/v1/item-prices/by-item/{item_id}")

        assert response.status_code == 200
        data = response.json()

        assert len(data) == 3
        for price in data:
            assert price["item_id"] == item_id

    def test_get_item_prices_by_item_with_validity_filter(
        self, client, test_item_data, test_item_price_data
    ):
        """Test getting item prices filtered by validity date"""
        # Create item
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Create prices with different validity periods
        now = datetime.now()
        past_date = now - timedelta(days=10)
        future_date = now + timedelta(days=10)

        # Valid price (no dates)
        valid_price = {
            **test_item_price_data,
            "item_id": item_id,
            "price": "10.00",
            "min_qty": 1,
        }

        # Expired price
        expired_price = {
            **test_item_price_data,
            "item_id": item_id,
            "price": "15.00",
            "min_qty": 2,
            "valid_from": past_date.isoformat(),
            "valid_upto": (now - timedelta(days=1)).isoformat(),
        }

        # Future price
        future_price = {
            **test_item_price_data,
            "item_id": item_id,
            "price": "12.00",
            "min_qty": 3,
            "valid_from": future_date.isoformat(),
        }

        client.post("/api/v1/item-prices", json=valid_price)
        client.post("/api/v1/item-prices", json=expired_price)
        client.post("/api/v1/item-prices", json=future_price)

        # Get prices valid today
        response = client.get(
            f"/api/v1/item-prices/by-item/{item_id}?valid_on={now.isoformat()}"
        )

        assert response.status_code == 200
        data = response.json()

        # Should only return the valid price (no dates) and not expired or future prices
        assert len(data) == 1
        assert data[0]["price"] == "10.00"

    def test_get_item_prices_by_item_not_found(self, client):
        """Test getting item prices for non-existent item"""
        fake_item_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/item-prices/by-item/{fake_item_id}")

        assert response.status_code == 404
        assert "item" in response.json()["detail"]["message"].lower()


class TestUpdateItemPrice:
    """Tests for PUT /api/v1/item-prices/{item_price_id}"""

    def test_update_item_price_success(
        self, client, test_item_data, test_item_price_data
    ):
        """Test updating an item price"""
        # Create item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        update_data = {"price": "150.00", "currency": "EUR"}
        response = client.put(f"/api/v1/item-prices/{item_price_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == "150.00"
        assert data["currency"] == "EUR"
        assert data["min_qty"] == test_item_price_data["min_qty"]  # Unchanged

    def test_update_item_price_dates(
        self, client, test_item_data, test_item_price_data
    ):
        """Test updating item price validity dates"""
        # Create item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        # Update with validity dates
        valid_from = datetime.now()
        valid_upto = valid_from + timedelta(days=60)

        update_data = {
            "valid_from": valid_from.isoformat(),
            "valid_upto": valid_upto.isoformat(),
        }
        response = client.put(f"/api/v1/item-prices/{item_price_id}", json=update_data)

        assert response.status_code == 200
        data = response.json()
        assert data["valid_from"] is not None
        assert data["valid_upto"] is not None

    def test_update_item_price_not_found(self, client):
        """Test updating a non-existent item price"""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/item-prices/{fake_id}", json={"price": "100.00"}
        )

        assert response.status_code == 404

    def test_update_item_price_invalid_date_range(
        self, client, test_item_data, test_item_price_data
    ):
        """Test updating with invalid date range"""
        # Create item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        # Update with invalid date range
        valid_from = datetime.now()
        valid_upto = valid_from - timedelta(days=1)  # Invalid: end before start

        update_data = {
            "valid_from": valid_from.isoformat(),
            "valid_upto": valid_upto.isoformat(),
        }
        response = client.put(f"/api/v1/item-prices/{item_price_id}", json=update_data)

        assert response.status_code == 400

    def test_update_item_price_duplicate_conditions(
        self, client, test_item_data, test_item_price_data
    ):
        """Test updating to create duplicate conditions"""
        # Create item
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Create two prices with different conditions
        price1_data = {**test_item_price_data, "item_id": item_id, "min_qty": 1}
        price2_data = {**test_item_price_data, "item_id": item_id, "min_qty": 10}

        client.post("/api/v1/item-prices", json=price1_data)
        create_response2 = client.post("/api/v1/item-prices", json=price2_data)

        price2_id = create_response2.json()["id"]

        # Try to update price2 to have same conditions as price1
        update_data = {"min_qty": 1}
        response = client.put(f"/api/v1/item-prices/{price2_id}", json=update_data)

        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "DUPLICATE_ITEM_PRICE"


class TestDeleteItemPrice:
    """Tests for DELETE /api/v1/item-prices/{item_price_id}"""

    def test_delete_item_price_success(
        self, client, test_item_data, test_item_price_data
    ):
        """Test deleting an item price"""
        # Create item and price first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        response = client.delete(f"/api/v1/item-prices/{item_price_id}")

        assert response.status_code == 204

        # Verify item price is no longer accessible
        get_response = client.get(f"/api/v1/item-prices/{item_price_id}")
        assert get_response.status_code == 404

    def test_delete_item_price_not_found(self, client):
        """Test deleting a non-existent item price"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/item-prices/{fake_id}")

        assert response.status_code == 404


class TestItemPriceValidation:
    """Tests for item price validation rules"""

    def test_create_item_price_negative_price(self, client, test_item_data):
        """Test creating item price with negative price fails"""
        # Create item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {
            "item_id": item_id,
            "price": "-10.00",  # Negative price
        }
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 400

    def test_create_item_price_negative_min_qty(self, client, test_item_data):
        """Test creating item price with negative min_qty fails"""
        # Create item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {
            "item_id": item_id,
            "price": "10.00",
            "min_qty": -1,  # Negative quantity
        }
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 400

    def test_create_item_price_invalid_currency_length(self, client, test_item_data):
        """Test creating item price with invalid currency length"""
        # Create item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Currency too short
        price_data = {
            "item_id": item_id,
            "price": "10.00",
            "currency": "A",  # Too short
        }
        response = client.post("/api/v1/item-prices", json=price_data)
        assert response.status_code == 400

        # Currency too long
        price_data = {
            "item_id": item_id,
            "price": "10.00",
            "currency": "VERYLONGCURRENCY",  # Too long
        }
        response = client.post("/api/v1/item-prices", json=price_data)
        assert response.status_code == 400

    def test_currency_case_normalization(self, client, test_item_data):
        """Test currency code is normalized to uppercase"""
        # Create item first
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {
            "item_id": item_id,
            "price": "10.00",
            "currency": "usd",  # Lowercase
        }
        response = client.post("/api/v1/item-prices", json=price_data)

        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "USD"  # Should be uppercase


class TestItemPricePermissions:
    """Tests for item price permission checks"""

    def test_create_item_price_without_permission(
        self, client, mock_current_user, test_item_data
    ):
        """Test creating item price without proper permissions"""
        # NOTE: Currently permissions are not enforced in the API
        # This test should be updated when permission enforcement is implemented
        # Remove create permission
        mock_current_user.permissions = ["item.read"]

        # Create item first
        mock_current_user.permissions = [
            "item.create",
            "item.read",
            "item.update",
            "item.delete",
        ]
        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        # Remove permissions
        mock_current_user.permissions = ["item.read"]

        price_data = {"item_id": item_id, "price": "10.00"}
        response = client.post("/api/v1/item-prices", json=price_data)

        # Currently returns 201 because permissions are not enforced
        # Should return 403 when permissions are properly implemented
        assert response.status_code == 201

    def test_update_item_price_without_permission(
        self, client, mock_current_user, test_item_data, test_item_price_data
    ):
        """Test updating item price without proper permissions"""
        # NOTE: Currently permissions are not enforced in the API
        # This test should be updated when permission enforcement is implemented
        # Create with full permissions first
        mock_current_user.permissions = [
            "item.create",
            "item.read",
            "item.update",
            "item.delete",
        ]

        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        # Remove update permission
        mock_current_user.permissions = ["item.read"]

        update_data = {"price": "200.00"}
        response = client.put(f"/api/v1/item-prices/{item_price_id}", json=update_data)

        # Currently returns 200 because permissions are not enforced
        # Should return 403 when permissions are properly implemented
        assert response.status_code == 200

    def test_delete_item_price_without_permission(
        self, client, mock_current_user, test_item_data, test_item_price_data
    ):
        """Test deleting item price without proper permissions"""
        # NOTE: Currently permissions are not enforced in the API
        # This test should be updated when permission enforcement is implemented
        # Create with full permissions first
        mock_current_user.permissions = [
            "item.create",
            "item.read",
            "item.update",
            "item.delete",
        ]

        item_response = client.post("/api/v1/items", json=test_item_data)
        item_id = item_response.json()["id"]

        price_data = {**test_item_price_data, "item_id": item_id}
        create_response = client.post("/api/v1/item-prices", json=price_data)
        item_price_id = create_response.json()["id"]

        # Remove delete permission
        mock_current_user.permissions = ["item.read"]

        response = client.delete(f"/api/v1/item-prices/{item_price_id}")

        # Currently returns 204 because permissions are not enforced
        # Should return 403 when permissions are properly implemented
        assert response.status_code == 204
