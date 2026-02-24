# Implementation Plan: UOM & Currency Master

## Overview

Implement four master-data entities (UOM, UOM Conversion, Currency Master, Exchange Rate enhancement) following the existing layered architecture: models → schemas → repositories → services → endpoints → router registration. Each layer builds on the previous. Tests are included as sub-tasks close to the implementation they validate.

## Tasks

- [ ] 1. Create SQLAlchemy models
  - [~] 1.1 Create UOM model in `core-service/app/models/uom.py`
    - Define `UOM` class with columns: `id`, `organization_id`, `name` (String 50), `abbreviation` (String 10), `description` (Text), audit fields (`created_by`, `updated_by`, `created_at`, `updated_at`, `deleted_at`)
    - Add partial unique constraints `uq_uom_org_name` and `uq_uom_org_abbr` with `WHERE deleted_at IS NULL`
    - Add index on `organization_id`
    - _Requirements: 1.8_

  - [~] 1.2 Create UOM Conversion model in `core-service/app/models/uom_conversion.py`
    - Define `UOMConversion` class with columns: `id`, `organization_id`, `item_id` (FK to `items.id`), `from_uom` (String 50), `to_uom` (String 50), `conversion_factor` (Numeric 19,6), audit fields including `deleted_at`
    - Add partial unique constraint `uq_uom_conv_org_item_pair` on (`organization_id`, `item_id`, `from_uom`, `to_uom`) with `WHERE deleted_at IS NULL`
    - Add check constraint `ck_uom_conv_positive_factor` ensuring `conversion_factor > 0`
    - Add index on `item_id`
    - _Requirements: 2.9, 2.10_

  - [~] 1.3 Create Currency Master model in `core-service/app/models/currency_master.py`
    - Define `CurrencyMaster` class with columns: `id`, `organization_id`, `code` (String 3), `name` (String 100), `symbol` (String 5, nullable), `is_base_currency` (Boolean, default false), audit fields including `deleted_at`
    - Add partial unique constraint `uq_currency_org_code` on (`organization_id`, `code`) with `WHERE deleted_at IS NULL`
    - Add index on `organization_id`
    - _Requirements: 3.10_

  - [~] 1.4 Enhance existing Exchange Rate model in `core-service/app/models/exchange_rate.py`
    - Add `organization_id` column (UUID, nullable for backward compat) with index
    - Add `captured_at` column (DateTime with timezone, nullable, defaults to `datetime.now(UTC)`)
    - Keep existing unique constraint and check constraint unchanged
    - _Requirements: 4.1_

  - [~] 1.5 Register new models in `core-service/app/models/__init__.py`
    - Import `UOM`, `UOMConversion`, `CurrencyMaster` so Alembic discovers them
    - _Requirements: 1.8, 2.9, 3.10_

- [ ] 2. Create Pydantic schemas
  - [~] 2.1 Create UOM schemas in `core-service/app/schemas/uom.py`
    - Define `UOMBase`, `UOMCreate`, `UOMUpdate`, `UOMResponse`, `UOMListResponse`
    - `name`: min 1, max 50 chars; `abbreviation`: min 1, max 10 chars; `description`: optional
    - `UOMListResponse` includes `uoms` list and `pagination` metadata
    - _Requirements: 1.1, 1.4_

  - [~] 2.2 Create UOM Conversion schemas in `core-service/app/schemas/uom_conversion.py`
    - Define `UOMConversionBase`, `UOMConversionCreate`, `UOMConversionUpdate`, `UOMConversionResponse`, `UOMConversionListResponse`
    - `conversion_factor`: Decimal, `gt=0`; `from_uom`/`to_uom`: min 1, max 50 chars
    - _Requirements: 2.1, 2.4, 2.7_

  - [~] 2.3 Create Currency Master schemas in `core-service/app/schemas/currency_master.py`
    - Define `CurrencyMasterBase`, `CurrencyMasterCreate`, `CurrencyMasterUpdate`, `CurrencyMasterResponse`, `CurrencyMasterListResponse`
    - `code`: pattern `^[A-Z]{3}$`, min/max 3 chars; `name`: max 100 chars; `symbol`: max 5 chars
    - _Requirements: 3.1, 3.4, 3.8_

  - [~] 2.4 Create Exchange Rate schemas in `core-service/app/schemas/exchange_rate.py`
    - Define `ExchangeRateCreate`, `ExchangeRateUpdate`, `ExchangeRateResponse`, `ExchangeRateListResponse`
    - `from_currency`/`to_currency`: pattern `^[A-Z]{3}$`; `rate`: Decimal, `gt=0`; `effective_date`: optional (defaults to today)
    - _Requirements: 4.2, 4.5, 4.8_

- [ ] 3. Create repository layer
  - [~] 3.1 Create UOM repository in `core-service/app/repositories/uom_repository.py`
    - Implement `create`, `get_by_id` (org-scoped, excludes soft-deleted), `list` (paginated, org-scoped, excludes soft-deleted, optional search), `update`, `soft_delete`
    - Implement `get_by_name` and `get_by_abbreviation` for uniqueness checks
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [~] 3.2 Create UOM Conversion repository in `core-service/app/repositories/uom_conversion_repository.py`
    - Implement `create`, `get_by_id` (org-scoped, excludes soft-deleted), `list` (paginated, filterable by `item_id`), `update`, `soft_delete`
    - Implement `get_by_item_and_pair(item_id, from_uom, to_uom, organization_id)` for uniqueness checks and `convert_quantity` lookups
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [~] 3.3 Create Currency Master repository in `core-service/app/repositories/currency_master_repository.py`
    - Implement `create`, `get_by_id` (org-scoped, excludes soft-deleted), `list` (paginated, org-scoped, optional search), `update`, `soft_delete`
    - Implement `get_by_code(code, organization_id)` for uniqueness checks
    - Implement `clear_base_currency(organization_id)` to set `is_base_currency = false` on all currencies in org
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [~] 3.4 Create Exchange Rate repository in `core-service/app/repositories/exchange_rate_repository.py`
    - Implement `create`, `get_by_id` (org-scoped), `list` (paginated, filterable by `from_currency`, `to_currency`, `start_date`, `end_date`), `update`, `hard_delete`
    - Implement `get_by_currency_pair_and_date(org_id, from_currency, to_currency, effective_date)` for upsert logic
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 4. Create service layer
  - [~] 4.1 Create UOM service in `core-service/app/services/uom_service.py`
    - Implement `create_uom`: check duplicate name and abbreviation within org (HTTP 409), then delegate to repository
    - Implement `get_uom`, `list_uoms`, `update_uom` (check duplicates on name/abbreviation change), `delete_uom`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [~] 4.2 Create UOM Conversion service in `core-service/app/services/uom_conversion_service.py`
    - Implement `create_conversion`: validate item exists in org (HTTP 404), check duplicate (item_id, from_uom, to_uom) within org (HTTP 409)
    - Implement `get_conversion`, `list_conversions`, `update_conversion`, `delete_conversion`
    - Implement `convert_quantity(item_id, from_uom, to_uom, quantity, organization_id)`: identity check → forward lookup → reverse lookup → raise ValidationError
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.8, 5.1, 5.2, 5.3, 5.4_

  - [ ]\* 4.3 Write property tests for convert_quantity
    - **Property 20: convert_quantity forward computation** — for any item with conversion (A→B, factor F) and positive Q, result = Q × F
    - **Property 21: convert_quantity reverse-lookup round trip** — converting Q from A→B then B→A returns Q (within decimal precision)
    - **Property 22: convert_quantity identity for same UOM** — convert_quantity(item, U, U, Q) returns Q without DB lookup
    - **Property 23: convert_quantity raises on missing conversion** — raises ValidationError when no conversion exists
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [~] 4.4 Create Currency Master service in `core-service/app/services/currency_master_service.py`
    - Implement `create_currency`: check duplicate code within org (HTTP 409), enforce base currency toggle (clear others if `is_base_currency=true`)
    - Implement `get_currency`, `list_currencies`, `update_currency` (enforce base currency toggle on update), `delete_currency`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.9_

  - [~] 4.5 Create Exchange Rate service in `core-service/app/services/exchange_rate_service.py`
    - Implement `create_exchange_rate`: validate `from_currency != to_currency` (HTTP 422), implement upsert logic (update existing if same org/pair/date exists)
    - Implement `get_exchange_rate`, `list_exchange_rates`, `update_exchange_rate`, `delete_exchange_rate` (hard delete)
    - Default `effective_date` to today if not provided; always set `organization_id` and `captured_at`
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

- [ ] 5. Checkpoint - Ensure models, schemas, repositories, and services are complete
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Create API endpoint layer
  - [~] 6.1 Create UOM endpoints in `core-service/app/api/v1/endpoints/uoms.py`
    - `POST /uoms` → 201, `GET /uoms` → 200 (paginated, search query param), `GET /uoms/{id}` → 200, `PATCH /uoms/{id}` → 200, `DELETE /uoms/{id}` → 204
    - Use `get_current_active_user` for auth, `require_permission` for authorization
    - Inject `UOMService` via dependency
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [ ] 6.2 Create UOM Conversion endpoints in `core-service/app/api/v1/endpoints/uom_conversions.py`
    - `POST /uom-conversions` → 201, `GET /uom-conversions` → 200 (filterable by `item_id`), `GET /uom-conversions/{id}` → 200, `PATCH /uom-conversions/{id}` → 200, `DELETE /uom-conversions/{id}` → 204
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [ ] 6.3 Create Currency Master endpoints in `core-service/app/api/v1/endpoints/currencies.py`
    - `POST /currencies` → 201, `GET /currencies` → 200 (paginated, search), `GET /currencies/{id}` → 200, `PATCH /currencies/{id}` → 200, `DELETE /currencies/{id}` → 204
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [ ] 6.4 Create Exchange Rate endpoints in `core-service/app/api/v1/endpoints/exchange_rates.py`
    - `POST /exchange-rates` → 201, `GET /exchange-rates` → 200 (filterable by `from_currency`, `to_currency`, `start_date`, `end_date`), `GET /exchange-rates/{id}` → 200, `PUT /exchange-rates/{id}` → 200, `DELETE /exchange-rates/{id}` → 204
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6_

- [ ] 7. Register routers and verify backward compatibility
  - [ ] 7.1 Register new routers in `core-service/app/api/v1/router.py`
    - Import and include `uoms`, `uom_conversions`, `currencies`, `exchange_rates` routers with prefixes `/uoms`, `/uom-conversions`, `/currencies`, `/exchange-rates` and appropriate tags
    - Ensure existing `currency.router` at `/currency` prefix remains unchanged
    - _Requirements: 4.10_

  - [ ] 7.2 Verify existing `/api/v1/currency/*` endpoints still function
    - Confirm the existing currency router import and registration is untouched
    - Verify the enhanced ExchangeRate model (nullable `organization_id`) doesn't break existing queries
    - _Requirements: 4.10_

- [ ] 8. Checkpoint - Ensure all endpoints are wired and backward compatibility is intact
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Write unit and integration tests
  - [ ] 9.1 Write UOM service unit tests in `core-service/tests/test_uom_service.py`
    - Test create with valid data, duplicate name detection (409), duplicate abbreviation detection (409), get by ID, list with pagination, update, soft-delete, not-found (404), org isolation
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]\* 9.2 Write UOM property tests in `core-service/tests/test_uom_properties.py`
    - **Property 1: UOM create-then-read round trip**
    - **Property 2: UOM soft-delete excludes from list**
    - **Property 3: UOM update reflects changes**
    - **Property 4: UOM duplicate detection within organization**
    - **Property 5: Organization isolation on reads**
    - **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8**

  - [ ] 9.3 Write UOM Conversion service unit tests in `core-service/tests/test_uom_conversion_service.py`
    - Test create with valid data, duplicate triple detection (409), item not found (404), positive factor validation (422), get, list filtered by item_id, update, soft-delete, convert_quantity forward/reverse/identity/missing
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 5.1, 5.2, 5.3, 5.4_

  - [ ]\* 9.4 Write UOM Conversion property tests in `core-service/tests/test_uom_conversion_properties.py`
    - **Property 6: UOM Conversion create-then-read round trip**
    - **Property 7: UOM Conversion list filters by item_id**
    - **Property 8: UOM Conversion update reflects changes**
    - **Property 9: UOM Conversion duplicate detection respects soft-delete**
    - **Property 10: Positive value validation**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6, 2.7, 2.10**

  - [ ] 9.5 Write Currency Master service unit tests in `core-service/tests/test_currency_master_service.py`
    - Test create with valid data, duplicate code detection (409), code format validation (422), base currency toggle, get, list, update, soft-delete, not-found (404), org isolation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [ ]\* 9.6 Write Currency Master property tests in `core-service/tests/test_currency_properties.py`
    - **Property 11: Currency create-then-read round trip**
    - **Property 12: Currency soft-delete excludes from list**
    - **Property 13: Single base currency invariant**
    - **Property 14: Currency code format validation**
    - **Property 15: Currency duplicate code detection**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5, 3.6, 3.7, 3.8**

  - [ ] 9.7 Write Exchange Rate service unit tests in `core-service/tests/test_exchange_rate_service.py`
    - Test create with valid data, upsert idempotence, same-currency rejection (422), positive rate validation (422), get, list with filters, update, hard-delete, org-scoped queries
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9_

  - [ ]\* 9.8 Write Exchange Rate property tests in `core-service/tests/test_exchange_rate_properties.py`
    - **Property 16: Exchange Rate create-then-read round trip**
    - **Property 17: Exchange Rate upsert idempotence**
    - **Property 18: Exchange Rate same-currency rejection**
    - **Property 19: Exchange Rate hard delete**
    - **Validates: Requirements 4.2, 4.4, 4.6, 4.7, 4.8, 4.9**

  - [ ] 9.9 Write backward compatibility test in `core-service/tests/test_exchange_rate_backward_compat.py`
    - Verify existing `/api/v1/currency/exchange-rates` endpoints still work after model enhancement
    - Verify records without `organization_id` (null) are still queryable via legacy endpoints
    - _Requirements: 4.10_

- [ ] 10. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (Properties 1–23)
- Unit tests validate specific examples and edge cases
- The existing `/api/v1/currency/*` endpoints must remain untouched — backward compatibility is critical (Req 4.10)
- `organization_id` on ExchangeRate is nullable to preserve backward compatibility with existing data
