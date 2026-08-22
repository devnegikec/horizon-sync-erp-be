"""Temporary verification that ItemResponse reflects packaging_units."""
import uuid

from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.schemas.item import ItemResponse


def test_item_response_reflects_packaging(db_session):
    org_id = uuid.uuid4()
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code="TMP-001",
        item_name="Tmp Item",
        item_type="stock",
        uom="Nos",
    )
    db_session.add(item)
    db_session.flush()

    pu = ItemPackagingUnit(
        organization_id=org_id,
        item_id=item.id,
        unit_name="Each",
        conversion_factor=1,
        length_mm=100,
        width_mm=50,
        height_mm=20,
        weight_grams=250,
        is_base_unit=True,
        is_active=True,
    )
    db_session.add(pu)
    db_session.commit()

    db_session.refresh(item)
    resp = ItemResponse.model_validate(item)
    assert resp.packaging_units is not None, "packaging_units is None"
    assert len(resp.packaging_units) == 1
    assert resp.packaging_units[0].unit_name == "Each"
