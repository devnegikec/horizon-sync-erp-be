"""ItemPackagingUnitService — CRUD and lookup for item packaging units.

Handles:
- Paginated listing of packaging units per item
- Creating packaging units with duplicate-name detection
- Partial updates with 404 guard
- Soft-deletion (is_active = False)
- QR-identifier lookup for inbound scan resolution

Requirements: 2.4, 2.5, 2.6
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.schemas.item_packaging_unit import (
    ItemPackagingUnitCreate,
    ItemPackagingUnitUpdate,
)


class ItemPackagingUnitService:
    """Service for managing packaging units per item."""

    # ------------------------------------------------------------------
    # LIST
    # ------------------------------------------------------------------

    def list_packaging_units(
        self,
        item_id: UUID,
        org_id: UUID,
        db: Session,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> dict:
        """Return a paginated list of packaging units for an item.

        Args:
            item_id: The item whose packaging units to list.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session.
            page: 1-based page number.
            page_size: Number of records per page.
            is_active: Optional filter — True/False to filter by active status.

        Returns:
            Dict with keys ``packaging_units`` (list of ItemPackagingUnit) and
            ``pagination`` (dict with page metadata).
        """
        query = db.query(ItemPackagingUnit).filter(
            ItemPackagingUnit.item_id == item_id,
            ItemPackagingUnit.organization_id == org_id,
        )

        if is_active is not None:
            query = query.filter(ItemPackagingUnit.is_active == is_active)

        total_items = query.count()
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        packaging_units = (
            query.order_by(ItemPackagingUnit.created_at.asc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return {
            "packaging_units": packaging_units,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ------------------------------------------------------------------
    # CREATE
    # ------------------------------------------------------------------

    def create_packaging_unit(
        self,
        item_id: UUID,
        data: ItemPackagingUnitCreate,
        org_id: UUID,
        db: Session,
    ) -> ItemPackagingUnit:
        """Create a new packaging unit for an item.

        Validates that the item exists and belongs to the organisation, then
        inserts the row.  The DB unique constraint ``uq_item_unit_name`` on
        ``(item_id, unit_name)`` is caught and surfaced as HTTP 409.

        Args:
            item_id: The item to attach the packaging unit to.
            data: Validated creation payload.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session.

        Returns:
            The newly created ItemPackagingUnit row.

        Raises:
            HTTPException 404: Item not found or belongs to a different org.
            HTTPException 409: A packaging unit with the same unit_name already
                exists for this item.
            HTTPException 422: conversion_factor is <= 0 (belt-and-suspenders
                guard; Pydantic already rejects this at the schema layer).
        """
        # Guard: conversion_factor must be positive
        if data.conversion_factor <= 0:
            raise HTTPException(
                status_code=422,
                detail="conversion_factor must be greater than 0",
            )

        # Verify item exists and belongs to the org
        item = (
            db.query(Item)
            .filter(
                Item.id == item_id,
                Item.organization_id == org_id,
            )
            .first()
        )
        if item is None:
            raise HTTPException(
                status_code=404,
                detail=f"Item {item_id} not found",
            )

        packaging_unit = ItemPackagingUnit(
            organization_id=org_id,
            item_id=item_id,
            unit_name=data.unit_name,
            qr_identifier=data.qr_identifier,
            conversion_factor=data.conversion_factor,
            items_per_master_pack=data.items_per_master_pack,
            length_mm=data.length_mm,
            width_mm=data.width_mm,
            height_mm=data.height_mm,
            weight_grams=data.weight_grams,
            is_base_unit=data.is_base_unit,
            is_active=data.is_active,
        )
        db.add(packaging_unit)

        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            # Detect the unique constraint on (item_id, unit_name)
            exc_str = str(exc.orig).lower() if exc.orig else str(exc).lower()
            if "uq_item_unit_name" in exc_str or "unique" in exc_str:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Packaging unit '{data.unit_name}' already exists for this item"
                    ),
                ) from exc
            raise

        db.refresh(packaging_unit)
        return packaging_unit

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update_packaging_unit(
        self,
        item_id: UUID,
        unit_id: UUID,
        data: ItemPackagingUnitUpdate,
        org_id: UUID,
        db: Session,
    ) -> ItemPackagingUnit:
        """Partially update a packaging unit.

        Only fields explicitly set in *data* are applied (None values are
        skipped so callers can omit fields they do not want to change).

        Args:
            item_id: The item the packaging unit belongs to.
            unit_id: The packaging unit to update.
            data: Partial update payload.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session.

        Returns:
            The updated ItemPackagingUnit row.

        Raises:
            HTTPException 404: Packaging unit not found, or belongs to a
                different item / organisation.
        """
        packaging_unit = (
            db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.id == unit_id,
                ItemPackagingUnit.item_id == item_id,
                ItemPackagingUnit.organization_id == org_id,
            )
            .first()
        )
        if packaging_unit is None:
            raise HTTPException(
                status_code=404,
                detail=f"Packaging unit {unit_id} not found",
            )

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(packaging_unit, field, value)

        try:
            db.flush()
        except IntegrityError as exc:
            db.rollback()
            exc_str = str(exc.orig).lower() if exc.orig else str(exc).lower()
            if "uq_item_unit_name" in exc_str or "unique" in exc_str:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Packaging unit '{data.unit_name}' already exists for this item"
                    ),
                ) from exc
            raise

        db.refresh(packaging_unit)
        return packaging_unit

    # ------------------------------------------------------------------
    # SOFT DELETE
    # ------------------------------------------------------------------

    def soft_delete_packaging_unit(
        self,
        item_id: UUID,
        unit_id: UUID,
        org_id: UUID,
        db: Session,
    ) -> ItemPackagingUnit:
        """Soft-delete a packaging unit by setting is_active = False.

        Does not hard-delete the row so that existing FK references in
        ``scan_session_items`` and ``bin_stock_levels`` remain valid.

        Args:
            item_id: The item the packaging unit belongs to.
            unit_id: The packaging unit to deactivate.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session.

        Returns:
            The updated ItemPackagingUnit row with is_active = False.

        Raises:
            HTTPException 404: Packaging unit not found.
        """
        packaging_unit = (
            db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.id == unit_id,
                ItemPackagingUnit.item_id == item_id,
                ItemPackagingUnit.organization_id == org_id,
            )
            .first()
        )
        if packaging_unit is None:
            raise HTTPException(
                status_code=404,
                detail=f"Packaging unit {unit_id} not found",
            )

        packaging_unit.is_active = False
        db.flush()
        db.refresh(packaging_unit)
        return packaging_unit

    # ------------------------------------------------------------------
    # QR IDENTIFIER LOOKUP
    # ------------------------------------------------------------------

    def resolve_by_qr_identifier(
        self,
        qr_identifier: str,
        org_id: UUID,
        db: Session,
    ) -> Optional[ItemPackagingUnit]:
        """Look up an active packaging unit by its QR identifier.

        Used during inbound scanning to resolve ``packaging_unit_qr_id`` from
        the QR payload to an ``ItemPackagingUnit`` row.  Returns ``None``
        (rather than raising) when not found so callers can treat the lookup
        as best-effort.

        Args:
            qr_identifier: The QR identifier string to look up.
            org_id: Organization ID for tenant isolation.
            db: SQLAlchemy session.

        Returns:
            The matching active ItemPackagingUnit, or None if not found /
            inactive.
        """
        return (
            db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.qr_identifier == qr_identifier,
                ItemPackagingUnit.organization_id == org_id,
                ItemPackagingUnit.is_active.is_(True),
            )
            .first()
        )
