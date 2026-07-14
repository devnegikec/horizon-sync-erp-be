# Requirements Document

## Introduction

This feature introduces four master-data entities to the core-service: UOM (Unit of Measure), UOM Conversion, Currency, and Exchange Rate. These tables provide the foundational reference data needed for multi-currency transactions and unit-of-measure conversions across the Procure-to-Pay and Order-to-Cash workflows. The implementation follows the existing repository → service → endpoint layered architecture with multi-tenancy, soft-delete, and UUID primary keys.

## Glossary

- **UOM_Master**: The master table that stores all valid units of measure (e.g., Kg, Nos, Box, Litre) for an organization.
- **UOM_Conversion**: A child table of Item that stores conversion factors between two UOMs for a specific item (e.g., 1 Box = 12 Nos for Item X).
- **Currency_Master**: The master table that stores all supported currencies for an organization, with an ISO 4217 code and a flag indicating the base currency.
- **Exchange_Rate**: The existing table that logs exchange rates between currency pairs, enhanced with organization-level scoping and a `captured_at` timestamp.
- **Conversion_Factor**: A positive decimal number used to convert a transaction quantity from one UOM to another. Formula: Base_Qty = Transaction_Qty × Conversion_Factor.
- **Base_Currency**: The single currency flagged as the organization's default for reporting and accounting.
- **API**: The FastAPI REST endpoints exposed under `/api/v1/`.
- **Repository**: The data-access class that encapsulates SQLAlchemy queries.
- **Service**: The business-logic class that orchestrates repository calls and enforces rules.
- **Organization**: The tenant boundary; all data is scoped by `organization_id`.

## Requirements

### Requirement 1: UOM Master CRUD

**User Story:** As a warehouse manager, I want to maintain a list of valid units of measure, so that items and transactions reference consistent UOM values.

#### Acceptance Criteria

1. THE API SHALL expose a `POST /api/v1/uoms` endpoint that creates a UOM record with fields: `name` (unique per organization, max 50 chars), `abbreviation` (unique per organization, max 10 chars), and optional `description`.
2. THE API SHALL expose a `GET /api/v1/uoms` endpoint that returns a paginated list of UOM records filtered by `organization_id`, excluding soft-deleted records.
3. THE API SHALL expose a `GET /api/v1/uoms/{id}` endpoint that returns a single UOM record by UUID, scoped to the requesting user's organization.
4. THE API SHALL expose a `PATCH /api/v1/uoms/{id}` endpoint that updates mutable fields (`name`, `abbreviation`, `description`) of an existing UOM record.
5. THE API SHALL expose a `DELETE /api/v1/uoms/{id}` endpoint that performs a soft delete by setting `deleted_at` to the current UTC timestamp.
6. IF a UOM with the same `name` or `abbreviation` already exists within the organization, THEN THE API SHALL return HTTP 409 with a descriptive error message.
7. IF the requested UOM does not exist or belongs to a different organization, THEN THE API SHALL return HTTP 404.
8. THE UOM_Master model SHALL include columns: `id` (UUID PK), `organization_id` (UUID, not null), `name` (String 50, not null), `abbreviation` (String 10, not null), `description` (Text, nullable), `created_by`, `updated_by`, `created_at`, `updated_at`, `deleted_at`.

### Requirement 2: UOM Conversion CRUD

**User Story:** As a procurement officer, I want to define conversion factors between UOMs for each item, so that the system can convert transaction quantities to base quantities automatically.

#### Acceptance Criteria

1. THE API SHALL expose a `POST /api/v1/uom-conversions` endpoint that creates a UOM Conversion record with fields: `item_id` (UUID, required), `from_uom` (String, required), `to_uom` (String, required), and `conversion_factor` (Decimal, positive, required).
2. THE API SHALL expose a `GET /api/v1/uom-conversions` endpoint that returns a paginated list of UOM Conversion records, filterable by `item_id`, scoped to the requesting user's organization.
3. THE API SHALL expose a `GET /api/v1/uom-conversions/{id}` endpoint that returns a single UOM Conversion record by UUID.
4. THE API SHALL expose a `PATCH /api/v1/uom-conversions/{id}` endpoint that updates `from_uom`, `to_uom`, or `conversion_factor`.
5. THE API SHALL expose a `DELETE /api/v1/uom-conversions/{id}` endpoint that performs a soft delete.
6. IF a conversion with the same `item_id`, `from_uom`, and `to_uom` combination already exists within the organization, THEN THE API SHALL return HTTP 409.
7. IF `conversion_factor` is zero or negative, THEN THE API SHALL return HTTP 422 with a validation error.
8. IF the referenced `item_id` does not exist within the organization, THEN THE API SHALL return HTTP 404.
9. THE UOM_Conversion model SHALL include columns: `id` (UUID PK), `organization_id` (UUID, not null), `item_id` (UUID FK to items.id, not null), `from_uom` (String 50, not null), `to_uom` (String 50, not null), `conversion_factor` (Numeric 19,6, not null), `created_by`, `updated_by`, `created_at`, `updated_at`, `deleted_at`.
10. THE UOM_Conversion model SHALL enforce a unique constraint on (`organization_id`, `item_id`, `from_uom`, `to_uom`) excluding soft-deleted rows.

### Requirement 3: Currency Master CRUD

**User Story:** As a finance manager, I want to maintain a list of supported currencies with a designated base currency, so that the system can handle multi-currency transactions.

#### Acceptance Criteria

1. THE API SHALL expose a `POST /api/v1/currencies` endpoint that creates a Currency record with fields: `code` (ISO 4217, 3 uppercase letters, unique per organization), `name` (max 100 chars), `symbol` (max 5 chars, nullable), and `is_base_currency` (boolean, default false).
2. THE API SHALL expose a `GET /api/v1/currencies` endpoint that returns a paginated list of Currency records for the organization, excluding soft-deleted records.
3. THE API SHALL expose a `GET /api/v1/currencies/{id}` endpoint that returns a single Currency record by UUID.
4. THE API SHALL expose a `PATCH /api/v1/currencies/{id}` endpoint that updates mutable fields (`name`, `symbol`, `is_base_currency`).
5. THE API SHALL expose a `DELETE /api/v1/currencies/{id}` endpoint that performs a soft delete.
6. WHEN a Currency record is created or updated with `is_base_currency` set to true, THE Service SHALL set `is_base_currency` to false on all other Currency records within the same organization, ensuring only one base currency exists at a time.
7. IF a Currency with the same `code` already exists within the organization, THEN THE API SHALL return HTTP 409.
8. IF the `code` field does not match the pattern of exactly 3 uppercase letters, THEN THE API SHALL return HTTP 422.
9. IF the requested Currency does not exist or belongs to a different organization, THEN THE API SHALL return HTTP 404.
10. THE Currency_Master model SHALL include columns: `id` (UUID PK), `organization_id` (UUID, not null), `code` (String 3, not null), `name` (String 100, not null), `symbol` (String 5, nullable), `is_base_currency` (Boolean, default false), `created_by`, `updated_by`, `created_at`, `updated_at`, `deleted_at`.

### Requirement 4: Exchange Rate Enhancement

**User Story:** As a finance manager, I want exchange rates to be scoped per organization and include a `captured_at` timestamp, so that rate history is auditable and tenant-isolated.

#### Acceptance Criteria

1. THE Exchange_Rate model SHALL be enhanced to include `organization_id` (UUID, not null) and `captured_at` (DateTime with timezone, defaults to current UTC time).
2. THE API SHALL expose a `POST /api/v1/exchange-rates` endpoint that creates an Exchange Rate record with fields: `from_currency` (String 3, required), `to_currency` (String 3, required), `rate` (Decimal positive, required), and optional `effective_date` (Date, defaults to today).
3. THE API SHALL expose a `GET /api/v1/exchange-rates` endpoint that returns a paginated list of Exchange Rate records for the organization, filterable by `from_currency`, `to_currency`, `start_date`, and `end_date`.
4. THE API SHALL expose a `GET /api/v1/exchange-rates/{id}` endpoint that returns a single Exchange Rate record by UUID.
5. THE API SHALL expose a `PUT /api/v1/exchange-rates/{id}` endpoint that updates `rate` and `effective_date`.
6. THE API SHALL expose a `DELETE /api/v1/exchange-rates/{id}` endpoint that hard-deletes the record.
7. IF an Exchange Rate with the same `organization_id`, `from_currency`, `to_currency`, and `effective_date` already exists, THEN THE API SHALL update the existing record instead of creating a duplicate.
8. IF `rate` is zero or negative, THEN THE API SHALL return HTTP 422.
9. IF `from_currency` equals `to_currency`, THEN THE API SHALL return HTTP 422 with a message indicating same-currency rates are not permitted.
10. THE existing `/api/v1/currency/exchange-rates` endpoints SHALL continue to function, with the new `/api/v1/exchange-rates` endpoints providing the organization-scoped alternative.

### Requirement 5: Conversion Utility

**User Story:** As a developer, I want a service-level utility to convert a quantity from one UOM to another for a given item, so that business logic across modules can perform UOM conversions without duplicating code.

#### Acceptance Criteria

1. THE Service SHALL provide a `convert_quantity(item_id, from_uom, to_uom, quantity, organization_id)` method that returns the converted quantity using the formula: `result = quantity × conversion_factor`.
2. IF no conversion record exists for the given `item_id`, `from_uom`, and `to_uom`, THEN THE Service SHALL attempt the reverse lookup (`to_uom` → `from_uom`) and compute `result = quantity / reverse_factor`.
3. IF neither forward nor reverse conversion exists, THEN THE Service SHALL raise a `ValidationError` with a descriptive message.
4. IF `from_uom` equals `to_uom`, THEN THE Service SHALL return the original quantity without a database lookup.
