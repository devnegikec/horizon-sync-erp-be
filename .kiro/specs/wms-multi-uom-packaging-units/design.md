# Design Document: WMS Multi-UOM Packaging Units

## Overview

This feature extends the WMS inbound workflow to support multiple units of measure (UOM) per SKU. It introduces a new `item_packaging_units` table, adds a `sku` column to `items`, adds volumetric capacity fields to `warehouse_locations`, adds packaging unit traceability to `bin_stock_levels` and `scan_session_items`, and introduces a `VolumetricAssignmentService` that automatically assigns bin locations to put-away list items based on available volume and weight capacity.

### Key Design Decisions

1. **Stock always tracked in Eaches** — `bin_stock_levels.quantity_on_hand` is always in base units (Eaches). `packaging_unit_id` on that table is metadata only.
2. **Conversion at approval, not at scan time** — `scan_session_items.raw_quantity` stores the raw scanned quantity in the packaging unit's own units. Multiplication by `conversion_factor` happens only when a receiving slip is approved.
3. **Volumetric assignment in the same transaction as put-away list creation** — The `VolumetricAssignmentService` runs inside the same DB transaction as `PutAwayService.generate_from_slip()`.
4. **`SELECT ... FOR UPDATE SKIP LOCKED`** — Candidate bin rows are locked during assignment to prevent concurrent double-assignment.
5. **Consolidation preference** — Bins already containing the same `(item_id, batch_number)` are ranked first before empty or mixed bins.
6. **Null capacity = unconstrained** — If `max_volume_cc` or `max_weight_grams` is null on a bin, that dimension is not checked during assignment.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                         API Layer (FastAPI Routers)                           │
├──────────────────────────────────────────────────────────────────────────────┤
│  ItemPackagingUnitEndpoints  │  InboundEndpoints  │  PutAwayEndpoints         │
│  GET/POST/PATCH/DELETE                                                        │
│  /api/v1/items/{item_id}/packaging-units                                      │
└────────────┬─────────────────────────┬──────────────────────┬────────────────┘
             │                         │                      │
┌────────────▼─────────────────────────▼──────────────────────▼────────────────┐
│                            Service Layer                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│  ItemPackagingUnitService  │  VolumetricAssignmentService                     │
│  InboundService (updated)  │  ReceivingSlipService (updated)                  │
│  PutAwayService (updated)  │                                                  │
└────────────┬─────────────────────────┬──────────────────────┬────────────────┘
             │                         │                      │
┌────────────▼─────────────────────────▼──────────────────────▼────────────────┐
│                        PostgreSQL (SQLAlchemy + Alembic)                       │
├──────────────────────────────────────────────────────────────────────────────┤
│  items (+ sku column)                │  item_packaging_units (new)            │
│  bin_stock_levels (+ packaging_unit_id)  │  warehouse_locations (+ vol/weight)│
│  scan_session_items (quantity→raw_quantity, + packaging_unit_id)              │
│  put_away_list_items (bin_location_id set by VolumetricAssignmentService)     │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Data Models

### 1. `items` table — new `sku` column

```sql
ALTER TABLE items ADD COLUMN sku VARCHAR(100) NULL;
CREATE INDEX idx_items_sku ON items(sku);
```

**SQLAlchemy model addition** (in `app/models/item.py`):

```python
# Add after the existing `uom` column
sku = Column(String(100), nullable=True, index=True)
```

`sku` is independent of `item_code`. Both fields coexist on the same record. `item_code` is the ERP-internal reference; `sku` is the warehouse-facing identifier used in scanning workflows.

---

### 2. `item_packaging_units` table (new)

```sql
CREATE TABLE item_packaging_units (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id   UUID NOT NULL,
    item_id           UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    unit_name         VARCHAR(100) NOT NULL,
    qr_identifier     VARCHAR(255) NULL,
    conversion_factor NUMERIC(15, 6) NOT NULL,
    length_mm         NUMERIC(10, 2) NULL,
    width_mm          NUMERIC(10, 2) NULL,
    height_mm         NUMERIC(10, 2) NULL,
    weight_grams      NUMERIC(10, 2) NULL,
    is_base_unit      BOOLEAN NOT NULL DEFAULT FALSE,
    is_active         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_item_unit_name UNIQUE (item_id, unit_name),
    CONSTRAINT chk_conversion_factor_positive CHECK (conversion_factor > 0)
);

CREATE INDEX idx_ipu_item_id ON item_packaging_units(item_id);
CREATE UNIQUE INDEX idx_ipu_qr_identifier ON item_packaging_units(qr_identifier)
    WHERE qr_identifier IS NOT NULL;
```

**SQLAlchemy model** (new file `app/models/item_packaging_unit.py`):

```python
"""ItemPackagingUnit model — defines packaging units per item with physical dimensions"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean, CheckConstraint, Column, DateTime, ForeignKey,
    Numeric, String, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.types import UUID


class ItemPackagingUnit(Base):
    """Defines a packaging unit for an item (e.g., Each, Box of 12, Pallet of 144)."""

    __tablename__ = "item_packaging_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    item_id = Column(
        UUID(as_uuid=True),
        ForeignKey("items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    unit_name = Column(String(100), nullable=False)
    qr_identifier = Column(String(255), nullable=True, unique=True)
    conversion_factor = Column(Numeric(15, 6), nullable=False)
    length_mm = Column(Numeric(10, 2), nullable=True)
    width_mm = Column(Numeric(10, 2), nullable=True)
    height_mm = Column(Numeric(10, 2), nullable=True)
    weight_grams = Column(Numeric(10, 2), nullable=True)
    is_base_unit = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        UniqueConstraint("item_id", "unit_name", name="uq_item_unit_name"),
        CheckConstraint("conversion_factor > 0", name="chk_conversion_factor_positive"),
    )

    # Relationships
    item = relationship("Item", back_populates="packaging_units")

    def __repr__(self):
        return (
            f"<ItemPackagingUnit(id={self.id}, item={self.item_id}, "
            f"unit='{self.unit_name}', factor={self.conversion_factor})>"
        )
```

Add to `Item` model:

```python
packaging_units = relationship(
    "ItemPackagingUnit", back_populates="item", cascade="all, delete-orphan"
)
```

---

### 3. `bin_stock_levels` table — new `packaging_unit_id` column

```sql
ALTER TABLE bin_stock_levels
    ADD COLUMN packaging_unit_id UUID NULL
        REFERENCES item_packaging_units(id) ON DELETE SET NULL;
```

The existing unique constraint `uq_bin_item_batch` on `(bin_location_id, item_id, batch_number)` is **unchanged**. `packaging_unit_id` is metadata only.

**SQLAlchemy model addition** (in `app/models/bin_stock_level.py`):

```python
packaging_unit_id = Column(
    UUID(as_uuid=True),
    ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
    nullable=True,
)

# Relationship
packaging_unit = relationship("ItemPackagingUnit")
```

---

### 4. `warehouse_locations` table — volumetric capacity columns

```sql
ALTER TABLE warehouse_locations
    ADD COLUMN max_volume_cc    NUMERIC(15, 2) NULL,
    ADD COLUMN max_weight_grams NUMERIC(15, 2) NULL;
```

**SQLAlchemy model addition** (in `app/models/warehouse_location.py`):

```python
max_volume_cc    = Column(Numeric(15, 2), nullable=True)
max_weight_grams = Column(Numeric(15, 2), nullable=True)
```

---

### 5. `scan_session_items` table — rename `quantity` + add `packaging_unit_id`

```sql
ALTER TABLE scan_session_items
    RENAME COLUMN quantity TO raw_quantity;

ALTER TABLE scan_session_items
    ADD COLUMN packaging_unit_id UUID NULL
        REFERENCES item_packaging_units(id) ON DELETE SET NULL;
```

**SQLAlchemy model update** (in `app/models/scan_session.py`):

```python
# Replace:  quantity = Column(Integer, nullable=False)
raw_quantity = Column(Integer, nullable=False)

# Add:
packaging_unit_id = Column(
    UUID(as_uuid=True),
    ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
    nullable=True,
)
packaging_unit = relationship("ItemPackagingUnit")
```

Update `__repr__` to reference `raw_quantity` instead of `quantity`.

## Pydantic Schemas

### `app/schemas/item_packaging_unit.py`

```python
"""Pydantic schemas for ItemPackagingUnit CRUD"""

from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ItemPackagingUnitCreate(BaseModel):
    unit_name: str = Field(..., min_length=1, max_length=100)
    qr_identifier: Optional[str] = Field(None, max_length=255)
    conversion_factor: Decimal = Field(..., gt=0, description="Must be > 0")
    length_mm: Optional[Decimal] = Field(None, ge=0)
    width_mm: Optional[Decimal] = Field(None, ge=0)
    height_mm: Optional[Decimal] = Field(None, ge=0)
    weight_grams: Optional[Decimal] = Field(None, ge=0)
    is_base_unit: bool = False
    is_active: bool = True

    @field_validator("conversion_factor")
    @classmethod
    def validate_conversion_factor(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("conversion_factor must be greater than 0")
        return v


class ItemPackagingUnitUpdate(BaseModel):
    unit_name: Optional[str] = Field(None, min_length=1, max_length=100)
    qr_identifier: Optional[str] = Field(None, max_length=255)
    conversion_factor: Optional[Decimal] = Field(None, gt=0)
    length_mm: Optional[Decimal] = Field(None, ge=0)
    width_mm: Optional[Decimal] = Field(None, ge=0)
    height_mm: Optional[Decimal] = Field(None, ge=0)
    weight_grams: Optional[Decimal] = Field(None, ge=0)
    is_base_unit: Optional[bool] = None

    @field_validator("conversion_factor")
    @classmethod
    def validate_conversion_factor(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v <= 0:
            raise ValueError("conversion_factor must be greater than 0")
        return v


class ItemPackagingUnitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    item_id: UUID
    unit_name: str
    qr_identifier: Optional[str] = None
    conversion_factor: Decimal
    length_mm: Optional[Decimal] = None
    width_mm: Optional[Decimal] = None
    height_mm: Optional[Decimal] = None
    weight_grams: Optional[Decimal] = None
    is_base_unit: bool
    is_active: bool
    created_at: object
    updated_at: object


class ItemPackagingUnitListResponse(BaseModel):
    packaging_units: list[ItemPackagingUnitResponse]
    pagination: dict
```

### Updated QR payload schema (inbound scan)

The existing QR payload JSON gains an optional field:

```python
class QRPayload(BaseModel):
    id: str                                    # qr_identifier
    sku: str
    qty: int = Field(..., gt=0)
    batch: str
    packaging_unit_qr_id: Optional[str] = None  # NEW — resolves to item_packaging_units.id
```

### Updated `ScanResult` response schema

```python
class ScanResult(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_item_id: UUID
    session_id: UUID
    qr_identifier: str
    sku: str
    raw_quantity: int          # renamed from quantity
    batch_number: str
    packaging_unit_id: Optional[UUID] = None   # NEW
    scanned_at: Optional[object] = None
    total_boxes_scanned: int
```

## Service Layer

### `ItemPackagingUnitService`

New service in `app/services/item_packaging_unit_service.py`.

```python
class ItemPackagingUnitService:

    def list_packaging_units(
        self, item_id: UUID, org_id: UUID, db: Session,
        page: int = 1, page_size: int = 20,
    ) -> dict:
        """Return paginated list of packaging units for an item."""

    def create_packaging_unit(
        self, item_id: UUID, data: ItemPackagingUnitCreate,
        org_id: UUID, db: Session,
    ) -> ItemPackagingUnit:
        """
        1. Verify item exists and belongs to org_id.
        2. Validate conversion_factor > 0 (also enforced by Pydantic + DB CHECK).
        3. Insert row; DB unique constraint on (item_id, unit_name) handles duplicates.
        4. Return created row.
        Raises:
            404 if item not found.
            409 if (item_id, unit_name) already exists.
            422 if conversion_factor <= 0.
        """

    def update_packaging_unit(
        self, item_id: UUID, unit_id: UUID, data: ItemPackagingUnitUpdate,
        org_id: UUID, db: Session,
    ) -> ItemPackagingUnit:
        """
        Partial update. Raises 404 if not found or belongs to different item/org.
        """

    def soft_delete_packaging_unit(
        self, item_id: UUID, unit_id: UUID, org_id: UUID, db: Session,
    ) -> ItemPackagingUnit:
        """Set is_active = False. Does not hard-delete to preserve FK references."""

    def resolve_by_qr_identifier(
        self, qr_identifier: str, org_id: UUID, db: Session,
    ) -> Optional[ItemPackagingUnit]:
        """Look up an active packaging unit by its qr_identifier."""
```

---

### `VolumetricAssignmentService`

New service in `app/services/volumetric_assignment_service.py`. Called from `PutAwayService.generate_from_slip()` within the same DB transaction.

```python
class VolumetricAssignmentService:

    def assign_bins(
        self,
        put_away_list_items: list[PutAwayListItem],
        warehouse_id: UUID,
        org_id: UUID,
        db: Session,
    ) -> None:
        """
        For each put_away_list_item, find and assign the best available bin.
        Mutates put_away_list_item.bin_location_id in place.
        All DB operations share the caller's transaction (db session).
        """
        for item in put_away_list_items:
            packaging_unit = self._get_packaging_unit(item, db)
            required_volume_cc = self._calc_volume(item.quantity, packaging_unit)
            required_weight_g  = self._calc_weight(item.quantity, packaging_unit)

            bin_loc = self._find_best_bin(
                item_id=item.item_id,
                batch_number=item.batch_number,
                warehouse_id=warehouse_id,
                org_id=org_id,
                required_volume_cc=required_volume_cc,
                required_weight_g=required_weight_g,
                db=db,
            )
            # bin_loc may be None — that is acceptable (Req 7.7)
            item.bin_location_id = bin_loc.id if bin_loc else None

    def _calc_volume(
        self, quantity: Decimal, pu: Optional[ItemPackagingUnit]
    ) -> Optional[Decimal]:
        """
        Returns quantity * L * W * H / 1000 (mm³ → cc) if all three dimensions
        are non-null on the packaging unit, else None (unconstrained).
        """
        if pu and pu.length_mm and pu.width_mm and pu.height_mm:
            return quantity * pu.length_mm * pu.width_mm * pu.height_mm / Decimal(1000)
        return None

    def _calc_weight(
        self, quantity: Decimal, pu: Optional[ItemPackagingUnit]
    ) -> Optional[Decimal]:
        """Returns quantity * weight_grams if weight_grams is non-null, else None."""
        if pu and pu.weight_grams:
            return quantity * pu.weight_grams
        return None

    def _find_best_bin(
        self,
        item_id: UUID,
        batch_number: Optional[str],
        warehouse_id: UUID,
        org_id: UUID,
        required_volume_cc: Optional[Decimal],
        required_weight_g: Optional[Decimal],
        db: Session,
    ) -> Optional[WarehouseLocation]:
        """
        Executes the volumetric allocation SQL query (see below).
        Returns the best bin or None.
        """
```

#### Volumetric Allocation SQL Query Pattern

```sql
-- Step 1: compute currently occupied volume and weight per bin
WITH bin_usage AS (
    SELECT
        bsl.bin_location_id,
        COALESCE(SUM(
            bsl.quantity_on_hand
            * ipu.length_mm * ipu.width_mm * ipu.height_mm / 1000.0
        ), 0) AS occupied_volume_cc,
        COALESCE(SUM(
            bsl.quantity_on_hand * ipu.weight_grams
        ), 0) AS occupied_weight_g
    FROM bin_stock_levels bsl
    LEFT JOIN item_packaging_units ipu ON ipu.id = bsl.packaging_unit_id
    WHERE bsl.organization_id = :org_id
    GROUP BY bsl.bin_location_id
),

-- Step 2: consolidation flag — bins already holding same item+batch rank first
consolidation AS (
    SELECT bin_location_id, TRUE AS has_same_item
    FROM bin_stock_levels
    WHERE item_id = :item_id
      AND batch_number IS NOT DISTINCT FROM :batch_number
      AND organization_id = :org_id
      AND quantity_on_hand > 0
)

SELECT wl.id
FROM warehouse_locations wl
LEFT JOIN bin_usage bu ON bu.bin_location_id = wl.id
LEFT JOIN consolidation c ON c.bin_location_id = wl.id
WHERE wl.organization_id = :org_id
  AND wl.warehouse_id    = :warehouse_id
  AND wl.location_type   = 'bin'
  AND wl.is_active       = TRUE
  -- Volume check: skip if bin has no limit OR item has no volume
  AND (
      wl.max_volume_cc IS NULL
      OR :required_volume_cc IS NULL
      OR (wl.max_volume_cc - COALESCE(bu.occupied_volume_cc, 0)) >= :required_volume_cc
  )
  -- Weight check: skip if bin has no limit OR item has no weight
  AND (
      wl.max_weight_grams IS NULL
      OR :required_weight_g IS NULL
      OR (wl.max_weight_grams - COALESCE(bu.occupied_weight_g, 0)) >= :required_weight_g
  )
ORDER BY
    COALESCE(c.has_same_item, FALSE) DESC,  -- consolidation bins first
    (wl.max_volume_cc - COALESCE(bu.occupied_volume_cc, 0)) ASC  -- tightest fit
LIMIT 1
FOR UPDATE SKIP LOCKED
```

The `FOR UPDATE SKIP LOCKED` clause prevents two concurrent put-away list generations from assigning the same bin to conflicting items.

---

### `InboundService` — changes

In `record_scan()`, after decoding the QR payload:

```python
def record_scan(self, session_id, qr_data, worker_id, org_id, db):
    payload = self.decode_qr_payload(qr_data)  # parses JSON

    # Resolve packaging unit if present in payload
    packaging_unit_id = None
    if payload.packaging_unit_qr_id:
        pu = self.packaging_unit_service.resolve_by_qr_identifier(
            payload.packaging_unit_qr_id, org_id, db
        )
        if pu:
            packaging_unit_id = pu.id
        # If not found, leave null — do not raise; traceability is best-effort at scan time

    scan_item = ScanSessionItem(
        organization_id=org_id,
        session_id=session_id,
        qr_identifier=payload.id,
        sku=payload.sku,
        raw_quantity=payload.qty,          # renamed field
        batch_number=payload.batch,
        raw_qr_data=qr_data,
        packaging_unit_id=packaging_unit_id,  # new field
    )
    db.add(scan_item)
    # ... rest of method unchanged
```

---

### `ReceivingSlipService` — changes

In `approve_slip()`, the conversion loop:

```python
def approve_slip(self, slip_id, org_id, db):
    slip = self._get_slip_or_404(slip_id, org_id, db)
    # ... status checks ...

    session_items = (
        db.query(ScanSessionItem)
        .filter(ScanSessionItem.session_id == slip.session_id)
        .all()
    )

    slip_items_by_key: dict[tuple, ReceivingSlipItem] = {}

    for scan_item in session_items:
        if scan_item.packaging_unit_id is not None:
            pu = db.get(ItemPackagingUnit, scan_item.packaging_unit_id)
            if pu is None or not pu.is_active:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"Packaging unit {scan_item.packaging_unit_id} "
                        "not found or inactive. Cannot approve slip."
                    ),
                )
            eaches_qty = int(scan_item.raw_quantity * pu.conversion_factor)
        else:
            eaches_qty = scan_item.raw_quantity

        # Aggregate by (sku, batch_number) into receiving_slip_items
        key = (scan_item.sku, scan_item.batch_number)
        if key in slip_items_by_key:
            slip_items_by_key[key].quantity += eaches_qty
            slip_items_by_key[key].box_count += 1
        else:
            slip_items_by_key[key] = ReceivingSlipItem(
                organization_id=org_id,
                slip_id=slip.id,
                sku=scan_item.sku,
                batch_number=scan_item.batch_number,
                quantity=eaches_qty,
                box_count=1,
            )

    for item in slip_items_by_key.values():
        db.add(item)

    slip.status = ReceivingSlipStatus.PENDING_PUTAWAY
    # ... trigger put-away list generation ...
```

---

### `PutAwayService` — changes

`generate_from_slip()` now calls `VolumetricAssignmentService.assign_bins()` within the same transaction:

```python
def generate_from_slip(self, slip_id, org_id, db):
    # ... existing logic to create PutAwayList and PutAwayListItem rows ...

    # NEW: volumetric bin assignment in the same transaction
    self.volumetric_service.assign_bins(
        put_away_list_items=put_away_list.items,
        warehouse_id=slip.warehouse_id,
        org_id=org_id,
        db=db,
    )

    db.flush()
    return put_away_list
```

When completing a put-away item (`complete_item()`), optionally record `packaging_unit_id` on the `BinStockLevel` row:

```python
def complete_item(self, put_away_item_id, worker_id, org_id, db):
    # ... existing stock update logic ...
    # If the put-away item has a packaging_unit_id (from the receiving slip item),
    # set it on the bin_stock_level row as metadata.
    if put_away_item.packaging_unit_id:
        bin_stock.packaging_unit_id = put_away_item.packaging_unit_id
```

## API Endpoints

### `GET /api/v1/items/{item_id}/packaging-units`

List all packaging units for an item (paginated).

**Query params:** `page`, `page_size`, `is_active` (optional filter)

**Response `200`:**

```json
{
  "packaging_units": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "item_id": "uuid",
      "unit_name": "Box of 12",
      "qr_identifier": "BOX-12-WIDGET",
      "conversion_factor": "12.000000",
      "length_mm": "300.00",
      "width_mm": "200.00",
      "height_mm": "150.00",
      "weight_grams": "1440.00",
      "is_base_unit": false,
      "is_active": true,
      "created_at": "2025-07-15T10:00:00Z",
      "updated_at": "2025-07-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 3,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

---

### `POST /api/v1/items/{item_id}/packaging-units`

Create a new packaging unit for an item.

**Request body:**

```json
{
  "unit_name": "Box of 12",
  "qr_identifier": "BOX-12-WIDGET",
  "conversion_factor": 12,
  "length_mm": 300,
  "width_mm": 200,
  "height_mm": 150,
  "weight_grams": 1440,
  "is_base_unit": false
}
```

**Response `201`:** `ItemPackagingUnitResponse`

**Errors:**

- `404` — item not found
- `409` — `(item_id, unit_name)` already exists
- `422` — `conversion_factor <= 0`

---

### `PATCH /api/v1/items/{item_id}/packaging-units/{id}`

Partial update of a packaging unit. All fields optional.

**Response `200`:** `ItemPackagingUnitResponse`

**Errors:** `404` if not found or belongs to different item/org.

---

### `DELETE /api/v1/items/{item_id}/packaging-units/{id}`

Soft-delete: sets `is_active = false`. Does not hard-delete.

**Response `200`:** `ItemPackagingUnitResponse` with `is_active: false`

**Errors:** `404` if not found.

---

### Error Reference

| Code | Scenario                            | Detail                                                              |
| ---- | ----------------------------------- | ------------------------------------------------------------------- |
| 404  | Item not found                      | `"Item {item_id} not found"`                                        |
| 404  | Packaging unit not found            | `"Packaging unit {id} not found"`                                   |
| 409  | Duplicate unit name                 | `"Packaging unit '{unit_name}' already exists for this item"`       |
| 422  | conversion_factor <= 0              | `"conversion_factor must be greater than 0"`                        |
| 422  | Inactive packaging unit at approval | `"Packaging unit {id} not found or inactive. Cannot approve slip."` |

## Alembic Migration 048

**File:** `core-service/alembic/versions/048_add_multi_uom_packaging_units.py`

```python
"""Add multi-UOM packaging units: item_packaging_units table, sku on items,
   volumetric capacity on warehouse_locations, packaging_unit_id on
   bin_stock_levels and scan_session_items, rename quantity→raw_quantity.

Revision ID: 048_add_multi_uom_packaging_units
Revises: 047_extend_pick_lists_and_create_put_away_lists
Create Date: 2025-07-15

Requirements: 1.1, 1.2, 2.1, 2.2, 2.3, 3.1, 4.1, 4.2, 5.1, 5.2, 8.1–8.5
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "048_add_multi_uom_packaging_units"
down_revision = "047_extend_pick_lists_and_create_put_away_lists"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Create item_packaging_units (must come first — other tables FK to it) ──
    op.create_table(
        "item_packaging_units",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit_name", sa.String(100), nullable=False),
        sa.Column("qr_identifier", sa.String(255), nullable=True),
        sa.Column("conversion_factor", sa.Numeric(15, 6), nullable=False),
        sa.Column("length_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("width_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("height_mm", sa.Numeric(10, 2), nullable=True),
        sa.Column("weight_grams", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_base_unit", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("item_id", "unit_name", name="uq_item_unit_name"),
        sa.CheckConstraint("conversion_factor > 0", name="chk_conversion_factor_positive"),
    )
    op.create_index("idx_ipu_org", "item_packaging_units", ["organization_id"])
    op.create_index("idx_ipu_item_id", "item_packaging_units", ["item_id"])
    op.create_index(
        "idx_ipu_qr_identifier", "item_packaging_units", ["qr_identifier"],
        unique=True,
        postgresql_where=sa.text("qr_identifier IS NOT NULL"),
    )

    # ── 2. Add sku to items ──
    op.add_column("items", sa.Column("sku", sa.String(100), nullable=True))
    op.create_index("idx_items_sku", "items", ["sku"])

    # ── 3. Add packaging_unit_id to bin_stock_levels ──
    op.add_column(
        "bin_stock_levels",
        sa.Column(
            "packaging_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # ── 4. Add volumetric capacity to warehouse_locations ──
    op.add_column("warehouse_locations",
                  sa.Column("max_volume_cc", sa.Numeric(15, 2), nullable=True))
    op.add_column("warehouse_locations",
                  sa.Column("max_weight_grams", sa.Numeric(15, 2), nullable=True))

    # ── 5. Rename quantity → raw_quantity on scan_session_items ──
    op.alter_column("scan_session_items", "quantity", new_column_name="raw_quantity")

    # ── 6. Add packaging_unit_id to scan_session_items ──
    op.add_column(
        "scan_session_items",
        sa.Column(
            "packaging_unit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("item_packaging_units.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    # Reverse order: FK columns first, then the referenced table

    # ── 6. Drop packaging_unit_id from scan_session_items ──
    op.drop_column("scan_session_items", "packaging_unit_id")

    # ── 5. Rename raw_quantity → quantity on scan_session_items ──
    op.alter_column("scan_session_items", "raw_quantity", new_column_name="quantity")

    # ── 4. Drop volumetric capacity from warehouse_locations ──
    op.drop_column("warehouse_locations", "max_weight_grams")
    op.drop_column("warehouse_locations", "max_volume_cc")

    # ── 3. Drop packaging_unit_id from bin_stock_levels ──
    op.drop_column("bin_stock_levels", "packaging_unit_id")

    # ── 2. Drop sku from items ──
    op.drop_index("idx_items_sku", table_name="items")
    op.drop_column("items", "sku")

    # ── 1. Drop item_packaging_units (last — other tables no longer FK to it) ──
    op.drop_index("idx_ipu_qr_identifier", table_name="item_packaging_units")
    op.drop_index("idx_ipu_item_id", table_name="item_packaging_units")
    op.drop_index("idx_ipu_org", table_name="item_packaging_units")
    op.drop_table("item_packaging_units")
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

**Property Reflection:** After reviewing all testable criteria, the following consolidations were made:

- Properties 6 and 7 (conversion with and without packaging unit) are kept separate because they test distinct code paths (multiplication vs. identity), but they are combined into a single "conversion round-trip" framing.
- Properties 3 and 8 (bin capacity invariant and null-capacity unconstrained) are kept separate because they test different branches of the capacity check.
- Properties 9 and 10 (no-fit resilience and consolidation preference) are kept separate because they test different aspects of the assignment algorithm.

---

### Property 1: SKU independence from item_code

_For any_ item with `item_code` X and `sku` Y, updating `sku` to any value Z should leave `item_code` unchanged at X.

**Validates: Requirements 1.3**

---

### Property 2: Positive conversion factor enforcement

_For any_ value `v ≤ 0`, attempting to create or update an `ItemPackagingUnit` with `conversion_factor = v` should be rejected with a validation error before any database write occurs.

**Validates: Requirements 2.5**

---

### Property 3: Unique constraint on (item_id, unit_name)

_For any_ `item_id` and `unit_name`, inserting a second `ItemPackagingUnit` row with the same `(item_id, unit_name)` pair should raise an integrity error, regardless of the values of all other columns.

**Validates: Requirements 2.2**

---

### Property 4: packaging_unit_id excluded from bin stock unique constraint

_For any_ `(bin_location_id, item_id, batch_number)` combination, inserting two `BinStockLevel` rows with different `packaging_unit_id` values should raise a unique constraint error, confirming that `packaging_unit_id` is not part of the uniqueness key.

**Validates: Requirements 3.2**

---

### Property 5: No conversion at scan time

_For any_ QR scan with raw quantity `Q` and any `packaging_unit_qr_id`, the stored `scan_session_items.raw_quantity` should equal `Q` exactly — never `Q × conversion_factor`.

**Validates: Requirements 5.3**

---

### Property 6: QR identifier resolution round-trip

_For any_ `ItemPackagingUnit` with `qr_identifier` = `Q`, scanning a QR payload containing `packaging_unit_qr_id = Q` should store the correct `packaging_unit_id` (the UUID of that packaging unit) in `scan_session_items`.

**Validates: Requirements 5.5**

---

### Property 7: Conversion factor applied at approval

_For any_ `scan_session_items` row with `raw_quantity = R` and a non-null `packaging_unit_id` whose `conversion_factor = C`, approving the receiving slip should produce a `receiving_slip_items.quantity` equal to `R × C` (rounded to integer).

**Validates: Requirements 6.2**

---

### Property 8: Identity conversion for null packaging unit

_For any_ `scan_session_items` row with `raw_quantity = R` and `packaging_unit_id = null`, approving the receiving slip should produce a `receiving_slip_items.quantity` equal to `R`.

**Validates: Requirements 6.3**

---

### Property 9: Assigned bin always satisfies capacity constraints

_For any_ put-away list item assigned to a bin `B`, if `B.max_volume_cc` is non-null and the item's required volume is non-null, then `(B.max_volume_cc − occupied_volume_cc) ≥ required_volume_cc`. The same invariant holds for weight. If either limit is null, that dimension is unconstrained and the check is skipped.

**Validates: Requirements 4.4, 7.5**

---

### Property 10: Unassigned items do not abort put-away list creation

_For any_ put-away list item where no bin in the warehouse has sufficient capacity, the put-away list should still be created successfully with `bin_location_id = null` for that item. The transaction should commit.

**Validates: Requirements 7.7**

---

### Property 11: Consolidation preference

_For any_ put-away item where bin `B` already contains stock with the same `item_id` and `batch_number`, and bin `B` has sufficient capacity, `B` should be selected over any other bin `B'` that does not already contain that item/batch combination, even if `B'` has more available capacity.

**Validates: Requirements 7.8**

---

### Property 12: Assigned bin belongs to the correct warehouse

_For any_ put-away list generated from a receiving slip for warehouse `W`, every non-null `bin_location_id` assigned by the `VolumetricAssignmentService` should reference a `WarehouseLocation` with `warehouse_id = W` and `is_active = true`.

**Validates: Requirements 7.2**

## Error Handling

### Validation errors (422)

| Scenario                                 | Detail                                                              |
| ---------------------------------------- | ------------------------------------------------------------------- |
| `conversion_factor <= 0`                 | `"conversion_factor must be greater than 0"`                        |
| Inactive packaging unit at slip approval | `"Packaging unit {id} not found or inactive. Cannot approve slip."` |
| Missing packaging unit at slip approval  | `"Packaging unit {id} not found or inactive. Cannot approve slip."` |

### Conflict errors (409)

| Scenario                         | Detail                                                        |
| -------------------------------- | ------------------------------------------------------------- |
| Duplicate `(item_id, unit_name)` | `"Packaging unit '{unit_name}' already exists for this item"` |

### Not found errors (404)

| Scenario                 | Detail                            |
| ------------------------ | --------------------------------- |
| Item not found           | `"Item {item_id} not found"`      |
| Packaging unit not found | `"Packaging unit {id} not found"` |

### Volumetric assignment — non-fatal

When no bin is found for a put-away item, the service logs a warning and sets `bin_location_id = null`. No exception is raised. The put-away list is created and the manager can manually assign the bin later.

## Testing Strategy

### Unit tests (example-based)

- `ItemPackagingUnitService.create_packaging_unit` with `conversion_factor = 0` → 422
- `ItemPackagingUnitService.create_packaging_unit` with duplicate `unit_name` → 409
- `ReceivingSlipService.approve_slip` with inactive packaging unit → 422
- `VolumetricAssignmentService._calc_volume` with null dimensions → returns `None`
- `VolumetricAssignmentService._calc_volume` with all dimensions set → returns correct cc value
- Scan without `packaging_unit_qr_id` → `packaging_unit_id` is null on `ScanSessionItem`

### Property tests (Hypothesis)

Each property above maps to a Hypothesis test. Key generators:

- `st.decimals(min_value=Decimal("0.000001"), max_value=Decimal("9999"))` for `conversion_factor`
- `st.decimals(min_value=Decimal("-100"), max_value=Decimal("0"))` for invalid `conversion_factor`
- `st.integers(min_value=1, max_value=10000)` for `raw_quantity`
- `st.uuids()` for item/bin/org IDs
- Composite strategies for `(bin, item, packaging_unit)` triples

**Tag format:** `@settings(max_examples=100)` with `@given(...)` decorators.

### Integration tests

- Full inbound flow: scan with packaging unit → approve slip → verify Eaches quantity
- Concurrent put-away list generation: two workers generating lists simultaneously should not get the same bin assigned (tests `SKIP LOCKED`)
- Migration round-trip: `alembic upgrade 048` then `alembic downgrade 047` restores schema
