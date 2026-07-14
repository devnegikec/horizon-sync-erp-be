# Requirements Document — Admin Portal

## Introduction

The Admin Portal is a super-admin management interface for the ERP platform. It provides system-level visibility and control across all organizations, users, invoices, payments, and system activity. The portal is built as a step-by-step feature set: each step delivers a self-contained backend (models, migrations, repositories, services, endpoints) plus a frontend steering document for UI integration.

The portal distinguishes between two admin scopes:

- **system_admin**: Cross-organization access to all data and operations.
- **org_admin**: Scoped to a single organization's data and operations.

The implementation leverages the existing FastAPI + PostgreSQL codebase, JWT auth via identity-service, RBAC permission system (`require_permission`, `has_permission` with wildcard support), and the established repository/service/endpoint patterns.

## GlossaryGood question — let me think through what a solid MVP Admin Portal needs beyond your four items.

Your four core features are a strong start. Here's what I'd recommend adding for a well-rounded MVP:

## Your Core 4 (solid picks)

1. User Activity Monitoring & Logging
2. User Management (per organization)
3. Organization Management
4. Invoice Creation, Sending & Payment Tracking

## Recommended Additions for MVP

5. **Dashboard / Overview** — A landing page with key metrics at a glance (total orgs, active users, revenue summary, recent activity). Without this, admins have no quick pulse on the system.

6. **Role & Permission Management** — You already have `roles TEXT[]` on users. Admins need a way to assign/revoke roles and define what each role can access. This is tightly coupled with User Management.

7. **Authentication & Admin Login** — Separate admin auth flow (or at minimum, admin role gate). You need to protect the portal itself.

8. **Audit Trail / System Logs** — Different from user activity monitoring. This tracks admin actions — who changed what, when. Critical for compliance and debugging.

9. **Notification Center** — Email/in-app notifications for key events: payment received, trial expiring, user locked out, invoice overdue. Even a simple version adds a lot of value.

10. **Organization Subscription/Billing Status** — You have `paid_until`, `on_trial`, `trial_expiry` on organizations. Admins need visibility into which orgs are on trial, expiring soon, or overdue. Ties directly into your invoice/payment tracking.

11. **Basic Reports & Export** — CSV/PDF export for user lists, org lists, payment history. Admins always need to pull data for stakeholders.

## Nice-to-Have (Post-MVP)

- Email template management
- Bulk user operations (activate/deactivate)
- System health monitoring
- Feature flags / org-level config
- Support ticket integration

## Suggested MVP Priority Order

| Priority | Feature                     | Why                              |
| -------- | --------------------------- | -------------------------------- |
| P0       | Admin Auth & Login          | Can't access anything without it |
| P0       | Dashboard                   | First thing admins see           |
| P0       | Organization Management     | Foundation for everything        |
| P0       | User Management + Roles     | Core admin function              |
| P1       | Invoice & Payment Tracking  | Revenue visibility               |
| P1       | User Activity Monitoring    | Security & compliance            |
| P1       | Subscription/Billing Status | Ties orgs to revenue             |
| P2       | Audit Trail                 | Admin accountability             |
| P2       | Notification Center         | Proactive alerting               |
| P2       | Reports & Export            | Data extraction                  |

So in short — I'd add Dashboard, Role Management, Admin Auth, Audit Trail, Subscription Status, and Basic Reports to round out your MVP. That gives you a portal that's actually usable day one.

Want me to start building out a spec or design doc for this admin portal?Good question — let me think through what a solid MVP Admin Portal needs beyond your four items.

Your four core features are a strong start. Here's what I'd recommend adding for a well-rounded MVP:

## Your Core 4 (solid picks)

1. User Activity Monitoring & Logging
2. User Management (per organization)
3. Organization Management
4. Invoice Creation, Sending & Payment Tracking

## Recommended Additions for MVP

5. **Dashboard / Overview** — A landing page with key metrics at a glance (total orgs, active users, revenue summary, recent activity). Without this, admins have no quick pulse on the system.

6. **Role & Permission Management** — You already have `roles TEXT[]` on users. Admins need a way to assign/revoke roles and define what each role can access. This is tightly coupled with User Management.

7. **Authentication & Admin Login** — Separate admin auth flow (or at minimum, admin role gate). You need to protect the portal itself.

8. **Audit Trail / System Logs** — Different from user activity monitoring. This tracks admin actions — who changed what, when. Critical for compliance and debugging.

9. **Notification Center** — Email/in-app notifications for key events: payment received, trial expiring, user locked out, invoice overdue. Even a simple version adds a lot of value.

10. **Organization Subscription/Billing Status** — You have `paid_until`, `on_trial`, `trial_expiry` on organizations. Admins need visibility into which orgs are on trial, expiring soon, or overdue. Ties directly into your invoice/payment tracking.

11. **Basic Reports & Export** — CSV/PDF export for user lists, org lists, payment history. Admins always need to pull data for stakeholders.

## Nice-to-Have (Post-MVP)

- Email template management
- Bulk user operations (activate/deactivate)
- System health monitoring
- Feature flags / org-level config
- Support ticket integration

## Suggested MVP Priority Order

| Priority | Feature                     | Why                              |
| -------- | --------------------------- | -------------------------------- |
| P0       | Admin Auth & Login          | Can't access anything without it |
| P0       | Dashboard                   | First thing admins see           |
| P0       | Organization Management     | Foundation for everything        |
| P0       | User Management + Roles     | Core admin function              |
| P1       | Invoice & Payment Tracking  | Revenue visibility               |
| P1       | User Activity Monitoring    | Security & compliance            |
| P1       | Subscription/Billing Status | Ties orgs to revenue             |
| P2       | Audit Trail                 | Admin accountability             |
| P2       | Notification Center         | Proactive alerting               |
| P2       | Reports & Export            | Data extraction                  |

So in short — I'd add Dashboard, Role Management, Admin Auth, Audit Trail, Subscription Status, and Basic Reports to round out your MVP. That gives you a portal that's actually usable day one.

Want me to start building out a spec or design doc for this admin portal?Good question — let me think through what a solid MVP Admin Portal needs beyond your four items.

Your four core features are a strong start. Here's what I'd recommend adding for a well-rounded MVP:

## Your Core 4 (solid picks)

1. User Activity Monitoring & Logging
2. User Management (per organization)
3. Organization Management
4. Invoice Creation, Sending & Payment Tracking

## Recommended Additions for MVP

5. **Dashboard / Overview** — A landing page with key metrics at a glance (total orgs, active users, revenue summary, recent activity). Without this, admins have no quick pulse on the system.

6. **Role & Permission Management** — You already have `roles TEXT[]` on users. Admins need a way to assign/revoke roles and define what each role can access. This is tightly coupled with User Management.

7. **Authentication & Admin Login** — Separate admin auth flow (or at minimum, admin role gate). You need to protect the portal itself.

8. **Audit Trail / System Logs** — Different from user activity monitoring. This tracks admin actions — who changed what, when. Critical for compliance and debugging.

9. **Notification Center** — Email/in-app notifications for key events: payment received, trial expiring, user locked out, invoice overdue. Even a simple version adds a lot of value.

10. **Organization Subscription/Billing Status** — You have `paid_until`, `on_trial`, `trial_expiry` on organizations. Admins need visibility into which orgs are on trial, expiring soon, or overdue. Ties directly into your invoice/payment tracking.

11. **Basic Reports & Export** — CSV/PDF export for user lists, org lists, payment history. Admins always need to pull data for stakeholders.

## Nice-to-Have (Post-MVP)

- Email template management
- Bulk user operations (activate/deactivate)
- System health monitoring
- Feature flags / org-level config
- Support ticket integration

## Suggested MVP Priority Order

| Priority | Feature                     | Why                              |
| -------- | --------------------------- | -------------------------------- |
| P0       | Admin Auth & Login          | Can't access anything without it |
| P0       | Dashboard                   | First thing admins see           |
| P0       | Organization Management     | Foundation for everything        |
| P0       | User Management + Roles     | Core admin function              |
| P1       | Invoice & Payment Tracking  | Revenue visibility               |
| P1       | User Activity Monitoring    | Security & compliance            |
| P1       | Subscription/Billing Status | Ties orgs to revenue             |
| P2       | Audit Trail                 | Admin accountability             |
| P2       | Notification Center         | Proactive alerting               |
| P2       | Reports & Export            | Data extraction                  |

So in short — I'd add Dashboard, Role Management, Admin Auth, Audit Trail, Subscription Status, and Basic Reports to round out your MVP. That gives you a portal that's actually usable day one.

Want me to start building out a spec or design doc for this admin portal?Good question — let me think through what a solid MVP Admin Portal needs beyond your four items.

Your four core features are a strong start. Here's what I'd recommend adding for a well-rounded MVP:

## Your Core 4 (solid picks)

1. User Activity Monitoring & Logging
2. User Management (per organization)
3. Organization Management
4. Invoice Creation, Sending & Payment Tracking

## Recommended Additions for MVP

5. **Dashboard / Overview** — A landing page with key metrics at a glance (total orgs, active users, revenue summary, recent activity). Without this, admins have no quick pulse on the system.

6. **Role & Permission Management** — You already have `roles TEXT[]` on users. Admins need a way to assign/revoke roles and define what each role can access. This is tightly coupled with User Management.

7. **Authentication & Admin Login** — Separate admin auth flow (or at minimum, admin role gate). You need to protect the portal itself.

8. **Audit Trail / System Logs** — Different from user activity monitoring. This tracks admin actions — who changed what, when. Critical for compliance and debugging.

9. **Notification Center** — Email/in-app notifications for key events: payment received, trial expiring, user locked out, invoice overdue. Even a simple version adds a lot of value.

10. **Organization Subscription/Billing Status** — You have `paid_until`, `on_trial`, `trial_expiry` on organizations. Admins need visibility into which orgs are on trial, expiring soon, or overdue. Ties directly into your invoice/payment tracking.

11. **Basic Reports & Export** — CSV/PDF export for user lists, org lists, payment history. Admins always need to pull data for stakeholders.

## Nice-to-Have (Post-MVP)

- Email template management
- Bulk user operations (activate/deactivate)
- System health monitoring
- Feature flags / org-level config
- Support ticket integration

## Suggested MVP Priority Order

| Priority | Feature                     | Why                              |
| -------- | --------------------------- | -------------------------------- |
| P0       | Admin Auth & Login          | Can't access anything without it |
| P0       | Dashboard                   | First thing admins see           |
| P0       | Organization Management     | Foundation for everything        |
| P0       | User Management + Roles     | Core admin function              |
| P1       | Invoice & Payment Tracking  | Revenue visibility               |
| P1       | User Activity Monitoring    | Security & compliance            |
| P1       | Subscription/Billing Status | Ties orgs to revenue             |
| P2       | Audit Trail                 | Admin accountability             |
| P2       | Notification Center         | Proactive alerting               |
| P2       | Reports & Export            | Data extraction                  |

So in short — I'd add Dashboard, Role Management, Admin Auth, Audit Trail, Subscription Status, and Basic Reports to round out your MVP. That gives you a portal that's actually usable day one.

Want me to start building out a spec or design doc for this admin portal?

- **Admin_Portal**: The super-admin web application for managing all organizations, users, billing, and system operations.
- **System_Admin**: A user with `user_type = "system_admin"` who has cross-organization access and bypasses per-resource permission checks.
- **Org_Admin**: A user with the `org_admin` role scoped to a single organization.
- **Identity_Service**: The existing microservice that handles authentication (login, register, logout), token issuance, and the `/me` endpoint returning `organization_id` and `permissions`.
- **Core_Service**: The existing FastAPI service hosting all ERP endpoints (invoices, payments, items, etc.) at `localhost:8001`.
- **Dashboard_API**: The set of admin-portal endpoints that aggregate cross-organization metrics for the admin dashboard.
- **Audit_Log**: A record of an admin action (who changed what, when) stored in the `admin_audit_logs` table.
- **Activity_Log**: A record of a user action (login, page view, data change) stored in the `user_activity_logs` table.
- **Notification**: An in-app or email alert triggered by a system event (payment received, trial expiring, invoice overdue).
- **Steering_Document**: A markdown file in `.kiro/steering/` that provides the frontend team with API endpoints, TypeScript types, service layer, React hooks, component examples, error handling, and a testing checklist for a specific feature.
- **Organization**: A tenant entity in the `organizations` table, identified by `id`, with fields for `name`, `short_code`, `status`, `paid_until`, `on_trial`, `trial_expiry`, `timezone`.
- **User**: An entity in the `users` table, scoped to an organization via `tenant_id`, with `email`, `mobile`, `roles TEXT[]`, `is_active`, `password_hash`.
- **Invoice**: A billing document in the `invoices` table with `invoice_type`, `status`, `grand_total`, `outstanding_amount`.
- **Payment**: A financial transaction in the `payments` table with `payment_type`, `amount`, `status`, `payment_method`.
- **Communication_Log**: A record in the `communication_logs` table tracking emails/messages sent, with `doc_type`, `channel`, `status`, `recipient`.

## Requirements

### Requirement 1: Admin Authentication and Role Gate

**User Story:** As a system administrator, I want a separate admin authentication flow with role-based access gating, so that only authorized administrators can access the admin portal.Good question — let me think through what a solid MVP Admin Portal needs beyond your four items.

Your four core features are a strong start. Here's what I'd recommend adding for a well-rounded MVP:

## Your Core 4 (solid picks)

1. User Activity Monitoring & Logging
2. User Management (per organization)
3. Organization Management
4. Invoice Creation, Sending & Payment Tracking

## Recommended Additions for MVP

5. **Dashboard / Overview** — A landing page with key metrics at a glance (total orgs, active users, revenue summary, recent activity). Without this, admins have no quick pulse on the system.

6. **Role & Permission Management** — You already have `roles TEXT[]` on users. Admins need a way to assign/revoke roles and define what each role can access. This is tightly coupled with User Management.

7. **Authentication & Admin Login** — Separate admin auth flow (or at minimum, admin role gate). You need to protect the portal itself.

8. **Audit Trail / System Logs** — Different from user activity monitoring. This tracks admin actions — who changed what, when. Critical for compliance and debugging.

9. **Notification Center** — Email/in-app notifications for key events: payment received, trial expiring, user locked out, invoice overdue. Even a simple version adds a lot of value.

10. **Organization Subscription/Billing Status** — You have `paid_until`, `on_trial`, `trial_expiry` on organizations. Admins need visibility into which orgs are on trial, expiring soon, or overdue. Ties directly into your invoice/payment tracking.

11. **Basic Reports & Export** — CSV/PDF export for user lists, org lists, payment history. Admins always need to pull data for stakeholders.

## Nice-to-Have (Post-MVP)

- Email template management
- Bulk user operations (activate/deactivate)
- System health monitoring
- Feature flags / org-level config
- Support ticket integration

## Suggested MVP Priority Order

| Priority | Feature                     | Why                              |
| -------- | --------------------------- | -------------------------------- |
| P0       | Admin Auth & Login          | Can't access anything without it |
| P0       | Dashboard                   | First thing admins see           |
| P0       | Organization Management     | Foundation for everything        |
| P0       | User Management + Roles     | Core admin function              |
| P1       | Invoice & Payment Tracking  | Revenue visibility               |
| P1       | User Activity Monitoring    | Security & compliance            |
| P1       | Subscription/Billing Status | Ties orgs to revenue             |
| P2       | Audit Trail                 | Admin accountability             |
| P2       | Notification Center         | Proactive alerting               |
| P2       | Reports & Export            | Data extraction                  |

So in short — I'd add Dashboard, Role Management, Admin Auth, Audit Trail, Subscription Status, and Basic Reports to round out your MVP. That gives you a portal that's actually usable day one.

Want me to start building out a spec or design doc for this admin portal?

#### Acceptance Criteria

1. WHEN a user submits valid credentials to the admin login endpoint, THE Identity_Service SHALL return a JWT access token containing `user_type = "system_admin"` in the payload.
2. WHEN a user submits invalid credentials to the admin login endpoint, THE Identity_Service SHALL return a 401 HTTP status with an error message.
3. WHEN a request arrives at any Admin_Portal endpoint without a valid Bearer token, THE Core_Service SHALL return a 401 HTTP status.
4. WHEN a request arrives at any Admin_Portal endpoint with a valid token but `user_type` is not `system_admin`, THE Core_Service SHALL return a 403 HTTP status with the message "Admin access required".
5. THE Core_Service SHALL provide a `require_admin` dependency that validates `user_type == "system_admin"` on the current user before granting access to admin endpoints.
6. WHEN an admin user calls the `/admin/me` endpoint, THE Core_Service SHALL return the admin user's profile including `id`, `email`, `user_type`, `organization_id`, and `permissions`.
7. THE Core_Service SHALL mount all admin-portal endpoints under the `/api/v1/admin/` URL prefix, separate from existing org-scoped endpoints.

---

### Requirement 2: Admin Dashboard and Overview Metrics

**User Story:** As a system administrator, I want a dashboard landing page with key platform metrics, so that I can quickly assess the health and activity of the entire system.

#### Acceptance Criteria

1. WHEN an admin user requests the dashboard overview endpoint, THE Dashboard_API SHALL return the total count of organizations, the count of active organizations (status = "ACTIVE"), and the count of organizations on trial.
2. WHEN an admin user requests the dashboard overview endpoint, THE Dashboard_API SHALL return the total count of users across all organizations and the count of active users (`is_active = true`).
3. WHEN an admin user requests the dashboard overview endpoint, THE Dashboard_API SHALL return a revenue summary containing total invoiced amount (sum of `grand_total` for all invoices with status "paid"), total outstanding amount (sum of `outstanding_amount` for invoices with status in "pending", "partial", "overdue"), and total payments received (sum of `amount` for payments with status "completed").
4. WHEN an admin user requests the dashboard overview endpoint, THE Dashboard_API SHALL return the 10 most recent activity entries sorted by `created_at` descending.
5. WHEN an admin user requests the dashboard overview endpoint with a `date_from` and `date_to` query parameter, THE Dashboard_API SHALL filter revenue and activity metrics to the specified date range.
6. THE Dashboard_API SHALL respond to the overview endpoint within 2000 milliseconds for a dataset of up to 10,000 organizations.

---

### Requirement 3: Organization Management

**User Story:** As a system administrator, I want to create, read, update, and list organizations with their settings and subscription status, so that I can manage all tenants on the platform.

#### Acceptance Criteria

1. WHEN an admin user sends a POST request with organization data (name, short_code, industry, timezone, status), THE Core_Service SHALL create a new organization record and return the created organization with a 201 HTTP status.
2. WHEN an admin user sends a GET request to the organizations list endpoint, THE Core_Service SHALL return a paginated list of all organizations with fields: `id`, `name`, `short_code`, `status`, `on_trial`, `trial_expiry`, `paid_until`, `timezone`, `created_at`.
3. WHEN an admin user sends a GET request to the organizations list endpoint with a `search` query parameter, THE Core_Service SHALL filter organizations by `name` or `short_code` containing the search term (case-insensitive).
4. WHEN an admin user sends a GET request to the organizations list endpoint with a `status` query parameter, THE Core_Service SHALL filter organizations by the specified status value.
5. WHEN an admin user sends a GET request for a single organization by ID, THE Core_Service SHALL return the full organization record including all fields and a summary of user count, invoice count, and payment total for that organization.
6. WHEN an admin user sends a PATCH request with updated fields for an organization, THE Core_Service SHALL update only the provided fields and return the updated organization.
7. WHEN an admin user sends a PATCH request to change an organization's status to "SUSPENDED", THE Core_Service SHALL update the status and set all users in that organization to `is_active = false`.
8. IF an admin user sends a POST request with a `short_code` that already exists, THEN THE Core_Service SHALL return a 409 HTTP status with the message "Organization with this short_code already exists".
9. IF an admin user sends a GET request for an organization ID that does not exist, THEN THE Core_Service SHALL return a 404 HTTP status.

---

### Requirement 4: User Management and Roles

**User Story:** As a system administrator, I want to list, view, create, update, and manage users across all organizations with role assignment, so that I can control access and permissions for every user on the platform.

#### Acceptance Criteria

1. WHEN an admin user sends a GET request to the admin users list endpoint, THE Core_Service SHALL return a paginated list of all users across all organizations with fields: `id`, `email`, `mobile`, `roles`, `is_active`, `tenant_id`, `organization_name`, `created_at`.
2. WHEN an admin user sends a GET request to the admin users list endpoint with an `organization_id` query parameter, THE Core_Service SHALL filter users to only those belonging to the specified organization.
3. WHEN an admin user sends a GET request to the admin users list endpoint with a `search` query parameter, THE Core_Service SHALL filter users by `email` or `mobile` containing the search term (case-insensitive).
4. WHEN an admin user sends a GET request to the admin users list endpoint with an `is_active` query parameter, THE Core_Service SHALL filter users by their active status.
5. WHEN an admin user sends a GET request for a single user by ID, THE Core_Service SHALL return the full user record including `id`, `email`, `mobile`, `roles`, `is_active`, `tenant_id`, `organization_name`, `created_at`, `updated_at`.
6. WHEN an admin user sends a PATCH request to update a user's `roles` field, THE Core_Service SHALL replace the user's roles array with the provided values and return the updated user.
7. WHEN an admin user sends a PATCH request to set a user's `is_active` to false, THE Core_Service SHALL deactivate the user and return the updated user.
8. WHEN an admin user sends a PATCH request to set a user's `is_active` to true, THE Core_Service SHALL reactivate the user and return the updated user.
9. WHEN an admin user sends a POST request to create a new user with `email`, `organization_id`, `roles`, and `password`, THE Core_Service SHALL create the user in the specified organization and return the created user with a 201 HTTP status.
10. IF an admin user sends a POST request with an `email` that already exists, THEN THE Core_Service SHALL return a 409 HTTP status with the message "User with this email already exists".
11. IF an admin user sends a GET request for a user ID that does not exist, THEN THE Core_Service SHALL return a 404 HTTP status.
12. THE Core_Service SHALL support the following role values: `system_admin`, `org_admin`, `user`.

---

### Requirement 5: Invoice Management, Sending, and Payment Tracking

**User Story:** As a system administrator, I want to view, create, and send invoices across all organizations and track their payment status, so that I can manage billing operations platform-wide.

#### Acceptance Criteria

1. WHEN an admin user sends a GET request to the admin invoices list endpoint, THE Core_Service SHALL return a paginated list of all invoices across all organizations with fields: `id`, `organization_id`, `organization_name`, `invoice_no`, `invoice_type`, `party_id`, `party_type`, `status`, `grand_total`, `outstanding_amount`, `posting_date`, `due_date`.
2. WHEN an admin user sends a GET request to the admin invoices list endpoint with an `organization_id` query parameter, THE Core_Service SHALL filter invoices to only those belonging to the specified organization.
3. WHEN an admin user sends a GET request to the admin invoices list endpoint with a `status` query parameter, THE Core_Service SHALL filter invoices by the specified status value.
4. WHEN an admin user sends a GET request to the admin invoices list endpoint with `date_from` and `date_to` query parameters, THE Core_Service SHALL filter invoices by `posting_date` within the specified range.
5. WHEN an admin user sends a GET request for a single invoice by ID, THE Core_Service SHALL return the full invoice record including line items and associated payment history.
6. WHEN an admin user sends a POST request to create an invoice with `organization_id`, `invoice_type`, `party_id`, `party_type`, `line_items`, and `due_date`, THE Core_Service SHALL create the invoice in the specified organization and return it with a 201 HTTP status.
7. WHEN an admin user sends a POST request to the invoice send endpoint for a specific invoice, THE Core_Service SHALL send the invoice to the party's email via the Communication_Log system and update the invoice status to "pending".
8. WHEN an admin user sends a GET request to the admin payments list endpoint, THE Core_Service SHALL return a paginated list of all payments across all organizations with fields: `id`, `organization_id`, `organization_name`, `payment_no`, `payment_type`, `party_id`, `amount`, `status`, `payment_method`, `posting_date`.
9. WHEN an admin user sends a GET request to the admin payments list endpoint with an `organization_id` query parameter, THE Core_Service SHALL filter payments to only those belonging to the specified organization.
10. WHEN an admin user sends a GET request to the admin payments list endpoint with a `status` query parameter, THE Core_Service SHALL filter payments by the specified status value.

---

### Requirement 6: User Activity Monitoring and Logging

**User Story:** As a system administrator, I want to track user actions, login history, and security events, so that I can monitor platform usage and detect suspicious activity.

#### Acceptance Criteria

1. THE Core_Service SHALL store user activity records in the `user_activity_logs` table with fields: `id`, `user_id`, `organization_id`, `action` (login, logout, page_view, data_create, data_update, data_delete), `resource_type`, `resource_id`, `ip_address`, `user_agent`, `metadata` (JSONB), `created_at`.
2. WHEN a user successfully logs in via the Identity_Service, THE Core_Service SHALL create an Activity_Log entry with action "login", the user's IP address, and user agent.
3. WHEN a user fails to log in via the Identity_Service, THE Core_Service SHALL create an Activity_Log entry with action "login_failed", the provided email, IP address, and user agent.
4. WHEN an admin user sends a GET request to the activity logs endpoint, THE Core_Service SHALL return a paginated list of activity logs sorted by `created_at` descending.
5. WHEN an admin user sends a GET request to the activity logs endpoint with a `user_id` query parameter, THE Core_Service SHALL filter activity logs to only those for the specified user.
6. WHEN an admin user sends a GET request to the activity logs endpoint with an `organization_id` query parameter, THE Core_Service SHALL filter activity logs to only those for the specified organization.
7. WHEN an admin user sends a GET request to the activity logs endpoint with an `action` query parameter, THE Core_Service SHALL filter activity logs by the specified action type.
8. WHEN an admin user sends a GET request to the activity logs endpoint with `date_from` and `date_to` query parameters, THE Core_Service SHALL filter activity logs to the specified date range.
9. WHEN an admin user requests login history for a specific user, THE Core_Service SHALL return all Activity_Log entries with action "login" or "login_failed" for that user, sorted by `created_at` descending.

---

### Requirement 7: Organization Subscription and Billing Status

**User Story:** As a system administrator, I want to view trial status, paid_until dates, expiring organizations, and overdue billing across all tenants, so that I can proactively manage subscriptions and revenue.

#### Acceptance Criteria

1. WHEN an admin user sends a GET request to the subscription overview endpoint, THE Core_Service SHALL return counts of: organizations on trial, organizations with active paid subscriptions, organizations with expired trials, and organizations with overdue billing (paid_until < current date and on_trial = false).
2. WHEN an admin user sends a GET request to the expiring organizations endpoint with a `days_ahead` query parameter (default 30), THE Core_Service SHALL return a list of organizations whose `trial_expiry` or `paid_until` falls within the specified number of days from the current date.
3. WHEN an admin user sends a GET request to the overdue organizations endpoint, THE Core_Service SHALL return a list of organizations where `paid_until` is before the current date and `on_trial` is false, sorted by `paid_until` ascending.
4. WHEN an admin user sends a PATCH request to update an organization's `paid_until` date, THE Core_Service SHALL update the field and set `on_trial` to false.
5. WHEN an admin user sends a PATCH request to extend an organization's trial, THE Core_Service SHALL update `trial_expiry` to the specified date and set `on_trial` to true.
6. WHEN an admin user sends a GET request for a single organization's billing details, THE Core_Service SHALL return the organization's `on_trial`, `trial_expiry`, `paid_until`, total invoiced amount, total paid amount, and outstanding balance.

---

### Requirement 8: Audit Trail and System Logs

**User Story:** As a system administrator, I want to track all admin actions with a complete audit trail, so that I can maintain compliance and investigate changes.

#### Acceptance Criteria

1. THE Core_Service SHALL store admin audit records in the `admin_audit_logs` table with fields: `id`, `admin_user_id`, `action` (create, update, delete, suspend, activate, role_change), `target_type` (organization, user, invoice, payment, setting), `target_id`, `changes` (JSONB storing old and new values), `ip_address`, `created_at`.
2. WHEN an admin user creates, updates, or deletes an organization, THE Core_Service SHALL create an Audit_Log entry recording the admin user ID, action, target organization ID, and the changed field values.
3. WHEN an admin user changes a user's roles or active status, THE Core_Service SHALL create an Audit_Log entry recording the admin user ID, action "role_change" or "activate"/"deactivate", target user ID, and old and new values.
4. WHEN an admin user sends a GET request to the audit logs endpoint, THE Core_Service SHALL return a paginated list of audit log entries sorted by `created_at` descending.
5. WHEN an admin user sends a GET request to the audit logs endpoint with an `admin_user_id` query parameter, THE Core_Service SHALL filter audit logs to only those performed by the specified admin.
6. WHEN an admin user sends a GET request to the audit logs endpoint with a `target_type` query parameter, THE Core_Service SHALL filter audit logs by the specified target type.
7. WHEN an admin user sends a GET request to the audit logs endpoint with a `target_id` query parameter, THE Core_Service SHALL filter audit logs to only those affecting the specified target.
8. WHEN an admin user sends a GET request to the audit logs endpoint with `date_from` and `date_to` query parameters, THE Core_Service SHALL filter audit logs to the specified date range.
9. THE Core_Service SHALL retain audit log records for a minimum of 365 days.

---

### Requirement 9: Notification Center

**User Story:** As a system administrator, I want to receive in-app and email notifications for key system events, so that I can respond promptly to important changes.

#### Acceptance Criteria

1. THE Core_Service SHALL store notification records in the `admin_notifications` table with fields: `id`, `recipient_user_id`, `notification_type` (payment_received, trial_expiring, user_locked, invoice_overdue, org_suspended), `title`, `message`, `reference_type`, `reference_id`, `is_read`, `read_at`, `created_at`.
2. WHEN a payment with status "completed" is recorded, THE Core_Service SHALL create a Notification with type "payment_received" for all system_admin users.
3. WHEN an organization's `trial_expiry` is within 7 days of the current date, THE Core_Service SHALL create a Notification with type "trial_expiring" for all system_admin users.
4. WHEN a user's `is_active` is set to false (locked out), THE Core_Service SHALL create a Notification with type "user_locked" for all system_admin users.
5. WHEN an invoice's `due_date` passes and the invoice status is not "paid" or "cancelled", THE Core_Service SHALL create a Notification with type "invoice_overdue" for all system_admin users.
6. WHEN an admin user sends a GET request to the notifications endpoint, THE Core_Service SHALL return a paginated list of notifications for the requesting admin user, sorted by `created_at` descending.
7. WHEN an admin user sends a GET request to the notifications endpoint with `is_read=false`, THE Core_Service SHALL return only unread notifications.
8. WHEN an admin user sends a PATCH request to mark a notification as read, THE Core_Service SHALL set `is_read` to true and `read_at` to the current timestamp.
9. WHEN an admin user sends a POST request to mark all notifications as read, THE Core_Service SHALL update all unread notifications for that admin user.
10. WHEN an admin user sends a GET request to the unread notification count endpoint, THE Core_Service SHALL return the count of notifications where `is_read` is false for the requesting admin user.

---

### Requirement 10: Basic Reports and Data Export

**User Story:** As a system administrator, I want to export user lists, organization lists, and payment history as CSV or PDF files, so that I can generate reports for stakeholders and compliance.

#### Acceptance Criteria

1. WHEN an admin user sends a GET request to the organization export endpoint with `format=csv`, THE Core_Service SHALL return a CSV file containing all organizations with columns: name, short_code, status, on_trial, trial_expiry, paid_until, timezone, created_at.
2. WHEN an admin user sends a GET request to the user export endpoint with `format=csv`, THE Core_Service SHALL return a CSV file containing all users with columns: email, mobile, roles, is_active, organization_name, created_at.
3. WHEN an admin user sends a GET request to the payment export endpoint with `format=csv`, THE Core_Service SHALL return a CSV file containing all payments with columns: payment_no, organization_name, payment_type, party_id, amount, status, payment_method, posting_date.
4. WHEN an admin user sends a GET request to any export endpoint with an `organization_id` query parameter, THE Core_Service SHALL filter the exported data to only records belonging to the specified organization.
5. WHEN an admin user sends a GET request to any export endpoint with `date_from` and `date_to` query parameters, THE Core_Service SHALL filter the exported data to records within the specified date range.
6. WHEN an admin user sends a GET request to the organization export endpoint with `format=pdf`, THE Core_Service SHALL return a PDF document containing the organization list formatted as a table.
7. THE Core*Service SHALL set the `Content-Disposition` header to `attachment; filename="{report_name}*{date}.{format}"` on all export responses.
8. THE Core_Service SHALL limit export results to 50,000 rows per request to prevent memory exhaustion.

---

### Requirement 11: Frontend Steering Document Generation

**User Story:** As a frontend developer, I want a steering document for each admin portal feature, so that I can build the UI with clear API contracts, TypeScript types, and component patterns.

#### Acceptance Criteria

1. FOR EACH completed backend feature step (Requirements 1 through 10), THE implementation process SHALL produce a steering document at `.kiro/steering/frontend-admin-{feature-slug}.md`.
2. THE Steering_Document SHALL contain sections for: API endpoints with request/response examples, TypeScript type definitions, service layer implementation, React hook implementations, component examples, error handling patterns, and a testing checklist.
3. THE Steering_Document SHALL follow the same format as the existing steering document at `.kiro/steering/frontend-qr-product-settings-module.md`.
4. THE Steering_Document SHALL include the base URL (`http://localhost:8001/api/v1/admin`), authentication requirements (Bearer token), and permission requirements for each endpoint.

---

### Requirement 12 (Nice-to-Have): Email Template Management

**User Story:** As a system administrator, I want to manage email templates for different document types, so that I can customize the content of automated emails.

#### Acceptance Criteria

1. WHERE email template management is enabled, THE Core_Service SHALL provide CRUD endpoints for email templates with fields: `id`, `organization_id` (null for system-wide), `template_name`, `doc_type`, `subject_template`, `body_template` (HTML), `is_active`, `created_at`, `updated_at`.
2. WHERE email template management is enabled, WHEN an admin user creates a template, THE Core_Service SHALL validate that `subject_template` and `body_template` contain valid placeholder syntax (e.g., `{{invoice_no}}`, `{{customer_name}}`).
3. WHERE email template management is enabled, WHEN the communication system sends an email for a document, THE Core_Service SHALL use the matching active template for the document's `doc_type`, falling back to the system default template if no organization-specific template exists.

---

### Requirement 13 (Nice-to-Have): Bulk User Operations

**User Story:** As a system administrator, I want to activate or deactivate multiple users at once, so that I can efficiently manage user access in bulk.

#### Acceptance Criteria

1. WHERE bulk user operations are enabled, WHEN an admin user sends a POST request with a list of user IDs and action "deactivate", THE Core_Service SHALL set `is_active` to false for all specified users and return the count of updated users.
2. WHERE bulk user operations are enabled, WHEN an admin user sends a POST request with a list of user IDs and action "activate", THE Core_Service SHALL set `is_active` to true for all specified users and return the count of updated users.
3. WHERE bulk user operations are enabled, THE Core_Service SHALL limit the number of user IDs per bulk request to 100.
4. WHERE bulk user operations are enabled, THE Core_Service SHALL create an Audit_Log entry for each user affected by the bulk operation.

---

### Requirement 14 (Nice-to-Have): System Health Monitoring

**User Story:** As a system administrator, I want to view service health, database status, and API response times, so that I can monitor system reliability.

#### Acceptance Criteria

1. WHERE system health monitoring is enabled, WHEN an admin user requests the health endpoint, THE Core_Service SHALL return the status of: Core_Service (up/down), Identity_Service (up/down), database connectivity (connected/disconnected), and current timestamp.
2. WHERE system health monitoring is enabled, WHEN an admin user requests the health endpoint, THE Core_Service SHALL return the database connection pool status including active connections, idle connections, and pool size.
3. WHERE system health monitoring is enabled, WHEN an admin user requests the health endpoint, THE Core_Service SHALL return the average API response time for the last 60 minutes.

---

### Requirement 15 (Nice-to-Have): Feature Flags and Organization-Level Configuration

**User Story:** As a system administrator, I want to enable or disable features per organization, so that I can control feature rollout and manage organization-specific configurations.

#### Acceptance Criteria

1. WHERE feature flags are enabled, THE Core_Service SHALL store feature flag records in a `feature_flags` table with fields: `id`, `organization_id`, `feature_key`, `is_enabled`, `config` (JSONB), `created_at`, `updated_at`.
2. WHERE feature flags are enabled, WHEN an admin user sends a GET request for an organization's feature flags, THE Core_Service SHALL return all feature flags for that organization.
3. WHERE feature flags are enabled, WHEN an admin user sends a PUT request to toggle a feature flag, THE Core_Service SHALL update the `is_enabled` field and return the updated flag.
4. WHERE feature flags are enabled, THE Core_Service SHALL provide a dependency `check_feature_flag(feature_key)` that org-scoped endpoints can use to gate access based on the requesting user's organization feature flags.
