"""Unit tests for UOM Conversion service

Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 5.1, 5.2, 5.3, 5.4
"""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import (
    DuplicateUOMConversionException,
    ItemNotFoundException,
    UOMConversionNotFoundException,
    ValidationError,
)
from app.schemas.uom_conversion import UOMConversionCreate, UOMConversionUpdate
from app.services.uom_conversion_service import UOMConversionService


@pytest.fixture
def conversion_service(db_session):
    """Create a UOM Conversion service instance with a test DB session."""
    return UOMConversionService(db_session)


@pytest.fixture
def sample_conversion(conversion_service, sample_item_id, sample_organization_id, sample_user_id):
    """Create and return a sample UOM conversion for reuse in tests."""
    data = UOMConversionCreate(
        item_id=sample_item_id,
        from_uom="Box",
        to_uom="Pieces",
        conversion_factor=Decimal("12.000000"),
    )
    return conversion_service.create_conversion(data, sample_organization_id, sample_user_id)


# ── Create ──────────────────────────────────────────────────────────────


def test_create_conversion_with_valid_data(
    conversion_service, sample_item_id, sample_organization_id, sample_user_id
):
    """Validates: Requirements 2.1"""
    data = UOMConversionCreate(
        item_id=sample_item_id,
        from_uom="Kg",
        to_uom="Gram",
        conversion_factor=Decimal("1000"),
    )
    conv = conversion_service.create_conversion(data, sample_organization_id, sample_user_id)

    assert conv.id is not None
    assert conv.item_id == sample_item_id
    assert conv.from_uom == "Kg"
    assert conv.to_uom == "Gram"
    assert conv.conversion_factor == Decimal("1000")
    assert conv.organization_id == sample_organization_id
    assert conv.created_by == sample_user_id
    assert conv.updated_by == sample_user_id
    assert conv.deleted_at is None


def test_create_conversion_duplicate_triple_raises_409(
    conversion_service, sample_conversion, sample_item_id, sample_organization_id, sample_user_id
):
    """Validates: Requirements 2.6"""
    duplicate = UOMConversionCreate(
        item_id=sample_item_id,
        from_uom="Box",
        to_uom="Pieces",
        conversion_factor=Decimal("24"),
    )
    with pytest.raises(DuplicateUOMConversionException):
        conversion_service.create_conversion(duplicate, sample_organization_id, sample_user_id)


def test_create_conversion_item_not_found_raises_404(
    conversion_service, sample_organization_id, sample_user_id
):
    """Validates: Requirements 2.8"""
    data = UOMConversionCreate(
        item_id=uuid.uuid4(),
        from_uom="Kg",
        to_uom="Gram",
        conversion_factor=Decimal("1000"),
    )
    with pytest.raises(ItemNotFoundException):
        conversion_service.create_conversion(data, sample_organization_id, sample_user_id)


def test_create_conversion_positive_factor_validation():
    """Validates: Requirements 2.7 — Pydantic rejects zero/negative conversion_factor."""
    with pytest.raises(Exception):
        UOMConversionCreate(
            item_id=uuid.uuid4(),
            from_uom="Kg",
            to_uom="Gram",
            conversion_factor=Decimal("0"),
        )

    with pytest.raises(Exception):
        UOMConversionCreate(
            item_id=uuid.uuid4(),
            from_uom="Kg",
            to_uom="Gram",
            conversion_factor=Decimal("-5"),
        )


# ── Get ─────────────────────────────────────────────────────────────────


def test_get_conversion_by_id(
    conversion_service, sample_conversion, sample_organization_id
):
    """Validates: Requirements 2.3"""
    fetched = conversion_service.get_conversion(sample_conversion.id, sample_organization_id)

    assert fetched.id == sample_conversion.id
    assert fetched.from_uom == "Box"
    assert fetched.to_uom == "Pieces"
    assert fetched.conversion_factor == Decimal("12.000000")


def test_get_conversion_not_found_raises_404(conversion_service, sample_organization_id):
    """Validates: Requirements 2.3"""
    with pytest.raises(UOMConversionNotFoundException):
        conversion_service.get_conversion(uuid.uuid4(), sample_organization_id)


# ── List ────────────────────────────────────────────────────────────────


def test_list_conversions_with_pagination(
    conversion_service, sample_item_id, sample_organization_id, sample_user_id
):
    """Validates: Requirements 2.2"""
    uom_pairs = [("Kg", "Gram"), ("Box", "Pieces"), ("Litre", "mL")]
    for from_uom, to_uom in uom_pairs:
        data = UOMConversionCreate(
            item_id=sample_item_id,
            from_uom=from_uom,
            to_uom=to_uom,
            conversion_factor=Decimal("100"),
        )
        conversion_service.create_conversion(data, sample_organization_id, sample_user_id)

    conversions, pagination = conversion_service.list_conversions(
        sample_organization_id, page=1, page_size=2
    )

    assert len(conversions) == 2
    assert pagination["total_items"] == 3
    assert pagination["total_pages"] == 2
    assert pagination["has_next"] is True
    assert pagination["has_prev"] is False


def test_list_conversions_filtered_by_item_id(
    conversion_service, sample_item_id, sample_organization_id, sample_user_id, db_session, mock_current_user
):
    """Validates: Requirements 2.2"""
    from app.models.item import Item

    # Create a second item
    item2 = Item(
        id=uuid.uuid4(),
        organization_id=sample_organization_id,
        item_code="TEST-ITEM-002",
        item_name="Test Item 2",
        item_type="stock",
        uom="Nos",
        maintain_stock=True,
        standard_rate=50.00,
        valuation_rate=40.00,
        created_by=mock_current_user.id,
        updated_by=mock_current_user.id,
    )
    db_session.add(item2)
    db_session.commit()
    db_session.refresh(item2)

    # Create conversions for both items
    conversion_service.create_conversion(
        UOMConversionCreate(item_id=sample_item_id, from_uom="Kg", to_uom="Gram", conversion_factor=Decimal("1000")),
        sample_organization_id, sample_user_id,
    )
    conversion_service.create_conversion(
        UOMConversionCreate(item_id=item2.id, from_uom="Box", to_uom="Pieces", conversion_factor=Decimal("12")),
        sample_organization_id, sample_user_id,
    )

    # Filter by first item
    conversions, pagination = conversion_service.list_conversions(
        sample_organization_id, item_id=sample_item_id
    )
    assert len(conversions) == 1
    assert conversions[0].item_id == sample_item_id
    assert pagination["total_items"] == 1


# ── Update ──────────────────────────────────────────────────────────────


def test_update_conversion(
    conversion_service, sample_conversion, sample_organization_id, sample_user_id
):
    """Validates: Requirements 2.4"""
    update_data = UOMConversionUpdate(conversion_factor=Decimal("24"))
    updated = conversion_service.update_conversion(
        sample_conversion.id, update_data, sample_organization_id, sample_user_id
    )

    assert updated.conversion_factor == Decimal("24")
    # from_uom and to_uom should remain unchanged
    assert updated.from_uom == "Box"
    assert updated.to_uom == "Pieces"


# ── Soft-delete ─────────────────────────────────────────────────────────


def test_soft_delete_conversion(
    conversion_service, sample_conversion, sample_organization_id, sample_user_id
):
    """Validates: Requirements 2.5"""
    conversion_service.delete_conversion(
        sample_conversion.id, sample_organization_id, sample_user_id
    )

    # Should not be retrievable after soft-delete
    with pytest.raises(UOMConversionNotFoundException):
        conversion_service.get_conversion(sample_conversion.id, sample_organization_id)

    # Should not appear in list
    conversions, pagination = conversion_service.list_conversions(sample_organization_id)
    assert len(conversions) == 0
    assert pagination["total_items"] == 0


# ── convert_quantity ────────────────────────────────────────────────────


def test_convert_quantity_forward(
    conversion_service, sample_conversion, sample_item_id, sample_organization_id
):
    """Validates: Requirements 5.1 — result = quantity × conversion_factor"""
    result = conversion_service.convert_quantity(
        item_id=sample_item_id,
        from_uom="Box",
        to_uom="Pieces",
        quantity=Decimal("5"),
        organization_id=sample_organization_id,
    )
    # 5 Box × 12 = 60 Pieces
    assert result == Decimal("5") * Decimal("12.000000")


def test_convert_quantity_reverse(
    conversion_service, sample_conversion, sample_item_id, sample_organization_id
):
    """Validates: Requirements 5.2 — result = quantity / reverse_factor"""
    result = conversion_service.convert_quantity(
        item_id=sample_item_id,
        from_uom="Pieces",
        to_uom="Box",
        quantity=Decimal("60"),
        organization_id=sample_organization_id,
    )
    # 60 Pieces / 12 = 5 Box
    assert result == Decimal("60") / Decimal("12.000000")


def test_convert_quantity_identity(
    conversion_service, sample_item_id, sample_organization_id
):
    """Validates: Requirements 5.4 — same UOM returns original quantity, no DB lookup."""
    result = conversion_service.convert_quantity(
        item_id=sample_item_id,
        from_uom="Kg",
        to_uom="Kg",
        quantity=Decimal("42.5"),
        organization_id=sample_organization_id,
    )
    assert result == Decimal("42.5")


def test_convert_quantity_missing_raises_validation_error(
    conversion_service, sample_item_id, sample_organization_id
):
    """Validates: Requirements 5.3 — no forward or reverse conversion raises ValidationError."""
    with pytest.raises(ValidationError):
        conversion_service.convert_quantity(
            item_id=sample_item_id,
            from_uom="Kg",
            to_uom="Litre",
            quantity=Decimal("10"),
            organization_id=sample_organization_id,
        )
