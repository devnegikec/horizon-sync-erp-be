# Implementation Plan: Audit Trail & Activity Log

## Overview

Implement automated, field-level change tracking via SQLAlchemy ORM event listeners. The system captures before/after snapshots of every data mutation (Create, Update, Delete) into an `audit_logs` table, exposes org-scoped and admin cross-org REST APIs, and provides a reusable React `AuditTimeline` component. Default mode is synchronous (same-transaction) with an optional async mode via a pluggable `AuditQueueBackend` interface.

## MVP Scope

Admin portal only: synchronous audit logging, admin cross-org API, admin portal UI page. No async writer, no org-scoped API, no shared AuditTimeline component, no property-based tests.

## Tasks

### ── MVP: Admin Portal Audit Trail (implement now) ──

- [x] 1. Create AuditLog model, enum, and Alembic migration [MVP]
  - [x] 1.1 Create `AuditAction` enum and `AuditLog` SQLAlchemy model in `horizon-sync-erp-be/core-service/app/models/audit_log.py` [MVP]
    - Define `AuditAction(str, enum.Enum)` with CREATE, UPDATE, DELETE values
    - Define `AuditLog(Base)` with columns: `id` (UUID PK), `user_id`, `organization_id`, `action` (String(10)), `table_name` (String(100)), `record_id` (UUID), `old_values` (JSONB), `new_values` (JSONB), `changed_fields` (JSONB), `ip_address` (String(45)), `user_agent` (Text), `created_at` (DateTime with timezone)
    - Use custom `UUID` and `JSONB` types from `app/models/types.py`
    - Add composite index on `(table_name, record_id)`, and individual indexes on `user_id`, `organization_id`, `action`, `created_at`
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 1.2 Register `AuditLog` in `horizon-sync-erp-be/core-service/app/models/__init__.py` [MVP]
    - Import `AuditLog` and the new `AuditAction` (as `AuditLogAction` alias to avoid conflict with existing `AuditAction` from `account_audit_log`)
    - Add to `__all__` list
    - _Requirements: 1.1_

  - [x] 1.3 Create Alembic migration `039_add_audit_logs_table.py` in `horizon-sync-erp-be/core-service/alembic/versions/` [MVP]
    - Create `audit_logs` table with all columns and indexes
    - Set `down_revision` to the current head (`038_add_brands_enhance_qr_models_credit_balance`)
    - _Requirements: 1.1, 1.3_

- [x] 2. Implement Audit Context and Middleware [MVP]
  - [x] 2.1 Create `AuditContext` dataclass and `ContextVar` in `horizon-sync-erp-be/core-service/app/core/audit_context.py` [MVP]
    - Define `AuditContext` dataclass with `user_id`, `organization_id`, `ip_address`, `user_agent` (all optional)
    - Create `_audit_context_var: ContextVar[AuditContext]` with default empty `AuditContext()`
    - Implement `get_audit_context()` and `set_audit_context()` functions
    - _Requirements: 7.1, 7.3_

  - [x] 2.2 Create `AuditContextMiddleware` in `horizon-sync-erp-be/core-service/app/middleware/audit_middleware.py` [MVP]
    - Extend `BaseHTTPMiddleware`
    - Extract `user_id` and `organization_id` from JWT token (decode without full validation, best-effort)
    - Extract `ip_address` from `X-Forwarded-For` header or `request.client.host`
    - Extract `user_agent` from request headers
    - Set context via `set_audit_context()`, reset in `finally` block
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 3. Implement Audit Listener (SQLAlchemy event hooks) [MVP]
  - [x] 3.1 Create `horizon-sync-erp-be/core-service/app/core/audit_listener.py` [MVP]
    - Define `GLOBAL_EXCLUDE_FIELDS` set: `{"password", "password_hash", "api_key", "secret_key", "token", "refresh_token"}`
    - Implement `_get_excluded_fields(model_class) -> set[str]` returning union of global + model's `__audit_exclude__`
    - Implement `_serialize_value(value)` handling UUID→str, datetime→ISO, Decimal→float, Enum→.value, None→None, fallback to `str()` with `"[unserializable]"` on error
    - Implement `_after_insert`, `_after_update`, `_after_delete` event handlers
    - For `_after_update`: use `sqlalchemy.orm.attributes.get_history()` to compute field diffs, populate `old_values`, `new_values`, `changed_fields`
    - For `_after_insert`: set `old_values=None`, `new_values` = all non-excluded column values
    - For `_after_delete`: set `old_values` = all non-excluded column values, `new_values=None`
    - Retrieve user context from `get_audit_context()`
    - Write audit entry synchronously (same transaction) — MVP uses sync only
    - Wrap all listener logic in try/except to never propagate exceptions to the caller
    - Implement `register_audit_listeners()` that iterates `Base.registry.mappers` and attaches listeners to models with `__audited__ = True`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4_

- [x] 4. Add audit configuration settings [MVP]
  - [x] 4.2 Add audit configuration settings to `horizon-sync-erp-be/core-service/app/config.py` [MVP]
    - Add `audit_async_enabled: bool = False`
    - Add `audit_flush_interval: float = 1.0`
    - Add `audit_batch_size: int = 50`
    - _Requirements: 4.3, 4.5_

- [x] 5. Checkpoint - Ensure core audit infrastructure works [MVP]
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create Pydantic schemas for Audit Log API [MVP]
  - [x] 6.1 Create `horizon-sync-erp-be/core-service/app/schemas/audit_log.py` [MVP]
    - Define `AuditLogListItem` with fields: `id`, `user_id`, `organization_id`, `action`, `table_name`, `record_id`, `old_values`, `new_values`, `changed_fields`, `ip_address`, `created_at`, `user_email` (optional)
    - Define `ChangeDiffEntry` with `field`, `old_value`, `new_value`
    - Define `AuditLogDetail(AuditLogListItem)` with computed `change_diff` via `@model_validator`
    - Define `AuditLogListResponse` with `audit_logs: list[AuditLogListItem]` and `pagination: PaginationMeta`
    - Define `AuditLogHistoryResponse` with `record_id`, `table_name`, `history: list[AuditLogDetail]`, `pagination: PaginationMeta`
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. Implement Repository and Service layers [MVP]
  - [x] 7.1 Create `horizon-sync-erp-be/core-service/app/repositories/audit_log_repository.py` [MVP]
    - Implement `AuditLogRepository` with `list_audit_logs(filters, page, page_size)` building dynamic WHERE clause
    - Support filters: `table_name`, `record_id`, `user_id`, `action`, `date_from`, `date_to`, `changed_field`, `organization_id`
    - For `changed_field` filter, query JSONB `changed_fields` column using `@>` operator
    - Join to `users` table for `user_email` (LEFT JOIN, no FK constraint)
    - Implement `get_record_history(table_name, record_id, org_id, page, page_size)` ordered by `created_at DESC`
    - Return `(rows, total_count)` tuple following existing repository pattern
    - _Requirements: 5.1, 5.2, 5.3, 5.5, 5B.1, 5B.4_

  - [x] 7.2 Create `horizon-sync-erp-be/core-service/app/services/audit_log_service.py` [MVP]
    - Implement `AuditLogService` with `list_audit_logs(...)` and `get_record_history(...)`
    - Delegate to `AuditLogRepository`, assemble `AuditLogListResponse` and `AuditLogHistoryResponse`
    - Compute `PaginationMeta` following existing pattern (page, page_size, total_items, total_pages, has_next, has_prev)
    - _Requirements: 5.1, 5.2, 5.6, 6.3, 6.4_

- [x] 8. Implement Admin API endpoint [MVP]
  - [x] 8.1 Add `AUDIT_READ` permission constant to `horizon-sync-erp-be/core-service/app/core/authorization.py` [MVP]
    - Add `AUDIT_READ = "audit.read"`
    - _Requirements: 5.4_

  - [x] 8.3 Create admin cross-org API at `horizon-sync-erp-be/core-service/app/api/v1/endpoints/admin/audit_logs.py` [MVP]
    - `GET /audit-logs` — cross-org paginated list with optional `organization_id` filter, requires `require_admin`
    - `GET /audit-logs/{record_id}/history` — cross-org record history, requires `require_admin`
    - _Requirements: 5B.1, 5B.2, 5B.3, 5B.4, 5B.5_

- [x] 9. Wire routes and register listeners in application startup [MVP]
  - [x] 9.2 Register admin audit log routes in `horizon-sync-erp-be/core-service/app/api/v1/endpoints/admin/__init__.py` [MVP]
    - Import `audit_logs` router from admin audit_logs module
    - Add `router.include_router(audit_logs_router, prefix="/audit-logs", tags=["Admin - Audit Logs"])`
    - _Requirements: 5B.1_

  - [x] 9.3 Register audit listeners and middleware in `horizon-sync-erp-be/core-service/app/main.py` lifespan [MVP]
    - Call `register_audit_listeners()` at startup
    - Add `AuditContextMiddleware` to the FastAPI app
    - _Requirements: 2.4, 7.3_

  - [x] 9.4 Add `__audited__ = True` to key existing models (e.g., `Invoice`, `Customer`, `Item`, `Warehouse`, `SalesOrder`) [MVP]
    - Mark a representative set of models for audit tracking
    - Add `__audit_exclude__` where needed (e.g., models with sensitive fields)
    - _Requirements: 2.5, 3.1_

- [x] 10. Checkpoint - Ensure backend audit trail is fully functional [MVP]
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Admin Portal Audit Logs UI [MVP]
  - [x] 11.1 Create audit log TypeScript types at `horizon-sync/apps/admin/src/app/types/audit.types.ts` [MVP]
    - Define `AuditLogEntry` interface matching `AuditLogListItem` schema (id, user_id, organization_id, action, table_name, record_id, old_values, new_values, changed_fields, ip_address, created_at, user_email)
    - Define `AuditLogListResponse` interface with `audit_logs` and `pagination`
    - Define `AuditLogFilters` interface for query params
    - _Requirements: 6.1, 6.3_

  - [x] 11.2 Create audit log API service at `horizon-sync/apps/admin/src/app/services/admin-audit-log.service.ts` [MVP]
    - Implement `getAuditLogs(filters)` calling `GET /api/v1/admin/audit-logs` with query params
    - Implement `getRecordHistory(recordId, tableName)` calling `GET /api/v1/admin/audit-logs/{recordId}/history`
    - Follow existing admin service patterns (e.g., `admin-invoice.service.ts`)
    - _Requirements: 5B.1, 5B.2_

  - [x] 11.3 Create `AuditLogsPage` at `horizon-sync/apps/admin/src/app/pages/AuditLogsPage.tsx` [MVP]
    - Paginated table of audit log entries with columns: timestamp, user email, action (Create/Update/Delete badge), table name, record ID, changed fields summary
    - Filter bar with: organization selector, table name dropdown, action type filter, date range picker
    - Expandable row detail showing old_values vs new_values diff for UPDATE actions
    - "Load More" or page-based pagination
    - Follow existing admin page patterns (e.g., `InvoicesPage.tsx`, `UsersPage.tsx`)
    - _Requirements: 5B.1, 5B.4, 8.2, 8.3_

  - [x] 11.4 Add Audit Logs route and sidebar navigation [MVP]
    - Add route `<Route path="/audit-logs" element={<AuditLogsPage />} />` in `horizon-sync/apps/admin/src/app/AppRoutes.tsx`
    - Add `{ title: 'Audit Logs', href: '/audit-logs', icon: FileText, requiresPermission: ['system_admin.master', '*.*'] }` to `mainNavItems` in `horizon-sync/apps/admin/src/app/components/Sidebar.tsx`
    - _Requirements: 5B.3_

- [x] 12. Final checkpoint - Ensure MVP is fully functional [MVP]
  - Ensure all tests pass, ask the user if questions arise.

### ── DEFERRED: Extended Version (implement later) ──

- [ ]* D1. Implement Audit Writer async backends [DEFERRED]
  - [ ]* D1.1 Create `horizon-sync-erp-be/core-service/app/core/audit_writer.py` [DEFERRED]
    - Define `AuditQueueBackend` ABC with `enqueue()`, `start()`, `stop()` abstract methods
    - Implement `SynchronousAuditWriter` with `write(db, entry)` that creates `AuditLog` and adds to session (no flush/commit)
    - Implement `InProcessQueueBackend(AuditQueueBackend)` with `asyncio.Queue`, configurable `flush_interval` and `batch_size`
    - Implement `_flush_loop()` that collects entries and bulk-inserts into DB
    - Handle queue-full (log warning, drop entry) and flush failure (retry up to 3 times, then drop with error log)
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6_

  - [ ]* D1.2 Wire async worker start/stop in `app/main.py` lifespan [DEFERRED]
    - If `settings.audit_async_enabled`, start `InProcessQueueBackend` worker at startup and stop at shutdown
    - _Requirements: 4.3, 4.4_

- [ ]* D2. Implement Org-Scoped Audit Log API [DEFERRED]
  - [ ]* D2.1 Create org-scoped API at `horizon-sync-erp-be/core-service/app/api/v1/endpoints/audit_logs.py` [DEFERRED]
    - `GET /audit-logs` — paginated list with filters, auto-filtered by `current_user.organization_id`, requires `audit.read` permission
    - `GET /audit-logs/{record_id}/history` — record change history, auto-filtered by org_id
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6_

  - [ ]* D2.2 Register org-scoped audit log routes in `horizon-sync-erp-be/core-service/app/api/v1/router.py` [DEFERRED]
    - Import `audit_logs` endpoint module
    - Add `api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["Audit Logs"])`
    - _Requirements: 5.1_

- [ ]* D3. Implement Frontend AuditTimeline shared component [DEFERRED]
  - [ ]* D3.1 Create `AuditTimeline` React component at `horizon-sync/libs/shared/ui/src/components/audit/AuditTimeline.tsx` [DEFERRED]
    - Accept `recordId`, `tableName`, and optional `apiBasePath` props
    - Render vertical timeline with action badges, expandable diff view, "Load More" pagination
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* D3.2 Write unit tests for AuditTimeline component [DEFERRED]
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [ ]* D4. Property-Based Tests (Hypothesis) [DEFERRED]
  - [ ]* D4.1 Property test: CREATE/DELETE action snapshots [DEFERRED] — _Properties 2, 3_
  - [ ]* D4.2 Property test: `_serialize_value` JSON-safe output [DEFERRED] — _Property 4_
  - [ ]* D4.3 Property test: Diff computation correctness [DEFERRED] — _Property 1_
  - [ ]* D4.4 Property test: Sensitive field exclusion [DEFERRED] — _Property 5_
  - [ ]* D4.5 Property test: Org-scoped query isolation [DEFERRED] — _Property 6_
  - [ ]* D4.6 Property test: Query filter correctness [DEFERRED] — _Property 7_
  - [ ]* D4.7 Property test: Record history ordering [DEFERRED] — _Property 8_
  - [ ]* D4.8 Property test: Change diff schema computation [DEFERRED] — _Property 9_

## Notes

- `[MVP]` = implement now (admin portal, synchronous mode, backend + frontend)
- `[DEFERRED]` = implement later (async writer, org-scoped API, shared timeline component, property tests)
- Tasks marked with `*` are optional/deferred
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- All backend files are under `horizon-sync-erp-be/core-service/`
- Frontend admin portal is at `horizon-sync/apps/admin/`
