"""API endpoint tests for /capacity/*."""

import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.main import app
from app.models.warehouse import Warehouse
from app.models.warehouse_location import WarehouseLocation


@pytest.fixture
def wh_user():
    return CurrentUser(
        id=uuid.uuid4(),
        email="wh@example.com",
        organization_id=uuid.uuid4(),
        user_type="user",
        permissions=["warehouse.read", "warehouse.update"],
    )


@pytest.fixture
def client(db_session, wh_user):
    def override_get_db():
        yield db_session

    async def override_get_current_user():
        return wh_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _setup(db_session, org_id):
    warehouse_id = uuid.uuid4()
    wh = Warehouse(
        id=warehouse_id,
        organization_id=org_id,
        name="Test Warehouse",
        code="WH-01",
        use_volume=True,
        use_weight=False,
        full_threshold_pct=Decimal("0.90"),
        almost_full_threshold_pct=Decimal("0.70"),
    )
    db_session.add(wh)

    bin_loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code="BIN-01",
        full_path="BIN-01",
        max_volume_cc=Decimal("100000"),
        is_active=True,
        version=1,
    )
    db_session.add(bin_loc)
    db_session.commit()
    return warehouse_id, bin_loc


class TestCapacityEndpoints:
    def test_get_bin_capacity(self, db_session, client, wh_user):
        warehouse_id, bin_loc = _setup(db_session, wh_user.organization_id)

        resp = client.get(f"/api/v1/capacity/bins/{bin_loc.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["bin_id"] == str(bin_loc.id)
        assert data["bin_state"] == "empty"
        assert data["is_available"] is True

    def test_get_capacity_tree(self, db_session, client, wh_user):
        warehouse_id, _ = _setup(db_session, wh_user.organization_id)

        resp = client.get(f"/api/v1/capacity/warehouses/{warehouse_id}/tree")

        assert resp.status_code == 200
        data = resp.json()
        assert data["level"] == "warehouse"
        assert data["children"][0]["level"] == "bin"

    def test_get_bin_states(self, db_session, client, wh_user):
        warehouse_id, bin_loc = _setup(db_session, wh_user.organization_id)

        resp = client.get(f"/api/v1/capacity/warehouses/{warehouse_id}/bin-states")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["bin_id"] == str(bin_loc.id)

    def test_get_available_bins(self, db_session, client, wh_user):
        warehouse_id, bin_loc = _setup(db_session, wh_user.organization_id)

        resp = client.get(
            "/api/v1/capacity/bins/available",
            params={"warehouse_id": str(warehouse_id), "task_type": "put_away"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert any(r["bin_id"] == str(bin_loc.id) for r in data)

    def test_refresh_bin(self, db_session, client, wh_user):
        warehouse_id, bin_loc = _setup(db_session, wh_user.organization_id)

        resp = client.post(f"/api/v1/capacity/bins/{bin_loc.id}/refresh")

        assert resp.status_code == 200
        data = resp.json()
        assert data["bin_state"] == "empty"

    def test_permission_denied_without_warehouse_read(
        self, db_session, client, wh_user
    ):
        # Simulate a user without warehouse permissions
        wh_user.permissions = ["item.read"]
        warehouse_id, bin_loc = _setup(db_session, wh_user.organization_id)

        resp = client.get(f"/api/v1/capacity/bins/{bin_loc.id}")

        assert resp.status_code == 403
