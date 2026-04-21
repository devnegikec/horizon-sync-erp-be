# Requirements Document

## Introduction

This feature adds automated, field-level change tracking to the Horizon Sync ERP system via a centralized `AuditLog` table. It complements the existing `UserActivityLog` (which tracks high-level user actions like login, logout, page views, and CRUD events) by capturing granular before/after snapshots of every data mutation (Create, Update, Delete) using SQLAlchemy ORM events. The system stores old and new values as JSONB, masks sensitive fields, supports both synchronous and asynchronous logging strategies, and exposes a React Timeline component for viewing record history.

## Glossary

- **Audit_Log**: The centralized database table that stores field-level change records including old values, new values, action type, and metadata for every tracked data mutation.
- **Audit_Listener**: The SQLAlchemy event listener module that intercepts `after_insert`, `after_update`, and `after_delete` ORM events and creates Audit_Log entries automatically.
- **Sensitive_Field_Registry**: A configuration mechanism (model-level attribute or central config) that declares which column names contain sensitive data and must be excluded from audit snapshots.
- **Audit_API**: The set of FastAPI endpoints that expose Audit_Log data for querying, filtering, and pagination.
- **Audit_Timeline**: The reusable React component that renders the change history of a specific record in a chronological timeline view.
- **Change_Diff**: A computed representation showing which fields changed between old_values and new_values for a single Audit_Log entry.
- **Async_Audit_Writer**: An optional background task mechanism that writes Audit_Log entries outside the main database transaction to avoid slowing down user-facing save operations at high scale. Implemented behind an abstract `AuditQueueBackend` interface with an initial `InProcessQueueBackend` (Python `asyncio.Queue`) and a future upgrade path to `RedisQueueBackend` (Redis Streams) for multi-replica deployments.
- **User_Activity_Log**: The existing model in `app/models/admin.py` that tracks high-level user actions (login, logout, page_view, data CRUD) without field-level detail.
- **Admin_Audit_API**: The set of admin portal FastAPI endpoints (under `/api/v1/admin/audit-logs`) that expose cross-organization Audit_Log data, restricted to `system_admin` users via the `require_admin` dependency.
- **Org_Scoped_Audit_API**: The set of organization-level FastAPI endpoints (under `/api/v1/audit-logs`) that expose Audit_Log data filtered by the current user's `organization_id`, requiring `audit.read` permission.

## Requirements

### Requirement 1: Audit Log Data Model

**User Story:** As a system administrator, I want a centralized audit log table that captures field-level changes with before/after snapshots, so that I can trace exactly what changed, when, and by whom.

#### Acceptance Criteria

1. THE Audit_Log SHALL store the following columns: `id` (UUID primary key), `user_id` (UUID), `organization_id` (UUID), `action` (enum: CREATE, UPDATE, DELETE), `table_name` (string), `record_id` (UUID), `old_values` (JSONB), `new_values` (JSONB), `changed_fields` (JSONB array of field names), `ip_address` (string, nullable), `user_agent` (text, nullable), and `created_at` (timestamp with timezone).
2. THE Audit_Log SHALL use the custom `UUID` and `JSONB` types from `app/models/types.py` for cross-database compatibility.
3. THE Audit_Log SHALL include database indexes on `table_name` + `record_id` (composite), `user_id`, `organization_id`, `action`, and `created_at` to support efficient querying.
4. WHEN an Audit_Log entry is created for an UPDATE action, THE Audit_Log SHALL populate `changed_fields` with the list of column names whose values differ between `old_values` and `new_values`.
5. WHEN an Audit_Log entry is created for a CREATE action, THE Audit_Log SHALL store `old_values` as null and `new_values` as the full serialized state of the new record.
6. WHEN an Audit_Log entry is created for a DELETE action, THE Audit_Log SHALL store `old_values` as the full serialized state of the deleted record and `new_values` as null.

### Requirement 2: Automated SQLAlchemy Event Listener

**User Story:** As a developer, I want audit logging to happen automatically via SQLAlchemy ORM events, so that I do not have to manually write audit code in every endpoint or service method.

#### Acceptance Criteria

1. THE Audit_Listener SHALL intercept `after_insert`, `after_update`, and `after_delete` SQLAlchemy ORM events on all tracked models.
2. THE Audit_Listener SHALL compute the diff between old and new column values for UPDATE operations by inspecting `sqlalchemy.orm.attributes.get_history()` on each mapped column.
3. THE Audit_Listener SHALL serialize column values to JSON-safe representations (converting UUIDs to strings, datetimes to ISO format, Decimals to floats, and Enums to their `.value`).
4. THE Audit_Listener SHALL create the Audit_Log entry within the same database transaction as the triggering operation to ensure data integrity.
5. THE Audit_Listener SHALL provide a model-level opt-in mechanism (e.g., a `__audited__ = True` class attribute) so that only explicitly marked models are tracked.
6. IF the Audit_Listener encounters a serialization error for a column value, THEN THE Audit_Listener SHALL log a warning and substitute the value with the string `"[unserializable]"` instead of failing the transaction.

### Requirement 3: Sensitive Data Masking

**User Story:** As a security officer, I want sensitive fields like hashed passwords and API keys excluded from audit logs, so that the audit trail does not become a security liability.

#### Acceptance Criteria

1. THE Sensitive_Field_Registry SHALL allow models to declare sensitive fields via a `__audit_exclude__` class attribute containing a set of column names.
2. WHEN the Audit_Listener processes a model with declared sensitive fields, THE Audit_Listener SHALL omit those fields entirely from both `old_values` and `new_values` in the Audit_Log entry.
3. THE Sensitive_Field_Registry SHALL provide a global default exclusion list containing `password`, `password_hash`, `api_key`, `secret_key`, `token`, and `refresh_token`.
4. WHEN a field appears in both the model-level `__audit_exclude__` and the global default exclusion list, THE Audit_Listener SHALL exclude the field (union of both lists).

### Requirement 4: Performance and Scalability

**User Story:** As a system architect, I want the audit trail to handle large volumes of data without degrading the performance of user-facing operations, so that the system remains responsive as we scale from a few organizations to many large organizations.

#### Acceptance Criteria

1. THE Audit_Log SHALL store `old_values` and `new_values` as PostgreSQL JSONB columns to enable indexed queries on specific field changes.
2. THE Audit_Log SHALL default to synchronous logging mode (within the same database transaction) to guarantee data integrity for low-to-moderate volume deployments.
3. THE Audit_Log SHALL support an optional asynchronous logging mode via the Async_Audit_Writer, toggled by a configuration setting (e.g., `AUDIT_ASYNC_ENABLED=true`), where audit entries are queued and written in a background task outside the main request transaction.
4. THE Async_Audit_Writer SHALL be implemented behind an abstract `AuditQueueBackend` interface, with an initial `InProcessQueueBackend` using Python `asyncio.Queue` and a background `asyncio.Task` started in FastAPI's lifespan event.
5. THE `InProcessQueueBackend` SHALL support configurable `flush_interval` (seconds) and `batch_size` (number of entries) settings to control how frequently queued entries are bulk-inserted into PostgreSQL.
6. THE `AuditQueueBackend` interface SHALL be designed to allow future implementations (e.g., `RedisQueueBackend` using Redis Streams) without changing the producer (Audit_Listener) code, enabling horizontal scaling across multiple service replicas.
7. THE Audit_API SHALL support cursor-based pagination for listing audit entries to maintain consistent performance regardless of table size.
8. THE Audit_Log table SHALL support partitioning by `created_at` (monthly range partitioning) to enable efficient archival and querying of historical data.

### Requirement 5: Organization-Scoped Audit Log Query API

**User Story:** As an organization admin, I want REST API endpoints to query audit logs scoped to my organization, so that I can review changes made by my team without seeing other organizations' data.

#### Acceptance Criteria

1. THE Audit_API SHALL expose a `GET /api/v1/audit-logs` endpoint that returns paginated audit entries filtered by `table_name`, `record_id`, `user_id`, `action`, `date_from`, `date_to`, and `changed_field`.
2. THE Audit_API SHALL expose a `GET /api/v1/audit-logs/{record_id}/history` endpoint that returns the complete change history for a specific record, ordered by `created_at` descending.
3. WHEN the `changed_field` filter is provided, THE Audit_API SHALL query the JSONB `changed_fields` column to return only entries where the specified field was modified.
4. THE Audit_API SHALL require `audit.read` permission via the existing `require_permission()` dependency.
5. THE Audit_API SHALL automatically filter all query results by the current user's `organization_id` so that org-level users can only see audit entries belonging to their own organization.
6. THE Audit_API SHALL return responses following the existing `PaginationMeta` schema pattern with `page`, `page_size`, `total_items`, `total_pages`, `has_next`, and `has_prev`.

### Requirement 5B: Admin Portal Cross-Organization Audit Log API

**User Story:** As a system administrator using the admin portal, I want to query audit logs across all organizations, so that I can investigate platform-wide changes for compliance and debugging.

#### Acceptance Criteria

1. THE Admin_Audit_API SHALL expose a `GET /api/v1/admin/audit-logs` endpoint that returns paginated audit entries across all organizations, with optional filters for `organization_id`, `table_name`, `record_id`, `user_id`, `action`, `date_from`, `date_to`, and `changed_field`.
2. THE Admin_Audit_API SHALL expose a `GET /api/v1/admin/audit-logs/{record_id}/history` endpoint that returns the complete change history for a specific record across any organization.
3. THE Admin_Audit_API SHALL require `system_admin` user type via the existing `require_admin` dependency, consistent with other admin portal endpoints.
4. THE Admin_Audit_API SHALL support filtering by `organization_id` to allow system admins to narrow results to a specific organization.
5. THE Admin_Audit_API SHALL return responses following the same `PaginationMeta` schema pattern used by the org-scoped API.

### Requirement 6: Audit Log Pydantic Schemas

**User Story:** As a developer, I want well-defined Pydantic schemas for audit log data, so that API request validation and response serialization are consistent with the rest of the codebase.

#### Acceptance Criteria

1. THE Audit_API SHALL use an `AuditLogListItem` schema containing `id`, `user_id`, `organization_id`, `action`, `table_name`, `record_id`, `old_values`, `new_values`, `changed_fields`, `ip_address`, `created_at`, and optional joined fields `user_email`.
2. THE Audit_API SHALL use an `AuditLogDetail` schema that extends `AuditLogListItem` with a computed `change_diff` field showing per-field old/new value pairs.
3. THE Audit_API SHALL use an `AuditLogListResponse` schema containing `audit_logs` (list of `AuditLogListItem`) and `pagination` (`PaginationMeta`).
4. THE Audit_API SHALL use an `AuditLogHistoryResponse` schema containing `record_id`, `table_name`, `history` (list of `AuditLogDetail`), and `pagination` (`PaginationMeta`).

### Requirement 7: User Context Propagation

**User Story:** As a developer, I want the audit listener to automatically capture the current user's ID, organization ID, and IP address, so that audit entries are attributed correctly without manual passing.

#### Acceptance Criteria

1. THE Audit_Listener SHALL retrieve the current user context (user_id, organization_id, ip_address) from a thread-local or context variable set by FastAPI middleware or dependency injection.
2. WHEN no user context is available (e.g., system-initiated operations, migrations, background tasks), THE Audit_Listener SHALL record `user_id` as null and set a `source` indicator of `"system"` in the Audit_Log metadata.
3. THE Audit_Listener SHALL use a FastAPI middleware or dependency that extracts user context from the authenticated request and stores it in a `contextvars.ContextVar` accessible by the SQLAlchemy event handlers.

### Requirement 8: Frontend Audit Timeline Component

**User Story:** As a user, I want to view the change history of any record in a timeline format, so that I can understand what changed and when.

#### Acceptance Criteria

1. THE Audit_Timeline SHALL be a reusable React component that accepts `recordId` and `tableName` as props and fetches the audit history from the Audit_API.
2. THE Audit_Timeline SHALL display each audit entry as a timeline node showing the action type (Create/Update/Delete), timestamp, user email, and a summary of changed fields.
3. WHEN a timeline node for an UPDATE action is expanded, THE Audit_Timeline SHALL display a side-by-side or inline diff view showing old and new values for each changed field.
4. THE Audit_Timeline SHALL support infinite scroll or "Load More" pagination to handle records with extensive change histories.
5. THE Audit_Timeline SHALL be placed in the shared UI library at `horizon-sync/libs/shared/ui/src/components/audit/` for reuse across platform and inventory apps.
