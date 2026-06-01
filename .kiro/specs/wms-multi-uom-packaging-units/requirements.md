# Requirements Document

## Introduction

This feature extends the Warehouse Management System (WMS) to support multiple units of measure (UOM) per SKU through a new `item_packaging_units` table. It introduces a `sku` column on the `items` table, volumetric and weight capacity fields on `warehouse_locations`, packaging unit traceability on `bin_stock_levels` and `scan_session_items`, and an automated volumetric bin-assignment service that selects and assigns suitable bins to put-away list items in a single transaction during put-away list generation.

The system continues to track all stock quantities in base units (Eaches). Packaging unit information is metadata for traceability and display purposes only. Quantity conversion from a scanned packaging unit to Eaches occurs at receiving slip approval, not at scan time.

## Glossary

- **Item**: A product record in the `items` table. `item_code` is the internal ERP identifier (e.g. `ITM-001`). `sku` is the warehouse-facing Stock Keeping Unit identifier (e.g. `WIDGET-EA`) used in scanning workflows, put-away lists, and pick lists. Both fields coexist independently on the same record.
- **SKU**: Stock Keeping Unit — a warehouse-facing identifier stored in the `sku` column on `items`. Used as the primary lookup key when resolving QR scans to items. Distinct from `item_code`, which remains the ERP-internal reference.
- **Packaging Unit**: A defined unit of measure for an item (e.g., Each, Box of 12, Pallet of 144), stored in `item_packaging_units`. Each packaging unit has physical dimensions, weight, a QR identifier, and a `conversion_factor` expressing how many Eaches it contains.
- **Base Unit (Eaches)**: The canonical unit in which all stock quantities are stored and tracked in `bin_stock_levels`.
- **Conversion Factor**: The integer or decimal multiplier stored on a packaging unit that converts one packaging unit quantity into Eaches (e.g., a Box of 12 has `conversion_factor = 12`).
- **Scan Session Item**: A row in `scan_session_items` representing one QR scan during an inbound session. Stores the raw scanned quantity and the packaging unit used at scan time.
- **Receiving Slip Approval**: The manager action that transitions a receiving slip from `pending_review` to `pending_putaway`. At this point, raw scanned quantities are multiplied by their packaging unit `conversion_factor` to produce Eaches quantities for the receiving slip line items.
- **Put-Away List**: A work order directing warehouse workers to place received goods into specific bin locations.
- **Put-Away List Item**: A single line on a put-away list, referencing an item, quantity (in Eaches), and an assigned bin location.
- **Volumetric Auto-Assignment Service**: The service component that, during put-away list generation, selects suitable bin locations based on available volume and weight capacity, and assigns them to put-away list items in one database transaction.
- **Available Volume**: `max_volume_cc` minus the sum of volumes already occupied by stock in a bin, expressed in cubic centimetres (cc).
- **Available Weight**: `max_weight_grams` minus the sum of weights already stored in a bin, expressed in grams.
- **BinStockLevel**: A row in `bin_stock_levels` tracking `quantity_on_hand` for a specific `(bin_location_id, item_id, batch_number)` combination. The unique constraint on these three columns remains unchanged.
- **Alembic Migration**: A versioned database schema change script managed by Alembic. The next migration after 047 is numbered 048.

## Requirements

### Requirement 1: SKU Column on Items

**User Story:** As a warehouse manager, I want each item to carry an optional SKU identifier so that I can reference items by their SKU in scanning workflows and put-away lists.

#### Acceptance Criteria

1. THE System SHALL add a nullable `sku` column of type `VARCHAR(100)` to the `items` table via Alembic migration 048.
2. THE System SHALL add a non-unique index on `items.sku` to support efficient lookups by SKU.
3. WHEN an item is created or updated with a `sku` value, THE System SHALL store the `sku` value independently of `item_code`, leaving `item_code` unchanged.
4. THE Item model SHALL expose the `sku` field in its SQLAlchemy column definition and in the corresponding Pydantic schemas.

---

### Requirement 2: Item Packaging Units Table

**User Story:** As a warehouse manager, I want to define multiple packaging units per item (e.g., Each, Box, Pallet) with physical dimensions and a QR identifier so that workers can scan any packaging unit and the system can convert quantities to Eaches automatically.

#### Acceptance Criteria

1. THE System SHALL create an `item_packaging_units` table via Alembic migration 048 with the following columns: `id` (UUID PK), `organization_id` (UUID, not null), `item_id` (UUID FK → `items.id`, not null), `unit_name` (VARCHAR(100), not null), `qr_identifier` (VARCHAR(255), unique within the table), `conversion_factor` (NUMERIC(15,6), not null, must be > 0), `length_mm` (NUMERIC(10,2), nullable), `width_mm` (NUMERIC(10,2), nullable), `height_mm` (NUMERIC(10,2), nullable), `weight_grams` (NUMERIC(10,2), nullable), `is_base_unit` (BOOLEAN, default false), `is_active` (BOOLEAN, default true), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ).
2. THE System SHALL enforce a unique constraint on `(item_id, unit_name)` so that no item has two packaging units with the same name.
3. THE System SHALL create an index on `item_packaging_units.item_id` and a unique index on `item_packaging_units.qr_identifier`.
4. THE ItemPackagingUnit model SHALL define a relationship back to `Item` and expose all columns via SQLAlchemy.
5. IF a `conversion_factor` value of zero or less is provided, THEN THE System SHALL reject the record with a validation error before persisting it.
6. THE System SHALL expose CRUD API endpoints for `item_packaging_units` under `/api/v1/items/{item_id}/packaging-units` with `GET` (list), `POST` (create), `PATCH /{id}` (update), and `DELETE /{id}` (soft-delete by setting `is_active = false`).

---

### Requirement 3: Packaging Unit Metadata on Bin Stock Levels

**User Story:** As a warehouse analyst, I want each bin stock level row to optionally record which packaging unit was last used to receive that stock so that I have traceability from bin stock back to the original packaging unit.

#### Acceptance Criteria

1. THE System SHALL add a nullable `packaging_unit_id` column of type UUID to the `bin_stock_levels` table via Alembic migration 048, with a foreign key referencing `item_packaging_units.id`.
2. THE System SHALL NOT include `packaging_unit_id` in the unique constraint `uq_bin_item_batch`; the existing unique constraint on `(bin_location_id, item_id, batch_number)` SHALL remain unchanged.
3. WHEN a put-away operation updates a `bin_stock_levels` row, THE System SHALL optionally record the `packaging_unit_id` of the packaging unit used during receiving on that row as metadata.
4. THE BinStockLevel model SHALL expose the `packaging_unit_id` field and a relationship to `ItemPackagingUnit`.

---

### Requirement 4: Volumetric Capacity Fields on Warehouse Locations

**User Story:** As a warehouse manager, I want to define maximum volume and weight limits for each bin location so that the system can automatically assign bins that have sufficient physical capacity for incoming stock.

#### Acceptance Criteria

1. THE System SHALL add a nullable `max_volume_cc` column of type `NUMERIC(15,2)` to the `warehouse_locations` table via Alembic migration 048, representing the bin's maximum storage volume in cubic centimetres.
2. THE System SHALL add a nullable `max_weight_grams` column of type `NUMERIC(15,2)` to the `warehouse_locations` table via Alembic migration 048, representing the bin's maximum storage weight in grams.
3. THE WarehouseLocation model SHALL expose `max_volume_cc` and `max_weight_grams` fields.
4. WHEN `max_volume_cc` or `max_weight_grams` is null on a bin, THE Volumetric Auto-Assignment Service SHALL treat that dimension as unconstrained (no capacity check for that dimension).

---

### Requirement 5: Packaging Unit Traceability on Scan Session Items

**User Story:** As a warehouse supervisor, I want each QR scan during an inbound session to record the packaging unit that was scanned and the raw quantity in that packaging unit so that I have full traceability from scan to final Eaches quantity.

#### Acceptance Criteria

1. THE System SHALL add a nullable `packaging_unit_id` column of type UUID to the `scan_session_items` table via Alembic migration 048, with a foreign key referencing `item_packaging_units.id`.
2. THE System SHALL rename the existing `quantity` column on `scan_session_items` to `raw_quantity` via Alembic migration 048 to make explicit that this value is in the packaging unit's own units, not Eaches.
3. WHEN a QR scan is recorded in an inbound session, THE Inbound Service SHALL store the scanned quantity in `scan_session_items.raw_quantity` and the resolved packaging unit in `scan_session_items.packaging_unit_id` without performing any conversion.
4. THE ScanSessionItem model SHALL expose `raw_quantity` and `packaging_unit_id` fields.
5. WHEN the QR payload contains a `packaging_unit_qr_id` field, THE Inbound Service SHALL resolve it to an `item_packaging_units.id` and store it in `scan_session_items.packaging_unit_id`.
6. IF the QR payload does not contain a `packaging_unit_qr_id`, THEN THE Inbound Service SHALL leave `scan_session_items.packaging_unit_id` as null and store the scanned quantity directly in `raw_quantity`.

---

### Requirement 6: Quantity Conversion at Receiving Slip Approval

**User Story:** As a warehouse manager, I want the system to automatically convert scanned packaging unit quantities to Eaches when I approve a receiving slip so that all downstream stock movements use the canonical base unit.

#### Acceptance Criteria

1. WHEN a receiving slip is approved, THE Receiving Slip Service SHALL iterate over all associated `scan_session_items` rows for the session.
2. WHEN a `scan_session_items` row has a non-null `packaging_unit_id`, THE Receiving Slip Service SHALL multiply `raw_quantity` by the `conversion_factor` of the referenced `item_packaging_units` row to compute the Eaches quantity for the receiving slip line item.
3. WHEN a `scan_session_items` row has a null `packaging_unit_id`, THE Receiving Slip Service SHALL use `raw_quantity` directly as the Eaches quantity for the receiving slip line item.
4. THE Receiving Slip Service SHALL store the computed Eaches quantity in the `receiving_slip_items.quantity` column.
5. IF a referenced `item_packaging_units` row is not found or is inactive at approval time, THEN THE Receiving Slip Service SHALL return a 422 error with a message identifying the missing or inactive packaging unit.

---

### Requirement 7: Volumetric Auto-Assignment Service

**User Story:** As a warehouse manager, I want the system to automatically find and assign suitable bin locations to put-away list items based on available volume and weight capacity so that workers receive a ready-to-execute put-away list without manual bin selection.

#### Acceptance Criteria

1. WHEN a put-away list is generated from an approved receiving slip, THE Volumetric Auto-Assignment Service SHALL execute within the same database transaction as put-away list creation.
2. THE Volumetric Auto-Assignment Service SHALL query `warehouse_locations` of type `bin` that are active (`is_active = true`) and belong to the same warehouse as the receiving slip.
3. FOR each put-away list item, THE Volumetric Auto-Assignment Service SHALL calculate the required volume as `quantity_eaches × packaging_unit.length_mm × packaging_unit.width_mm × packaging_unit.height_mm / 1000` (converting mm³ to cc) when all three dimension fields are non-null on the packaging unit.
4. FOR each put-away list item, THE Volumetric Auto-Assignment Service SHALL calculate the required weight as `quantity_eaches × packaging_unit.weight_grams` when `weight_grams` is non-null on the packaging unit.
5. THE Volumetric Auto-Assignment Service SHALL select a bin where `(max_volume_cc - currently_occupied_volume_cc) >= required_volume_cc` AND `(max_weight_grams - currently_occupied_weight_grams) >= required_weight_grams`, applying only the constraints for which both the bin limit and the packaging unit dimension are non-null.
6. WHEN a suitable bin is found, THE Volumetric Auto-Assignment Service SHALL set `put_away_list_items.bin_location_id` to that bin's id within the same transaction.
7. WHEN no suitable bin is found for a put-away list item, THE Volumetric Auto-Assignment Service SHALL leave `put_away_list_items.bin_location_id` as null and SHALL NOT abort the transaction; the put-away list SHALL still be created with the unassigned item.
8. THE Volumetric Auto-Assignment Service SHALL prefer bins that already contain the same `item_id` and `batch_number` combination (consolidation preference) before selecting empty or mixed bins.
9. THE Volumetric Auto-Assignment Service SHALL use `SELECT ... FOR UPDATE SKIP LOCKED` on candidate bin rows to prevent concurrent assignment conflicts.

---

### Requirement 8: Alembic Migration 048

**User Story:** As a backend engineer, I want all schema changes for this feature delivered in a single Alembic migration (048) so that the database can be upgraded and rolled back atomically.

#### Acceptance Criteria

1. THE System SHALL create Alembic migration `048_add_multi_uom_packaging_units` with `down_revision = "047_extend_pick_lists_and_create_put_away_lists"`.
2. THE migration `upgrade()` function SHALL apply all schema changes described in Requirements 1–4 and 5.1–5.2 in the correct dependency order: `item_packaging_units` table first, then FK columns on `items`, `bin_stock_levels`, `scan_session_items`, and `warehouse_locations`.
3. THE migration `downgrade()` function SHALL reverse all changes in the correct reverse order, dropping FK columns before dropping the `item_packaging_units` table.
4. THE migration SHALL include `op.create_index` and `op.drop_index` calls for all indexes introduced in Requirements 1–5.
5. IF the migration is run against a database that already has any of the new columns, THEN the migration SHALL fail with a clear Alembic error rather than silently succeeding.
