# Implementation Plan: WMS Multi-UOM Packaging Units

## Overview

Implement multi-unit-of-measure support for the WMS inbound workflow. The plan follows strict dependency order: schema first, then models, then schemas, then services, then API, then service updates, then tests. All stock quantities remain in Eaches; packaging unit data is metadata for traceability and volumetric bin assignment.

## Tasks

- [x] 1. Alembic migration 048 — schema foundation
  - [x] 1.1 Create `048_add_multi_uom_packaging_units.py` with `down_revision = "047_extend_pick_lists_and_create_put_away_lists"`
    - In `upgrade()`: create `item_packaging_units` table first (all other FK columns reference it), then add `sku` to `items`, then add `packaging_unit_id` to `bin_stock_levels`, then add `max_volume_cc` / `max_weight_grams` to `warehouse_locations`, then rename `quantity` → `raw_quantity` on `scan_session_items`, then add `packaging_unit_id` to `scan_session_items`
    - Include all `op.create_index` / `op.create_unique_index` calls: `idx_ipu_org`, `idx_ipu_item_id`, `idx_ipu_qr_identifier` (partial unique where not null), `idx_items_sku`
    - Include `UniqueConstraint("item_id", "unit_name", name="uq_item_unit_name")` and `CheckConstraint("conversion_factor > 0", name="chk_conversion_factor_positive")`
    - In `downgrade()`: reverse in strict reverse order — drop FK columns before dropping `item_packaging_units`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 2. SQLAlchemy models
  - [x] 2.1 Create `app/models/item_packaging_unit.py` with `ItemPackagingUnit` model
    - Columns: `id`, `organization_id`, `item_id` (FK → `items.id` CASCADE), `unit_name`, `qr_identifier` (unique), `conversion_factor` (Numeric 15,6), `length_mm`, `width_mm`, `height_mm`, `weight_grams` (all Numeric 10,2 nullable), `is_base_unit`, `is_active`, `created_at`, `updated_at`
    - `__table_args__`: `UniqueConstraint("item_id", "unit_name")`, `CheckConstraint("conversion_factor > 0")`
    - Relationship: `item = relationship("Item", back_populates="packaging_units")`
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 2.2 Update `app/models/item.py` — add `sku` column and `packaging_units` relationship
    - Add `sku = Column(String(100), nullable=True, index=True)` after the `uom` column
    - Add `packaging_units = relationship("ItemPackagingUnit", back_populates="item", cascade="all, delete-orphan")`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [x] 2.3 Update `app/models/bin_stock_level.py` — add `packaging_unit_id` column and relationship
    - Add `packaging_unit_id = Column(UUID(as_uuid=True), ForeignKey("item_packaging_units.id", ondelete="SET NULL"), nullable=True)`
    - Add `packaging_unit = relationship("ItemPackagingUnit")`
    - Do NOT add `packaging_unit_id` to the `uq_bin_item_batch` constraint
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 2.4 Update `app/models/warehouse_location.py` — add volumetric capacity columns
    - Add `max_volume_cc = Column(Numeric(15, 2), nullable=True)` and `max_weight_grams = Column(Numeric(15, 2), nullable=True)`
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 2.5 Update `app/models/scan_session.py` — rename `quantity` → `raw_quantity` and add `packaging_unit_id`
    - Replace `quantity = Column(Integer, nullable=False)` with `raw_quantity = Column(Integer, nullable=False)`
    - Add `packaging_unit_id = Column(UUID(as_uuid=True), ForeignKey("item_packaging_units.id", ondelete="SET NULL"), nullable=True)`
    - Add `packaging_unit = relationship("ItemPackagingUnit")`
    - Update `__repr__` to reference `raw_quantity`
    - _Requirements: 5.1, 5.2, 5.4_

- [x] 3. Pydantic schemas
  - [x] 3.1 Create `app/schemas/item_packaging_unit.py`
    - `ItemPackagingUnitCreate`: `unit_name`, `qr_identifier` (optional), `conversion_factor` (Decimal, gt=0), `length_mm`, `width_mm`, `height_mm`, `weight_grams` (all optional Decimal ge=0), `is_base_unit`, `is_active`; include `@field_validator("conversion_factor")` rejecting ≤ 0
    - `ItemPackagingUnitUpdate`: all fields optional, same validator on `conversion_factor`
    - `ItemPackagingUnitResponse`: `model_config = ConfigDict(from_attributes=True)`, all columns including `id`, `organization_id`, `item_id`, timestamps
    - `ItemPackagingUnitListResponse`: `packaging_units: list[ItemPackagingUnitResponse]`, `pagination: dict`
    - _Requirements: 2.1, 2.5_

  - [x] 3.2 Update inbound QR payload and scan result schemas
    - In the existing QR payload schema (wherever `QRPayload` is defined), add `packaging_unit_qr_id: Optional[str] = None`
    - In the existing `ScanResult` response schema, rename `quantity` → `raw_quantity` and add `packaging_unit_id: Optional[UUID] = None`
    - _Requirements: 5.3, 5.5_

- [x] 4. ItemPackagingUnitService
  - [x] 4.1 Create `app/services/item_packaging_unit_service.py` with `ItemPackagingUnitService`
    - `list_packaging_units(item_id, org_id, db, page, page_size)` — paginated query filtered by `item_id` and `organization_id`; optionally filter by `is_active`
    - `create_packaging_unit(item_id, data, org_id, db)` — verify item exists and belongs to org; insert row; catch `IntegrityError` on `uq_item_unit_name` and raise HTTP 409; raise HTTP 422 if `conversion_factor <= 0`
    - `update_packaging_unit(item_id, unit_id, data, org_id, db)` — partial update; raise HTTP 404 if not found or belongs to different item/org
    - `soft_delete_packaging_unit(item_id, unit_id, org_id, db)` — set `is_active = False`; raise HTTP 404 if not found
    - `resolve_by_qr_identifier(qr_identifier, org_id, db)` — query active row by `qr_identifier`; return `None` if not found
    - _Requirements: 2.4, 2.5, 2.6_

- [x] 5. API router for packaging units
  - [x] 5.1 Create `app/api/v1/endpoints/item_packaging_units.py` router
    - `GET /api/v1/items/{item_id}/packaging-units` → `ItemPackagingUnitListResponse` (200); query params: `page`, `page_size`, `is_active`
    - `POST /api/v1/items/{item_id}/packaging-units` → `ItemPackagingUnitResponse` (201); body: `ItemPackagingUnitCreate`; errors: 404, 409, 422
    - `PATCH /api/v1/items/{item_id}/packaging-units/{id}` → `ItemPackagingUnitResponse` (200); body: `ItemPackagingUnitUpdate`; error: 404
    - `DELETE /api/v1/items/{item_id}/packaging-units/{id}` → `ItemPackagingUnitResponse` (200) with `is_active: false`; error: 404
    - Register router in `app/api/v1/api.py` (or equivalent router aggregator)
    - _Requirements: 2.6_

- [x] 6. VolumetricAssignmentService
  - [x] 6.1 Create `app/services/volumetric_assignment_service.py` with `VolumetricAssignmentService`
    - `assign_bins(put_away_list_items, warehouse_id, org_id, db)` — iterates each item, calls `_get_packaging_unit`, `_calc_volume`, `_calc_weight`, `_find_best_bin`; mutates `item.bin_location_id` in place; if no bin found, leaves `bin_location_id = None` without aborting
    - `_calc_volume(quantity, pu)` — returns `quantity * L * W * H / 1000` (mm³ → cc) only when all three dimensions are non-null; else `None`
    - `_calc_weight(quantity, pu)` — returns `quantity * weight_grams` when non-null; else `None`
    - `_find_best_bin(item_id, batch_number, warehouse_id, org_id, required_volume_cc, required_weight_g, db)` — executes the volumetric allocation SQL with `bin_usage` CTE, `consolidation` CTE, volume/weight WHERE clauses, `ORDER BY consolidation DESC, tightest fit ASC`, `LIMIT 1 FOR UPDATE SKIP LOCKED`; returns `WarehouseLocation` or `None`
    - All DB operations share the caller's session (no new transaction)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9_

- [x] 7. InboundService updates
  - [x] 7.1 Update `record_scan()` in `InboundService` to store `raw_quantity` and resolve `packaging_unit_qr_id`
    - After decoding QR payload, if `payload.packaging_unit_qr_id` is present, call `ItemPackagingUnitService.resolve_by_qr_identifier()`; store result id in `packaging_unit_id` (leave null if not found — best-effort)
    - Store `raw_quantity=payload.qty` (renamed field) and `packaging_unit_id` on the new `ScanSessionItem`
    - _Requirements: 5.3, 5.5, 5.6_

- [x] 8. ReceivingSlipService updates
  - [x] 8.1 Update `approve_slip()` in `ReceivingSlipService` to convert `raw_quantity` → Eaches at approval time
    - For each `ScanSessionItem` with non-null `packaging_unit_id`: fetch `ItemPackagingUnit`; if not found or `is_active = False`, raise HTTP 422 with message `"Packaging unit {id} not found or inactive. Cannot approve slip."`
    - Compute `eaches_qty = int(scan_item.raw_quantity * pu.conversion_factor)`
    - For items with null `packaging_unit_id`: use `raw_quantity` directly as Eaches
    - Aggregate by `(sku, batch_number)` into `receiving_slip_items.quantity`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 9. PutAwayService updates
  - [x] 9.1 Update `generate_from_slip()` in `PutAwayService` to call `VolumetricAssignmentService` in the same transaction
    - After creating `PutAwayList` and `PutAwayListItem` rows, instantiate `VolumetricAssignmentService` and call `assign_bins(put_away_list.items, slip.warehouse_id, org_id, db)`
    - Call `db.flush()` after `assign_bins` to persist bin assignments before returning
    - _Requirements: 7.1, 7.6, 7.7_

  - [x] 9.2 Update `complete_item()` in `PutAwayService` to set `packaging_unit_id` on `BinStockLevel`
    - After updating `quantity_on_hand` on the `BinStockLevel` row, if the put-away item carries a `packaging_unit_id`, set `bin_stock.packaging_unit_id = put_away_item.packaging_unit_id`
    - _Requirements: 3.3_

- [x] 10. Checkpoint — verify migration and models
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Unit tests for ItemPackagingUnitService and VolumetricAssignmentService
  - [x] 11.1 Write unit tests for `ItemPackagingUnitService`
    - Test `create_packaging_unit`: happy path, duplicate `unit_name` raises 409, `conversion_factor <= 0` raises 422, item not found raises 404
    - Test `soft_delete_packaging_unit`: sets `is_active = False`, not-found raises 404
    - Test `resolve_by_qr_identifier`: returns unit when active, returns `None` when inactive or not found
    - _Requirements: 2.4, 2.5, 2.6_

  - [x] 11.2 Write unit tests for `VolumetricAssignmentService._calc_volume` and `_calc_weight`
    - `_calc_volume`: returns correct cc when all three dims present; returns `None` when any dim is null
    - `_calc_weight`: returns correct grams when `weight_grams` present; returns `None` when null
    - _Requirements: 7.3, 7.4_

  - [x] 11.3 Write unit tests for `VolumetricAssignmentService.assign_bins`
    - Bin with sufficient capacity is assigned; bin with insufficient volume is skipped; bin with insufficient weight is skipped; no suitable bin leaves `bin_location_id = None` without raising
    - Consolidation preference: bin already holding same `(item_id, batch_number)` is ranked first
    - _Requirements: 7.5, 7.6, 7.7, 7.8_

- [x] 12. Property-based tests (Hypothesis) for correctness properties
  - [x] 12.1 Write property test: conversion_factor positivity invariant (Property 1)
    - For any `conversion_factor > 0`, `ItemPackagingUnit` creation succeeds; for any `conversion_factor <= 0`, it is rejected
    - **Property 1: conversion_factor > 0 is always enforced**
    - **Validates: Requirements 2.5**

  - [x] 12.2 Write property test: raw_quantity round-trip (Property 2)
    - For any positive integer `raw_quantity` and positive `conversion_factor`, `eaches = int(raw_quantity * conversion_factor)` is always ≥ `raw_quantity` when `conversion_factor >= 1`
    - **Property 2: Eaches quantity is never less than raw_quantity when conversion_factor ≥ 1**
    - **Validates: Requirements 6.2**

  - [x] 12.3 Write property test: null packaging_unit_id passes through raw_quantity unchanged (Property 3)
    - For any `raw_quantity`, when `packaging_unit_id` is null, `eaches_qty == raw_quantity`
    - **Property 3: null packaging_unit_id → identity conversion**
    - **Validates: Requirements 6.3**

  - [x] 12.4 Write property test: volume calculation unit consistency (Property 4)
    - For any positive `length_mm`, `width_mm`, `height_mm`, and `quantity`, `_calc_volume` returns `quantity * L * W * H / 1000` and the result is always positive
    - **Property 4: volume_cc is always positive when all dimensions are positive**
    - **Validates: Requirements 7.3**

  - [x] 12.5 Write property test: null dimension makes volume unconstrained (Property 5)
    - For any combination where at least one of `length_mm`, `width_mm`, `height_mm` is null, `_calc_volume` returns `None`
    - **Property 5: any null dimension → unconstrained volume**
    - **Validates: Requirements 7.3, 4.4**

  - [x] 12.6 Write property test: null weight makes weight unconstrained (Property 6)
    - When `weight_grams` is null, `_calc_weight` returns `None` for any quantity
    - **Property 6: null weight_grams → unconstrained weight**
    - **Validates: Requirements 7.4, 4.4**

  - [x] 12.7 Write property test: bin capacity check is monotone (Property 7)
    - If a bin accepts a required volume `V`, it also accepts any `V' < V` (given the same occupied volume)
    - **Property 7: capacity acceptance is monotone in required volume**
    - **Validates: Requirements 7.5**

  - [x] 12.8 Write property test: assign_bins never raises when no bin is available (Property 8)
    - For any list of put-away items and an empty warehouse, `assign_bins` completes without exception and all `bin_location_id` values are `None`
    - **Property 8: assign_bins is total — never raises on empty candidate set**
    - **Validates: Requirements 7.7**

  - [x] 12.9 Write property test: consolidation preference is stable (Property 9)
    - When a consolidation bin and a non-consolidation bin both have sufficient capacity, the consolidation bin is always selected
    - **Property 9: consolidation bin is always preferred over non-consolidation bin**
    - **Validates: Requirements 7.8**

  - [x] 12.10 Write property test: unique qr_identifier per organisation (Property 10)
    - Attempting to create two `ItemPackagingUnit` rows with the same `qr_identifier` in the same org raises an integrity error
    - **Property 10: qr_identifier uniqueness is enforced**
    - **Validates: Requirements 2.2, 2.3**

  - [x] 12.11 Write property test: unique (item_id, unit_name) constraint (Property 11)
    - Attempting to create two packaging units with the same `(item_id, unit_name)` raises HTTP 409 regardless of other field values
    - **Property 11: (item_id, unit_name) uniqueness is enforced**
    - **Validates: Requirements 2.2**

  - [x] 12.12 Write property test: soft-delete preserves FK references (Property 12)
    - After soft-deleting a packaging unit (`is_active = False`), existing `scan_session_items` and `bin_stock_levels` rows that reference it still have a valid (non-null) `packaging_unit_id` FK
    - **Property 12: soft-delete does not cascade to referencing rows**
    - **Validates: Requirements 2.6, 3.1, 5.1**

- [x] 13. Integration test for full inbound flow with packaging units
  - [x] 13.1 Write integration test covering the complete inbound flow
    - Setup: create item with `sku`, create `ItemPackagingUnit` (Box of 12, `conversion_factor=12`, with dimensions and weight), create warehouse with bins that have `max_volume_cc` and `max_weight_grams`
    - Step 1: start inbound scan session; record scan with QR payload containing `packaging_unit_qr_id`; assert `ScanSessionItem.raw_quantity` is stored and `packaging_unit_id` is resolved
    - Step 2: end session → receiving slip created
    - Step 3: approve slip; assert `ReceivingSlipItem.quantity = raw_quantity * conversion_factor` (Eaches); assert HTTP 422 is raised if packaging unit is inactive
    - Step 4: assert `PutAwayList` is generated; assert `PutAwayListItem.bin_location_id` is set by `VolumetricAssignmentService` to a bin with sufficient capacity
    - Step 5: complete put-away item; assert `BinStockLevel.packaging_unit_id` is set and `quantity_on_hand` is in Eaches
    - _Requirements: 5.3, 5.5, 6.1, 6.2, 6.4, 7.1, 7.6, 3.3_

- [x] 14. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Migration 048 must be applied before any other task can be tested against a live database
- `VolumetricAssignmentService` shares the caller's DB session — never open a new transaction inside it
- `bin_stock_levels.packaging_unit_id` is metadata only; it is NOT part of the `uq_bin_item_batch` unique constraint
- All stock quantities in `bin_stock_levels.quantity_on_hand` and `receiving_slip_items.quantity` are always in Eaches
- Conversion from packaging units to Eaches happens exactly once: at receiving slip approval
- Property tests use Hypothesis; run with `pytest --hypothesis-seed=0` for reproducibility

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "2.2", "2.3", "2.4", "2.5"] },
    { "id": 2, "tasks": ["3.1", "3.2"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["5.1", "6.1"] },
    { "id": 5, "tasks": ["7.1", "8.1", "9.1", "9.2"] },
    { "id": 6, "tasks": ["11.1", "11.2", "11.3"] },
    {
      "id": 7,
      "tasks": [
        "12.1",
        "12.2",
        "12.3",
        "12.4",
        "12.5",
        "12.6",
        "12.7",
        "12.8",
        "12.9",
        "12.10",
        "12.11",
        "12.12"
      ]
    },
    { "id": 8, "tasks": ["13.1"] }
  ]
}
```
