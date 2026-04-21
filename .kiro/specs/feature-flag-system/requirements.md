# Requirements Document

## Introduction

The Feature Flag System enables Horizon Sync ERP administrators to control feature availability at runtime without redeployment. For the MVP (client demo), the system supports GLOBAL-scoped flags only with simple enabled/disabled evaluation. The data model is designed for extensibility — columns for tenant, user, and rollout percentage exist in the schema but are not actively used in MVP evaluation logic. The system integrates into the existing FastAPI/SQLAlchemy backend and React/TypeScript frontend, following the established repository/service/endpoint architecture.

## Glossary

- **Feature_Flag_Service**: The backend service layer responsible for creating, updating, deleting, and evaluating feature flags.
- **Feature_Flag_Repository**: The data access layer that performs CRUD operations on the feature_flags table.
- **Feature_Flag_API**: The set of FastAPI endpoints exposing feature flag management and evaluation operations.
- **Flag_Evaluator**: The component within Feature_Flag_Service that resolves a flag's effective status by looking up the GLOBAL flag for a given feature name.
- **Admin_UI**: The React-based admin interface for managing feature flags (toggle, create, view).
- **Scope**: The level at which a feature flag applies. MVP supports GLOBAL only. TENANT and USER are reserved for future use.

## Requirements

### Requirement 1: Feature Flag Data Model

**User Story:** As a developer, I want a well-defined feature flag data model, so that flags can be stored with all necessary metadata and the schema is extensible for future scoped evaluation.

#### Acceptance Criteria

1. THE Feature_Flag_Repository SHALL store each feature flag with the following fields: id (UUID primary key), name (unique string), description (text, nullable), enabled (boolean, default false), scope (enum: GLOBAL, TENANT, USER, default GLOBAL), tenant_id (UUID, nullable), user_id (UUID, nullable), rollout_percentage (integer 0–100, nullable), created_at (timestamp), updated_at (timestamp).
2. THE Feature_Flag_Repository SHALL enforce a unique constraint on the combination of name, scope, tenant_id, and user_id.
3. WHEN a feature flag is created via the MVP API, THE Feature_Flag_Repository SHALL set scope to GLOBAL, tenant_id to null, and user_id to null.

### Requirement 2: Feature Flag CRUD API

**User Story:** As an administrator, I want API endpoints to create, read, update, and delete feature flags, so that I can manage feature availability from the admin portal.

#### Acceptance Criteria

1. WHEN a valid create request is received with name, description, and enabled fields, THE Feature_Flag_API SHALL create a new GLOBAL-scoped feature flag and return the created flag with HTTP 201.
2. WHEN a create request contains a duplicate name, THE Feature_Flag_API SHALL return HTTP 409 with a descriptive error message.
3. WHEN a valid update request is received with a flag id, THE Feature_Flag_API SHALL update the specified fields (name, description, enabled) and return the updated flag with HTTP 200.
4. WHEN a delete request is received with a valid flag id, THE Feature_Flag_API SHALL delete the flag and return HTTP 204.
5. WHEN a delete request references a non-existent flag id, THE Feature_Flag_API SHALL return HTTP 404.
6. WHEN a list request is received, THE Feature_Flag_API SHALL return all feature flags without pagination.
7. WHEN a get-by-id request is received with a valid flag id, THE Feature_Flag_API SHALL return the feature flag with HTTP 200.

### Requirement 3: Flag Evaluation Logic

**User Story:** As a developer, I want a reliable flag evaluation mechanism, so that the system correctly determines whether a feature is enabled.

#### Acceptance Criteria

1. WHEN evaluating a feature flag by name, THE Flag_Evaluator SHALL look up the GLOBAL-scoped flag matching the provided feature name.
2. WHEN no GLOBAL flag is found for the given feature name, THE Flag_Evaluator SHALL return disabled (false) as the safe default.
3. WHEN a matching GLOBAL flag is found, THE Flag_Evaluator SHALL return the value of the enabled field.
4. IF the Flag_Evaluator encounters a database error during evaluation, THEN THE Flag_Evaluator SHALL return disabled (false) as the safe default.

### Requirement 4: Flag Evaluation API Endpoint

**User Story:** As a frontend or backend consumer, I want an API endpoint to check if a feature is enabled, so that I can conditionally render UI or execute logic.

#### Acceptance Criteria

1. WHEN a GET request is received with a feature name path parameter, THE Feature_Flag_API SHALL return the evaluated flag status as a JSON object containing feature_name and enabled (boolean).
2. WHEN the feature name references a non-existent flag, THE Feature_Flag_API SHALL return enabled as false.

### Requirement 5: Helper Utility for Integration

**User Story:** As a developer, I want a simple helper function to check feature flags from any service, so that I can gate features with minimal boilerplate.

#### Acceptance Criteria

1. THE Feature_Flag_Service SHALL expose an `is_feature_enabled(feature_name, db_session)` function that returns a boolean.
2. WHEN `is_feature_enabled` is called, THE Feature_Flag_Service SHALL query the database directly for the GLOBAL flag matching the feature name and return the enabled value.
3. IF `is_feature_enabled` encounters a database error, THEN THE Feature_Flag_Service SHALL return disabled (false) and log the error at ERROR level.

### Requirement 6: Sample Integration in Invoice Flow

**User Story:** As a developer, I want a reference integration of the feature flag system in the invoice module, so that the team has a working example to follow for other modules.

#### Acceptance Criteria

1. THE Invoice_Service SHALL use `is_feature_enabled` to gate at least one feature in the invoice creation or update flow (e.g., "invoice_auto_journal_posting").
2. WHEN the gated feature flag is disabled, THE Invoice_Service SHALL skip the gated logic and continue with the default behavior.
3. WHEN the gated feature flag is enabled, THE Invoice_Service SHALL execute the gated logic.

### Requirement 7: Admin UI for Feature Flag Management

**User Story:** As an administrator, I want a UI to manage feature flags within the Settings section of the admin portal, so that I can toggle flags and create new ones without using API tools.

#### Acceptance Criteria

1. THE Admin_UI SHALL render the feature flag management interface as a new tab in the Settings section of the admin portal.
2. THE Admin_UI SHALL position the feature flag management tab immediately after the existing "Admin Users" tab in the Settings section.
3. THE Admin_UI SHALL label the feature flag management tab "Feature Controls" to provide a user-friendly name instead of the technical term "Feature Flags".
4. THE Admin_UI SHALL display a table of all feature flags with columns: name, description, enabled status (toggle), and created_at.
5. WHEN an administrator clicks a toggle on a flag row, THE Admin_UI SHALL send an update request to the Feature_Flag_API and reflect the new status.
6. WHEN creating a new flag, THE Admin_UI SHALL present a form with fields for name, description, and enabled.
7. IF the API returns an error during a flag operation, THEN THE Admin_UI SHALL display the error message to the administrator.

### Requirement 8: Logging

**User Story:** As a developer, I want basic logging for flag evaluations, so that I can troubleshoot issues during the demo.

#### Acceptance Criteria

1. WHEN a flag is evaluated, THE Feature_Flag_Service SHALL log the feature name and result (enabled/disabled) at INFO level.
2. IF a flag evaluation fails due to an unexpected error, THEN THE Feature_Flag_Service SHALL log the error details at ERROR level.

### Requirement 9: Unit Tests for Flag Evaluation

**User Story:** As a developer, I want unit tests for the flag evaluation logic, so that I can verify correctness and prevent regressions.

#### Acceptance Criteria

1. THE test suite SHALL verify that the evaluator returns the correct enabled status for an existing GLOBAL flag.
2. THE test suite SHALL verify that the evaluator returns disabled (false) when no flag exists for a given feature name.
3. THE test suite SHALL verify that the evaluator returns disabled (false) when a database error occurs during evaluation.

## Future Enhancements

The following capabilities are deferred to post-demo iterations based on client feedback:

- **TENANT and USER scope evaluation**: Priority chain (USER > TENANT > GLOBAL) for multi-scope flag resolution.
- **Rollout percentage evaluation**: Hash-based percentage rollout for gradual feature enablement.
- **Bulk flag evaluation endpoint**: Evaluate multiple flags in a single API request.
- **In-memory caching with TTL**: Cache evaluated results with configurable time-to-live and invalidation on flag changes.
- **Permission-based access control**: Require `feature_flag.manage` permission for CRUD operations instead of admin-only access.
- **Pagination on list endpoint**: Paginated flag listing with filters for scope, tenant_id, and enabled status.
- **Tenant/user filters in Admin UI**: Filter dropdowns for scope, tenant_id, and user_id in the management table.
- **Detailed audit logging**: Full audit trail with operation type, actor, evaluation context (tenant_id, user_id), resolved scope, and evaluation duration.
