# Implementation Plan: Feature Flag System

## Overview

Implement a GLOBAL-scoped feature flag system for Horizon Sync ERP. Backend follows the existing repository → service → endpoint pattern in core-service (FastAPI/SQLAlchemy). Frontend adds a "Feature Controls" page to the admin portal (React/TypeScript). Includes a reference integration in the invoice flow and property-based tests via Hypothesis.

## Tasks

- [x] 1. Create Alembic migration and SQLAlchemy model
  - [x] 1.1 Create Alembic migration `040_add_feature_flags_table.py`
    - Create `feature_flags` table with columns: id (UUID PK), name (VARCHAR 255), description (TEXT nullable), enabled (BOOLEAN default false), scope (VARCHAR 20 default 'GLOBAL'), tenant_id (UUID nullable), user_id (UUID nullable), rollout_percentage (INTEGER with CHECK 0–100 nullable), created_at (TIMESTAMPTZ), updated_at (TIMESTAMPTZ)
    - Add unique constraint on (name, scope, tenant_id, user_id)
    - Add indexes on `name` and `scope`
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 Create SQLAlchemy model `app/models/feature_flag.py`
    - Define `FeatureFlag` model class extending `Base` with `__tablename__ = "feature_flags"`
    - Follow existing model patterns (see `app/models/invoice.py` for reference)
    - Use `app.models.types.UUID` and `app.database.Base`
    - _Requirements: 1.1, 1.3_

- [x] 2. Create Pydantic schemas and repository
  - [x] 2.1 Create Pydantic schemas `app/schemas/feature_flag.py`
    - `FeatureFlagCreate`: name (required, min 1, max 255, pattern `^[a-z0-9_]+$`), description (optional, max 1000), enabled (default false)
    - `FeatureFlagUpdate`: all fields optional with same validation
    - `FeatureFlagResponse`: full flag with all DB fields
    - `FeatureFlagListResponse`: wrapper with `flags: list[FeatureFlagResponse]`
    - `FeatureFlagEvaluation`: feature_name + enabled boolean
    - _Requirements: 1.1, 2.1, 2.3, 4.1_

  - [x] 2.2 Create repository `app/repositories/feature_flag_repository.py`
    - Implement `create`, `get_by_id`, `get_by_name` (with scope param), `list_all`, `update`, `delete`, `name_exists` methods
    - Follow existing ORM repository patterns (see `app/repositories/invoice_repository.py`)
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.6, 2.7_

- [x] 3. Create service layer with evaluation logic and helper
  - [x] 3.1 Create service `app/services/feature_flag_service.py`
    - Implement `create_flag`, `get_flag`, `list_flags`, `update_flag`, `delete_flag`, `evaluate` methods
    - `create_flag`: set scope=GLOBAL, tenant_id=None, user_id=None; raise 409 on duplicate name
    - `evaluate`: lookup GLOBAL flag by name, return enabled value; return false if not found
    - Add INFO-level logging on evaluation, ERROR-level on failures
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 8.1, 8.2_

  - [x] 3.2 Create standalone `is_feature_enabled(feature_name, db)` helper function
    - Module-level function in `feature_flag_service.py`
    - Wraps all exceptions in try/except, returns `False` as safe default
    - Logs errors at ERROR level
    - _Requirements: 5.1, 5.2, 5.3_

- [x] 4. Create API endpoints and register router
  - [x] 4.1 Create endpoint file `app/api/v1/endpoints/admin/feature_flags.py`
    - POST `/` → create flag (201)
    - GET `/` → list all flags (200)
    - GET `/{flag_id}` → get by ID (200)
    - PATCH `/{flag_id}` → update flag (200)
    - DELETE `/{flag_id}` → delete flag (204)
    - GET `/evaluate/{feature_name}` → evaluate flag (200)
    - All endpoints use `require_admin` dependency from `app.dependencies`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 4.1, 4.2_

  - [x] 4.2 Register feature flags router in `app/api/v1/endpoints/admin/__init__.py`
    - Import and include `feature_flags_router` with prefix `/feature-flags` and tag `"Admin - Feature Flags"`
    - _Requirements: 2.1_

- [x] 5. Checkpoint - Backend API complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create admin portal frontend
  - [x] 6.1 Create API service `apps/admin/src/app/services/feature-flag.service.ts`
    - Follow existing service pattern (see `admin-audit-log.service.ts`)
    - Methods: `listFlags()`, `createFlag(data)`, `updateFlag(id, data)`, `deleteFlag(id)`, `evaluateFlag(name)`
    - Use `useUserStore` for auth token, `environment.apiCoreUrl` for base URL
    - _Requirements: 7.1, 7.5, 7.6_

  - [x] 6.2 Create `FeatureControlsPage` at `apps/admin/src/app/pages/FeatureControlsPage.tsx`
    - Display table of all flags with columns: name, description, enabled (toggle switch), created_at
    - Toggle switch calls PATCH endpoint and reflects new status
    - Create form with name, description, enabled fields
    - Show toast on API errors
    - Follow existing page patterns (see `UsersPage.tsx`, `AuditLogsPage.tsx`)
    - _Requirements: 7.1, 7.4, 7.5, 7.6, 7.7_

  - [x] 6.3 Add route and sidebar navigation
    - Add `/feature-controls` route in `AppRoutes.tsx` pointing to `FeatureControlsPage`
    - Add "Feature Controls" nav item in `Sidebar.tsx` `bottomNavItems` array after "System Permissions" and before "Settings", with `requiresMaster: true` and `Zap` or `ToggleLeft` icon
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 7. Checkpoint - Frontend complete
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Invoice flow integration
  - [x] 8.1 Integrate `is_feature_enabled` in `InvoiceService.update()`
    - Import `is_feature_enabled` from `app.services.feature_flag_service`
    - Wrap the `requires_journal_entry` block: only execute journal posting if `is_feature_enabled("invoice_auto_journal_posting", self.db)` returns True
    - Log skip message at INFO level when flag is disabled
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 9. Backend tests
  - [ ]* 9.1 Write unit tests at `horizon-sync-erp-be/core-service/tests/test_feature_flag_service.py`
    - Test create flag returns correct data with GLOBAL scope defaults
    - Test duplicate name returns 409
    - Test partial update preserves unchanged fields
    - Test delete removes flag
    - Test evaluate returns correct enabled value for existing flag
    - Test evaluate returns false for missing flag
    - Test evaluate returns false on DB error (mock exception)
    - Test invoice integration: mock `is_feature_enabled`, verify journal posting is gated
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ]* 9.2 Write property test: Create–Read Round Trip
    - **Property 1: Create–Read Round Trip**
    - **Validates: Requirements 1.3, 2.1, 2.7**
    - Use Hypothesis with `st.from_regex(r"[a-z][a-z0-9_]{0,49}", fullmatch=True)` for names
    - Verify created flag matches input and has scope=GLOBAL, tenant_id=None, user_id=None

  - [ ]* 9.3 Write property test: Duplicate Name Rejection
    - **Property 2: Duplicate Name Rejection**
    - **Validates: Requirements 1.2, 2.2**
    - Create flag, attempt duplicate, verify 409 and flag count unchanged

  - [ ]* 9.4 Write property test: Update Preserves Changes
    - **Property 3: Update Preserves Changes**
    - **Validates: Requirements 2.3**
    - Generate random partial updates, verify updated fields change and omitted fields retain original values

  - [ ]* 9.5 Write property test: Delete Removes Flag
    - **Property 4: Delete Removes Flag**
    - **Validates: Requirements 2.4**
    - Create and delete flag, verify not found on get and absent from list

  - [ ]* 9.6 Write property test: List Completeness
    - **Property 5: List Completeness**
    - **Validates: Requirements 2.6**
    - Create N flags, verify list returns exactly N and all names present

  - [ ]* 9.7 Write property test: Evaluation Returns Enabled Value
    - **Property 6: Evaluation Returns Enabled Value**
    - **Validates: Requirements 3.1, 3.3, 4.1, 5.1, 5.2, 9.1**
    - Create flag with random enabled value, evaluate by name, verify result matches

  - [ ]* 9.8 Write property test: Missing Flag Evaluates to Disabled
    - **Property 7: Missing Flag Evaluates to Disabled**
    - **Validates: Requirements 3.2, 4.2, 9.2**
    - Generate random non-existent names, verify evaluation returns false

- [x] 10. Final checkpoint - All tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- The migration number is `040` (next after existing `039_add_audit_logs_table.py`)
- Backend uses Python (FastAPI/SQLAlchemy), frontend uses TypeScript (React)
- Property tests use Hypothesis library with minimum 100 iterations each
- All admin endpoints are gated by `require_admin` (system_admin user_type)
