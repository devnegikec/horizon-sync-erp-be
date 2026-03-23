# Implementation Plan: Admin Portal

## Overview

Step-by-step implementation of the super-admin portal for the ERP platform. Each feature group implements the full backend stack (models → repositories → services → endpoints) plus a frontend steering document. Tasks are ordered by priority: P0 first, then P1, P2, and nice-to-have features.

The Alembic migration for all 4 new tables is consolidated in the first task group since subsequent features depend on them.

## Tasks

- [x] 1. Admin Foundation — Auth Gate, New Tables, and Admin Router (P0)

  - [x] 1.1 Create SQLAlchemy models for all 4 new admin tables (`UserActivityLog`, `AdminAuditLog`, `AdminNotification`, `FeatureFlag`) in `core-service/app/models/admin.py`

    - Define models matching the design document schema (user_activity_logs, admin_audit_logs, admin_notifications, feature_flags)
    - Add proper indexes, foreign keys, and column constraints
    - Register models in `core-service/app/models/__init__.py`
    - _Requirements: 6.1, 8.1, 9.1, 15.1_

  - [x] 1.2 Create Alembic migration for all 4 new tables in a single migration file

    - Generate migration with `alembic revision --autogenerate`
    - Include all indexes defined in the design (idx_activity_logs_user, idx_audit_logs_admin, idx_notifications_recipient, idx_notifications_unread, idx_feature_flags_org, etc.)
    - _Requirements: 6.1, 8.1, 9.1, 15.1_

  - [x] 1.3 Implement `require_admin` dependency in `identity-service/app/dependencies.py`

    - Wrap `get_current_active_user` and validate `user_type == UserType.SYSTEM_ADMIN`
    - Return 403 with "Admin access required" for non-admin users
    - Return the `CurrentUser` unchanged for admin users
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 1.4 Create admin auth endpoint in `identity-service`

    - Create `identity-service/app/api/v1/endpoints/admin/` package with `__init__.py`
    - Create `identity-service/app/api/v1/endpoints/admin/auth.py` with `GET /identity/admin/me` endpoint
    - Register the admin router in `identity-service/app/api/v1/router.py` under prefix `/identity/admin`
    - _Requirements: 1.6, 1.7_

  - [x] 1.5 Create Pydantic schemas for admin auth responses in `identity-service/app/schemas/admin.py`

    - `AdminProfileResponse` with fields: id, email, first_name, last_name, display_name, user_type, organization_id, permissions
    - _Requirements: 1.6_

  - [x] 1.6 Implement `require_admin` dependency in `core-service/app/dependencies.py`

    - Wrap `get_current_user` and validate `user_type == "system_admin"` (from JWT token payload)
    - Return 403 with "Admin access required" for non-admin users
    - This is used by all core-service admin endpoints (dashboard, org mgmt, user mgmt, etc.)
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 1.7 Create admin router mount under `/api/v1/admin/` prefix in core-service

    - Create `core-service/app/api/v1/endpoints/admin/` package with `__init__.py`
    - Register the admin router in the main app router
    - _Requirements: 1.7_

  - [ ]\* 1.8 Write property tests for admin auth gate

    - **Property 1: Admin gate rejects non-admin users and accepts admin users** — test in both identity-service and core-service
    - **Validates: Requirements 1.3, 1.4, 1.5**
    - **Property 2: Admin /me endpoint returns complete profile** — test in identity-service
    - **Validates: Requirements 1.6**

  - [x] 1.9 Create frontend steering document `.kiro/steering/frontend-admin-auth.md`
    - Document identity-service `/identity/admin/me` endpoint for admin profile
    - Document core-service `require_admin` gate behavior (403 for non-admin)
    - Include TypeScript types, service layer, React hooks, error handling, testing checklist
    - Follow format of existing `.kiro/steering/frontend-qr-product-settings-module.md`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 2. Checkpoint — Ensure admin foundation tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [x] 3. Admin Dashboard (P0)

  - [x] 3.1 Create Pydantic schemas for dashboard responses

    - `OrgMetrics` (total, active, on_trial), `UserMetrics` (total, active), `RevenueMetrics` (total_invoiced, total_outstanding, total_received)
    - `ActivityLogItem`, `DashboardOverview` combining all metrics + recent_activity
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 3.2 Create `AdminDashboardRepository` in `core-service/app/repositories/admin_dashboard_repository.py`

    - Cross-org aggregation queries for org counts, user counts, revenue sums
    - Recent activity query (last 10 entries sorted by created_at desc)
    - Date range filtering support for revenue and activity metrics
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.3 Create `AdminDashboardService` in `core-service/app/services/admin_dashboard_service.py`

    - Orchestrate repository calls and assemble `DashboardOverview` response
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

  - [x] 3.4 Create dashboard endpoint `GET /admin/dashboard/overview` in `core-service/app/api/v1/endpoints/admin/dashboard.py`

    - Accept optional `date_from` and `date_to` query parameters
    - Use `require_admin` dependency
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]\* 3.5 Write property tests for dashboard metrics

    - **Property 3: Dashboard metrics match database aggregations**
    - **Validates: Requirements 2.1, 2.2, 2.3**
    - **Property 4: Dashboard date range filtering**
    - **Validates: Requirements 2.5**
    - **Property 5: Dashboard recent activity ordering**
    - **Validates: Requirements 2.4**

  - [x] 3.6 Create frontend steering document `.kiro/steering/frontend-admin-dashboard.md`
    - Document dashboard overview endpoint, TypeScript types, service layer, React hooks, component examples, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [-] 4. Organization Management (P0)

  - [x] 4.1 Create Pydantic schemas for organization admin operations

    - `AdminOrgCreate`, `AdminOrgUpdate`, `AdminOrgListResponse`, `AdminOrgDetailResponse` (with user_count, invoice_count, payment_total)
    - `AdminOrgBillingResponse` (on_trial, trial_expiry, paid_until, total_invoiced, total_paid, outstanding)
    - _Requirements: 3.1, 3.2, 3.5, 3.6_

  - [~] 4.2 Create `AdminOrganizationRepository` in `core-service/app/repositories/admin_organization_repository.py`

    - Cross-org list with search (name/short_code), status filter, pagination
    - Get by ID with summary counts (user_count, invoice_count, payment_total)
    - Create, update, deactivate_all_users (for suspension cascade)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

  - [~] 4.3 Create `AdminOrganizationService` in `core-service/app/services/admin_organization_service.py`

    - CRUD operations with duplicate short_code check (409)
    - Suspension cascade: set all org users to is_active=false
    - Integrate `AdminAuditService` for logging changes
    - _Requirements: 3.1, 3.6, 3.7, 3.8, 8.2_

  - [~] 4.4 Create organization admin endpoints in `core-service/app/api/v1/endpoints/admin/organizations.py`

    - `POST /admin/organizations` — create org (201, 409 for duplicate short_code)
    - `GET /admin/organizations` — paginated list with search, status filter
    - `GET /admin/organizations/{id}` — detail with summary counts (404 if not found)
    - `PATCH /admin/organizations/{id}` — partial update with suspension cascade
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [ ]\* 4.5 Write property tests for organization management

    - **Property 6: Organization creation round-trip**
    - **Validates: Requirements 3.1**
    - **Property 7: Organization list filtering correctness**
    - **Validates: Requirements 3.2, 3.3, 3.4**
    - **Property 8: Organization detail includes correct summary counts**
    - **Validates: Requirements 3.5**
    - **Property 9: Organization partial update preserves unmodified fields**
    - **Validates: Requirements 3.6**
    - **Property 10: Organization suspension cascades to users**
    - **Validates: Requirements 3.7**
    - **Property 11: Duplicate short_code rejection**
    - **Validates: Requirements 3.8**

  - [~] 4.6 Create frontend steering document `.kiro/steering/frontend-admin-organizations.md`
    - Document all org endpoints, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 5. User Management and Roles (P0)

  - [~] 5.1 Create Pydantic schemas for user admin operations

    - `AdminUserCreate`, `AdminUserUpdate`, `AdminUserListResponse`, `AdminUserDetailResponse` (with organization_name)
    - Role validation: only allow `system_admin`, `org_admin`, `user`
    - _Requirements: 4.1, 4.5, 4.6, 4.9, 4.12_

  - [~] 5.2 Create `AdminUserRepository` in `core-service/app/repositories/admin_user_repository.py`

    - Cross-org user list with joins to organizations for organization_name
    - Filters: organization_id, search (email/mobile), is_active, pagination
    - Create user in specified org, update roles/is_active
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.9_

  - [~] 5.3 Create `AdminUserService` in `core-service/app/services/admin_user_service.py`

    - CRUD with duplicate email check (409), not found check (404)
    - Role change and activation/deactivation trigger audit logs
    - Password hashing for new user creation
    - _Requirements: 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 8.3_

  - [~] 5.4 Create user admin endpoints in `core-service/app/api/v1/endpoints/admin/users.py`

    - `POST /admin/users` — create user (201, 409 for duplicate email)
    - `GET /admin/users` — paginated list with org_id, search, is_active filters
    - `GET /admin/users/{id}` — detail with organization_name (404 if not found)
    - `PATCH /admin/users/{id}` — update roles, is_active
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12_

  - [ ]\* 5.5 Write property tests for user management

    - **Property 12: Cross-org user list filtering correctness**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4**
    - **Property 13: User role update replaces roles array**
    - **Validates: Requirements 4.6**
    - **Property 14: User activation round-trip**
    - **Validates: Requirements 4.7, 4.8**
    - **Property 15: User creation round-trip with org assignment**
    - **Validates: Requirements 4.9**
    - **Property 16: Duplicate email rejection**
    - **Validates: Requirements 4.10**
    - **Property 17: Role validation**
    - **Validates: Requirements 4.12**

  - [~] 5.6 Create frontend steering document `.kiro/steering/frontend-admin-users.md`
    - Document all user endpoints, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [~] 6. Checkpoint — Ensure all P0 tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Invoice & Payment Tracking (P1)

  - [~] 7.1 Create Pydantic schemas for invoice and payment admin operations

    - `AdminInvoiceListResponse`, `AdminInvoiceDetailResponse` (with line items + payment history)
    - `AdminInvoiceCreate`, `AdminInvoiceSendResponse`
    - `AdminPaymentListResponse`
    - _Requirements: 5.1, 5.5, 5.6, 5.8_

  - [~] 7.2 Create `AdminInvoiceRepository` in `core-service/app/repositories/admin_invoice_repository.py`

    - Cross-org invoice list with filters: organization_id, status, date_from/date_to, pagination
    - Invoice detail with line items and associated payments
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

  - [~] 7.3 Create `AdminPaymentRepository` in `core-service/app/repositories/admin_payment_repository.py`

    - Cross-org payment list with filters: organization_id, status, pagination
    - _Requirements: 5.8, 5.9, 5.10_

  - [~] 7.4 Create `AdminInvoiceService` in `core-service/app/services/admin_invoice_service.py`

    - List/detail/create invoices cross-org
    - Invoice send: create communication_log entry, update invoice status to "pending"
    - _Requirements: 5.1, 5.5, 5.6, 5.7_

  - [~] 7.5 Create `AdminPaymentService` in `core-service/app/services/admin_payment_service.py`

    - List payments cross-org with filters
    - _Requirements: 5.8, 5.9, 5.10_

  - [~] 7.6 Create invoice and payment admin endpoints in `core-service/app/api/v1/endpoints/admin/invoices.py` and `payments.py`

    - `GET /admin/invoices` — paginated list with org_id, status, date range filters
    - `GET /admin/invoices/{id}` — detail with line items + payment history
    - `POST /admin/invoices` — create invoice in specified org (201)
    - `POST /admin/invoices/{id}/send` — send invoice via communication_log
    - `GET /admin/payments` — paginated list with org_id, status filters
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_

  - [ ]\* 7.7 Write property tests for invoice and payment tracking

    - **Property 18: Invoice list cross-org filtering**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**
    - **Property 19: Invoice detail includes line items and payments**
    - **Validates: Requirements 5.5**
    - **Property 20: Invoice send creates communication log and updates status**
    - **Validates: Requirements 5.7**
    - **Property 21: Payment list cross-org filtering**
    - **Validates: Requirements 5.8, 5.9, 5.10**

  - [~] 7.8 Create frontend steering document `.kiro/steering/frontend-admin-invoices-payments.md`
    - Document all invoice/payment endpoints, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 8. User Activity Monitoring and Logging (P1)

  - [~] 8.1 Create Pydantic schemas for activity log operations

    - `ActivityLogCreate`, `ActivityLogListResponse`, `ActivityLogItem`
    - `LoginHistoryResponse`
    - _Requirements: 6.1, 6.4, 6.9_

  - [~] 8.2 Create `UserActivityLogRepository` in `core-service/app/repositories/user_activity_log_repository.py`

    - Create activity log entries (login, logout, login_failed, page_view, data_create, data_update, data_delete)
    - List with filters: user_id, organization_id, action, date_from/date_to, pagination
    - Login history for specific user (action in login, login_failed)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [~] 8.3 Create `UserActivityLogService` in `core-service/app/services/user_activity_log_service.py`

    - Log activity entries with IP address and user agent extraction
    - Query activity logs with combined filters, sorted by created_at desc
    - Note: Login/logout events originate from identity-service; core-service logs data CRUD events. Identity-service should call core-service's activity log endpoint (or write directly to shared DB) for login events.
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [~] 8.4 Create activity log admin endpoints in `core-service/app/api/v1/endpoints/admin/activity_logs.py`

    - `GET /admin/activity-logs` — paginated list with user_id, org_id, action, date range filters
    - `GET /admin/activity-logs/users/{user_id}/login-history` — login/login_failed entries for user
    - _Requirements: 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [ ]\* 8.5 Write property tests for activity monitoring

    - **Property 22: Activity log creation on login events**
    - **Validates: Requirements 6.2, 6.3**
    - **Property 23: Activity log filtering and sorting**
    - **Validates: Requirements 6.4, 6.5, 6.6, 6.7, 6.8**
    - **Property 24: Login history returns only login events for specified user**
    - **Validates: Requirements 6.9**

  - [~] 8.6 Create frontend steering document `.kiro/steering/frontend-admin-activity-logs.md`
    - Document activity log endpoints, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 9. Organization Subscription and Billing Status (P1)

  - [~] 9.1 Create Pydantic schemas for subscription and billing operations

    - `SubscriptionOverview` (on_trial_count, active_paid_count, expired_trial_count, overdue_count)
    - `ExpiringOrgListResponse`, `OverdueOrgListResponse`
    - `OrgBillingDetailResponse` (on_trial, trial_expiry, paid_until, total_invoiced, total_paid, outstanding)
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [~] 9.2 Create `AdminSubscriptionRepository` in `core-service/app/repositories/admin_subscription_repository.py`

    - Subscription overview aggregation queries (on_trial, active_paid, expired_trial, overdue counts)
    - Expiring organizations query (trial_expiry or paid_until within days_ahead)
    - Overdue organizations query (paid_until < now, on_trial = false, sorted by paid_until asc)
    - Organization billing detail (total_invoiced, total_paid, outstanding)
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [~] 9.3 Create `AdminSubscriptionService` in `core-service/app/services/admin_subscription_service.py`

    - Subscription overview, expiring list, overdue list
    - Billing update side effects: paid_until update sets on_trial=false, trial_expiry update sets on_trial=true
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [~] 9.4 Create subscription admin endpoints in `core-service/app/api/v1/endpoints/admin/subscriptions.py`

    - `GET /admin/subscriptions/overview` — trial/paid/expired/overdue counts
    - `GET /admin/subscriptions/expiring?days_ahead=30` — expiring organizations
    - `GET /admin/subscriptions/overdue` — overdue organizations
    - `GET /admin/organizations/{id}/billing` — billing detail for single org
    - _Requirements: 7.1, 7.2, 7.3, 7.6_

  - [ ]\* 9.5 Write property tests for subscription and billing

    - **Property 25: Subscription overview counts match database state**
    - **Validates: Requirements 7.1**
    - **Property 26: Expiring organizations filtering**
    - **Validates: Requirements 7.2**
    - **Property 27: Overdue organizations filtering and sorting**
    - **Validates: Requirements 7.3**
    - **Property 28: Billing update side effects**
    - **Validates: Requirements 7.4, 7.5**
    - **Property 29: Organization billing detail aggregation**
    - **Validates: Requirements 7.6**

  - [~] 9.6 Create frontend steering document `.kiro/steering/frontend-admin-subscriptions.md`
    - Document subscription/billing endpoints, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [~] 10. Checkpoint — Ensure all P1 tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. Audit Trail and System Logs (P2)

  - [~] 11.1 Create Pydantic schemas for audit log operations

    - `AuditLogListResponse`, `AuditLogItem` (admin_user_id, action, target_type, target_id, changes, ip_address, created_at)
    - _Requirements: 8.1, 8.4_

  - [~] 11.2 Create `AdminAuditLogRepository` in `core-service/app/repositories/admin_audit_log_repository.py`

    - List with filters: admin_user_id, target_type, target_id, date_from/date_to, pagination
    - Sorted by created_at descending
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 8.8_

  - [~] 11.3 Create `AdminAuditService` in `core-service/app/services/admin_audit_service.py`

    - Shared audit logger: log(admin_user_id, action, target_type, target_id, old_values, new_values, ip_address)
    - Query audit logs with combined filters
    - _Requirements: 8.2, 8.3, 8.4, 8.9_

  - [~] 11.4 Create audit log admin endpoint in `core-service/app/api/v1/endpoints/admin/audit_logs.py`

    - `GET /admin/audit-logs` — paginated list with admin_user_id, target_type, target_id, date range filters
    - _Requirements: 8.4, 8.5, 8.6, 8.7, 8.8_

  - [ ]\* 11.5 Write property tests for audit trail

    - **Property 30: Admin write operations create audit logs**
    - **Validates: Requirements 8.2, 8.3**
    - **Property 31: Audit log filtering and sorting**
    - **Validates: Requirements 8.4, 8.5, 8.6, 8.7, 8.8**

  - [~] 11.6 Create frontend steering document `.kiro/steering/frontend-admin-audit-logs.md`
    - Document audit log endpoint, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 12. Notification Center (P2)

  - [~] 12.1 Create Pydantic schemas for notification operations

    - `NotificationListResponse`, `NotificationItem`, `UnreadCountResponse`
    - _Requirements: 9.1, 9.6, 9.10_

  - [~] 12.2 Create `AdminNotificationRepository` in `core-service/app/repositories/admin_notification_repository.py`

    - List notifications for a specific admin user with is_read filter, pagination, sorted by created_at desc
    - Mark single notification as read (set is_read=true, read_at=now)
    - Mark all notifications as read for a user
    - Unread count for a user
    - _Requirements: 9.6, 9.7, 9.8, 9.9, 9.10_

  - [~] 12.3 Create `AdminNotificationService` in `core-service/app/services/admin_notification_service.py`

    - `notify_all_admins(notification_type, title, message, reference_type, reference_id)` — create notification for every system_admin user
    - Query/mark-read/mark-all-read/unread-count operations
    - _Requirements: 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_

  - [~] 12.4 Integrate notification triggers into existing services

    - Payment completed → "payment_received" notification
    - Trial expiring (within 7 days) → "trial_expiring" notification
    - User deactivated → "user_locked" notification
    - Invoice overdue → "invoice_overdue" notification
    - _Requirements: 9.2, 9.3, 9.4, 9.5_

  - [~] 12.5 Create notification admin endpoints in `core-service/app/api/v1/endpoints/admin/notifications.py`

    - `GET /admin/notifications` — paginated list for requesting admin, with is_read filter
    - `GET /admin/notifications/unread-count` — unread count for requesting admin
    - `PATCH /admin/notifications/{id}/read` — mark single notification as read
    - `POST /admin/notifications/mark-all-read` — mark all as read for requesting admin
    - _Requirements: 9.6, 9.7, 9.8, 9.9, 9.10_

  - [ ]\* 12.6 Write property tests for notification center

    - **Property 32: System event notifications reach all admins**
    - **Validates: Requirements 9.2, 9.3, 9.4, 9.5**
    - **Property 33: Notification list scoped to requesting admin**
    - **Validates: Requirements 9.6, 9.7**
    - **Property 34: Mark notification as read sets fields correctly**
    - **Validates: Requirements 9.8**
    - **Property 35: Mark all notifications as read**
    - **Validates: Requirements 9.9**
    - **Property 36: Unread notification count accuracy**
    - **Validates: Requirements 9.10**

  - [~] 12.7 Create frontend steering document `.kiro/steering/frontend-admin-notifications.md`
    - Document notification endpoints, TypeScript types, service layer, React hooks, component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ] 13. Basic Reports and Data Export (P2)

  - [~] 13.1 Create Pydantic schemas and utility for export operations

    - Export query params schema (format, organization_id, date_from, date_to)
    - CSV generation utility function
    - PDF generation utility function (using reportlab or similar)
    - _Requirements: 10.1, 10.6_

  - [~] 13.2 Create `AdminExportRepository` in `core-service/app/repositories/admin_export_repository.py`

    - Query organizations, users, payments with optional org_id and date range filters
    - Enforce 50,000 row cap
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.8_

  - [~] 13.3 Create `AdminExportService` in `core-service/app/services/admin_export_service.py`

    - Generate CSV/PDF for organizations, users, payments
    - Set Content-Disposition header: `attachment; filename="{report_name}_{date}.{format}"`
    - _Requirements: 10.1, 10.2, 10.3, 10.6, 10.7, 10.8_

  - [~] 13.4 Create export admin endpoints in `core-service/app/api/v1/endpoints/admin/export.py`

    - `GET /admin/export/organizations?format=csv|pdf&organization_id=&date_from=&date_to=`
    - `GET /admin/export/users?format=csv&organization_id=&date_from=&date_to=`
    - `GET /admin/export/payments?format=csv&organization_id=&date_from=&date_to=`
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

  - [ ]\* 13.5 Write property tests for export

    - **Property 37: CSV export round-trip**
    - **Validates: Requirements 10.1, 10.2, 10.3**
    - **Property 38: Export filtering by organization and date range**
    - **Validates: Requirements 10.4, 10.5**
    - **Property 39: Export Content-Disposition header format**
    - **Validates: Requirements 10.7**

  - [~] 13.6 Create frontend steering document `.kiro/steering/frontend-admin-reports-export.md`
    - Document export endpoints, TypeScript types, service layer, React hooks (download triggers), component examples, error handling, testing checklist
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [~] 14. Checkpoint — Ensure all P2 tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ]\* 15. Email Template Management (Nice-to-Have, Req 12)

  - [ ]\* 15.1 Create Pydantic schemas for email template CRUD

    - `EmailTemplateCreate`, `EmailTemplateUpdate`, `EmailTemplateResponse`
    - Validate placeholder syntax in subject_template and body_template
    - _Requirements: 12.1, 12.2_

  - [ ]\* 15.2 Create `AdminEmailTemplateRepository` and `AdminEmailTemplateService`

    - CRUD operations for email templates
    - Template resolution: org-specific → system default fallback
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ]\* 15.3 Create email template admin endpoints

    - CRUD endpoints under `/admin/email-templates`
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ]\* 15.4 Create frontend steering document `.kiro/steering/frontend-admin-email-templates.md`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ]\* 16. Bulk User Operations (Nice-to-Have, Req 13)

  - [ ]\* 16.1 Create Pydantic schemas for bulk user operations

    - `BulkUserActionRequest` (user_ids list, action: activate/deactivate), max 100 IDs validation
    - `BulkUserActionResponse` (updated_count)
    - _Requirements: 13.1, 13.2, 13.3_

  - [ ]\* 16.2 Create bulk user service and endpoint

    - `POST /admin/users/bulk-action` — activate/deactivate multiple users
    - Create audit log entry for each affected user
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]\* 16.3 Write property test for bulk operations

    - **Property 42: Bulk user operations**
    - **Validates: Requirements 13.1, 13.2, 13.4**

  - [ ]\* 16.4 Create frontend steering document `.kiro/steering/frontend-admin-bulk-operations.md`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ]\* 17. System Health Monitoring (Nice-to-Have, Req 14)

  - [ ]\* 17.1 Create Pydantic schemas for health check response

    - `SystemHealthResponse` (core_service status, identity_service status, db connectivity, db pool stats, avg response time, timestamp)
    - _Requirements: 14.1, 14.2, 14.3_

  - [ ]\* 17.2 Create health check service and endpoint

    - `GET /admin/health` — check core-service, identity-service, DB connectivity, pool stats, avg response time
    - _Requirements: 14.1, 14.2, 14.3_

  - [ ]\* 17.3 Create frontend steering document `.kiro/steering/frontend-admin-system-health.md`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [ ]\* 18. Feature Flags and Org-Level Configuration (Nice-to-Have, Req 15)

  - [ ]\* 18.1 Create Pydantic schemas for feature flag operations

    - `FeatureFlagCreate`, `FeatureFlagUpdate`, `FeatureFlagResponse`, `FeatureFlagListResponse`
    - _Requirements: 15.1, 15.2, 15.3_

  - [ ]\* 18.2 Create `FeatureFlagRepository` and `FeatureFlagService`

    - CRUD for feature flags per organization
    - `check_feature_flag(feature_key)` dependency for org-scoped endpoints
    - _Requirements: 15.1, 15.2, 15.3, 15.4_

  - [ ]\* 18.3 Create feature flag admin endpoints

    - `GET /admin/feature-flags?organization_id=` — list flags for org
    - `PUT /admin/feature-flags/{id}` — toggle flag
    - _Requirements: 15.2, 15.3_

  - [ ]\* 18.4 Write property tests for feature flags

    - **Property 40: Feature flag toggle round-trip**
    - **Validates: Requirements 15.3**
    - **Property 41: Feature flag gate dependency**
    - **Validates: Requirements 15.4**

  - [ ]\* 18.5 Create frontend steering document `.kiro/steering/frontend-admin-feature-flags.md`
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [~] 19. Final Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests reference specific property numbers from the design document
- Checkpoints ensure incremental validation at each priority tier
- Frontend steering documents (Req 11) are embedded as the last sub-task of each feature group
- The Alembic migration in task 1.2 creates ALL 4 new tables upfront to avoid migration ordering issues
- Nice-to-have features (tasks 15-18) are entirely optional top-level groups
- **Service split**: Admin auth (`require_admin` dependency + `/admin/me` endpoint) lives in `identity-service` since that's where authentication, user models, and login logic reside. All admin data-management endpoints (dashboard, org CRUD, user mgmt, invoices, etc.) live in `core-service` with its own `require_admin` that validates `user_type` from the JWT token.
- **Shared DB**: Both services share the same PostgreSQL database, so identity-service login events can write directly to `user_activity_logs` table.
