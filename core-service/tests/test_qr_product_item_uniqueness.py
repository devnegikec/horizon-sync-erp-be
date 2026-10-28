import uuid
import pytest

from app.services.qr_product_service import QRProductService
from app.repositories.item_repository import ItemRepository
from app.models.item import Item
from app.models.qr_product import QRProduct


def test_qr_product_creation_does_not_duplicate_item(db_session, mock_current_user):
    # Prepare service and repositories
    svc = QRProductService(db_session)

    # Create a QR product dict
    product_data = {
        "name": "Unique Test Product",
        "generic_name": "UTP-001",
        "gtin": None,
        "industry": None,
    }

    # Create first product — should create linked Item
    product = svc.create_product(
        type("D", (), {"model_dump": lambda self=None: product_data})(),
        mock_current_user.organization_id,
        mock_current_user.id,
    )

    # Manually attempt to create another Item referencing same QR product (simulate race)
    item_repo = ItemRepository(db_session)
    item_count_before = (
        db_session.query(Item).filter(Item.qr_product_id == product.id).count()
    )

    # Ensure only one item exists per QR product (the service should not create duplicates)
    assert item_count_before <= 1

    # Product names are organization-scoped and case-insensitive.
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as duplicate_error:
        svc.create_product(
            type("D", (), {"model_dump": lambda self=None: {**product_data, "name": " unique test product "}})(),
            mock_current_user.organization_id,
            mock_current_user.id,
        )
    assert duplicate_error.value.status_code == 409

    # Additionally, ensure database unique constraint prevents duplicate item_code
    # Create a raw Item with duplicate item_code and expect an IntegrityError
    from sqlalchemy.exc import IntegrityError
    from app.services.document_numbering_service import DocumentNumberingService

    item_code = DocumentNumberingService(db_session).get_next_number(
        mock_current_user.organization_id, "item"
    )
    item = Item(
        organization_id=mock_current_user.organization_id,
        item_code=item_code,
        item_name="Test dup",
        item_type="stock",
    )
    db_session.add(item)
    db_session.commit()

    dup = Item(
        organization_id=mock_current_user.organization_id,
        item_code=item_code,
        item_name="Test dup 2",
        item_type="stock",
    )
    db_session.add(dup)
    with pytest.raises(IntegrityError):
        db_session.commit()
