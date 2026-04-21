# Implementation Plan: Admin Invoice & Organization Management

## Overview

Add an Invoice Management page to the admin portal with cross-organization invoice viewing, filtering, overdue statistics, per-org billing summaries, and organization suspend/reactivate functionality. The implementation reuses shared UI components from `@horizon-sync/ui` and follows the established admin page patterns (UsersPage, OrganizationsPage). Backend work is limited to a single new stats endpoint on the existing admin invoices router.

## Tasks

- [x] 1. Backend: Add invoice stats endpoint and schema
  - [x] 1.1 Add `AdminInvoiceStatsResponse` schema to `core-service/app/schemas/admin_invoice.py`
    - Add Pydantic model with fields: `total_invoices` (int), `overdue_invoices` (int), `total_outstanding` (Decimal), `total_overdue_amount` (Decimal)
    - _Requirements: 7.1_

  - [x] 1.2 Add `get_stats()` method to `AdminInvoiceService` in `core-service/app/services/admin_invoice_service.py`
    - SQL aggregation: COUNT all invoices, COUNT overdue (due_date < now AND status IN ('pending','partial')), SUM outstanding_amount total, SUM outstanding_amount for overdue only
    - Accept optional `organization_id` parameter to scope stats to a single org
    - Return zero counts when no invoices match (not 404)
    - _Requirements: 7.1, 7.2, 7.3_

  - [x] 1.3 Add `GET /stats` endpoint to `core-service/app/api/v1/endpoints/admin/invoices.py`
    - Route: `@router.get("/stats")` with `organization_id: UUID | None = Query(None)` parameter
    - Requires `require_admin` dependency
    - Must be placed BEFORE the `/{invoice_id}` route to avoid path conflicts
    - _Requirements: 7.1, 7.2_

  - [ ]* 1.4 Write property tests for stats endpoint (Hypothesis)
    - **Property 11: Stats endpoint returns correct aggregates**
    - **Property 12: Stats endpoint respects organization scoping**
    - **Property 7 (backend): Overdue classification logic**
    - **Validates: Requirements 7.1, 7.2, 7.3**

- [x] 2. Frontend: Add invoice types and service layer
  - [x] 2.1 Create `apps/admin/src/app/types/invoice.types.ts`
    - Define `AdminInvoiceListItem`, `AdminInvoiceListResponse`, `AdminInvoiceFilters`, `AdminInvoiceStatsResponse`, `AdminInvoiceDetailResponse` interfaces
    - Re-export `Invoice` type from `@horizon-sync/ui` for detail view
    - _Requirements: 1.2, 7.1_

  - [x] 2.2 Create `apps/admin/src/app/services/admin-invoice.service.ts`
    - Follow the same pattern as `admin-organization.service.ts` (static class with `request<T>` helper, `useUserStore` for auth, `environment.apiCoreUrl` for base URL)
    - Methods: `list(filters)`, `getById(id)`, `getStats(organizationId?)`
    - Build query params from `AdminInvoiceFilters` for the list endpoint
    - _Requirements: 1.1, 2.1, 2.2, 2.3, 2.4, 3.1, 4.2, 7.1_

  - [x] 2.3 Create React Query hooks in `apps/admin/src/app/hooks/`
    - `useInvoices.ts` — wraps `AdminInvoiceService.list(filters)` with queryKey `['admin-invoices', filters]`
    - `useInvoiceStats.ts` — wraps `AdminInvoiceService.getStats(orgId)` with queryKey `['admin-invoice-stats', orgId]`
    - `useInvoice.ts` — wraps `AdminInvoiceService.getById(id)` with queryKey `['admin-invoice', id]`, enabled only when id is truthy
    - Follow the same pattern as `useOrganizations.ts`
    - _Requirements: 1.1, 4.2_

- [x] 3. Frontend: Build InvoicesPage with stat cards, filters, and table
  - [x] 3.1 Create `apps/admin/src/app/pages/InvoicesPage.tsx`
    - Follow the same layout structure as `UsersPage.tsx` and `OrganizationsPage.tsx`: header → stat cards → filters → DataTable
    - Page wrapper with `animate-in fade-in slide-in-from-bottom-4 duration-500`
    - Header section with title "Invoices", description, and gradient-styled refresh button (`from-[#3058EE] to-[#7D97F6]`)
    - _Requirements: 1.1, 8.1, 8.2, 8.4_

  - [x] 3.2 Implement stat cards section in InvoicesPage
    - Four stat cards: Total Invoices (FileText icon, slate bg), Overdue Invoices (AlertTriangle icon, red bg), Total Outstanding (DollarSign icon, amber bg), Total Overdue Amount (DollarSign icon, red bg)
    - Use the same `StatCard` component pattern from UsersPage
    - Data from `useInvoiceStats` hook; show "—" on fetch failure
    - _Requirements: 4.1, 4.2, 4.4, 8.1_

  - [x] 3.3 Implement filter bar in InvoicesPage
    - Search input filtering by invoice number or party name (using `SearchInput` from `@horizon-sync/ui`)
    - Organization dropdown populated from `useOrganizations()` hook — searchable by name
    - Status dropdown with options: All, Draft, Pending, Paid, Partial, Overdue, Cancelled (using `Select` from `@horizon-sync/ui`)
    - Date range inputs (from/to) for posting date filtering
    - `DataTableViewOptions` for column visibility
    - All filter changes reset pagination to page 1
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 8.3_

  - [x] 3.4 Integrate shared `InvoicesTable` from `@horizon-sync/ui` with organization name column
    - Reuse `InvoicesTable` component, extend with an `organization_name` column for cross-org context
    - Wire `onView` to open `InvoiceDetailDialog`, pass `serverPagination` config with page size 20
    - Map `AdminInvoiceListItem` to the `Invoice` type expected by InvoicesTable
    - _Requirements: 1.2, 1.3, 1.4, 3.1_

  - [x] 3.5 Integrate shared `InvoiceDetailDialog` from `@horizon-sync/ui`
    - Reuse `InvoiceDetailDialog` component for invoice detail modal
    - Add organization name and organization ID display above the invoice content
    - Show `InvoiceStatusBadge` for current status with color coding
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

  - [ ]* 3.6 Write property tests for filter and pagination behavior
    - **Property 5: Filter change resets pagination**
    - **Property 7 (frontend): Overdue classification in status badge**
    - **Validates: Requirements 2.5, 4.3**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Frontend: Organization billing summary and suspend/reactivate
  - [x] 5.1 Implement OrgBillingSummaryCard in InvoicesPage
    - Conditionally rendered when an organization filter is selected
    - Display: organization name, total invoices, overdue count, total outstanding amount (from org-scoped stats)
    - Hidden when no organization filter is selected
    - _Requirements: 5.1, 5.3_

  - [x] 5.2 Implement suspend/reactivate actions with ConfirmationDialog
    - Show "Suspend Organization" button when org status is active and has overdue invoices; show "Reactivate Organization" when org status is suspended
    - Reuse `ConfirmationDialog` from `@horizon-sync/ui` (same as "Mark as Paid" in InvoiceManagement.tsx)
    - Suspend dialog: title "Suspend Organization", description with org name + overdue count + overdue amount, confirmLabel "Suspend", cancelLabel "Cancel"
    - Reactivate dialog: title "Reactivate Organization", confirmLabel "Reactivate", cancelLabel "Cancel"
    - Use `onClick={() => doSave()}` pattern (not `<form onSubmit>`) inside the dialog
    - On confirm: PATCH `/api/v1/admin/organizations/{id}` with `{ status: "suspended" | "active" }` via `AdminOrganizationService.update()`
    - On success: show success toast, invalidate invoice queries to refresh list
    - On failure: show error toast with failure reason
    - _Requirements: 5.2, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9_

  - [ ]* 5.3 Write property tests for suspend/reactivate behavior
    - **Property 9: Action button reflects organization status**
    - **Property 10: Organization status toggle sends correct status**
    - **Validates: Requirements 6.1, 6.4, 6.7, 6.9**

- [x] 6. Frontend: Wire routing and navigation
  - [x] 6.1 Add `/invoices` route to `apps/admin/src/app/AppRoutes.tsx`
    - Import `InvoicesPage` and add `<Route path="/invoices" element={<InvoicesPage />} />` inside the `AdminGuard > DashboardLayout > Routes` block
    - _Requirements: 1.1_

  - [x] 6.2 Add "Invoices" nav item to `apps/admin/src/app/components/Sidebar.tsx`
    - Add `{ title: 'Invoices', href: '/invoices', icon: FileText }` to `mainNavItems` array (import `FileText` from lucide-react)
    - _Requirements: 1.1, 8.1_

- [x] 7. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Backend: Add send-reminder endpoint
  - [x] 8.1 Add `SendReminderRequest` schema to `core-service/app/schemas/admin_invoice.py`
    - Add Pydantic model with fields: `to` (EmailStr), `subject` (str), `body` (str)
    - _Requirements: 9.5_

  - [x] 8.2 Add `send_reminder()` method to `AdminInvoiceService` in `core-service/app/services/admin_invoice_service.py`
    - Fetch invoice by ID, validate it is overdue (due_date < today AND status IN ('pending', 'partial'))
    - Return 400 "Invoice is not overdue" if validation fails
    - Delegate to CommunicationService.send_email with the provided to, subject, body
    - Return `{ invoice_id, status: "reminder_sent", communication: result }`
    - _Requirements: 9.5, 9.6, 9.7_

  - [x] 8.3 Add `POST /{invoice_id}/send-reminder` endpoint to `core-service/app/api/v1/endpoints/admin/invoices.py`
    - Route: `@router.post("/{invoice_id}/send-reminder")` with `SendReminderRequest` body
    - Requires `require_admin` dependency
    - Delegates to `AdminInvoiceService.send_reminder()`
    - _Requirements: 9.5, 9.6_

  - [ ]* 8.4 Write property tests for send-reminder endpoint (Hypothesis)
    - **Property 14: Send reminder endpoint rejects non-overdue invoices**
    - **Validates: Requirements 9.6, 9.7**

- [x] 9. Frontend: Add overdue payment reminder email functionality
  - [x] 9.1 Add `sendReminder(invoiceId, emailData)` method to `AdminInvoiceService` in `apps/admin/src/app/services/admin-invoice.service.ts`
    - POST to `/api/v1/admin/invoices/{id}/send-reminder` with `{ to, subject, body }`
    - Follow the same `request<T>` helper pattern as existing methods
    - _Requirements: 9.5_

  - [x] 9.2 Add reminder email pre-population helper in `apps/admin/src/app/pages/InvoicesPage.tsx`
    - Create `buildReminderEmailData(invoice: AdminInvoiceListItem)` function
    - Calculate `daysOverdue = Math.floor((Date.now() - new Date(invoice.due_date).getTime()) / 86400000)`
    - Pre-populate subject: `"Payment Reminder: Invoice {invoice_no} — Overdue by {days_overdue} days"`
    - Pre-populate body with invoice number, currency, grand total, due date, days overdue, outstanding amount
    - _Requirements: 9.2, 9.3, 9.4_

  - [x] 9.3 Integrate `SendInvoiceEmailDialog` from `@horizon-sync/ui` into InvoicesPage
    - Import `SendInvoiceEmailDialog` from `@horizon-sync/ui`
    - Add `reminderInvoice` state to track the invoice being reminded
    - Add `sendingReminder` state for loading indicator
    - Wire `onSend` callback to call `AdminInvoiceService.sendReminder()`
    - On success: show success toast, close dialog
    - On failure: show error toast with failure reason
    - _Requirements: 9.2, 9.5, 9.8, 9.9_

  - [x] 9.4 Add "Send Reminder" action button to InvoicesPage for overdue invoices
    - Add checkbox selection column to InvoicesTable for multi-select
    - Show "Send Reminder" button in the action bar, enabled only when all selected invoices are overdue
    - Single invoice: open SendInvoiceEmailDialog with pre-populated fields from `buildReminderEmailData()`
    - Multiple invoices: send reminders sequentially for each selected invoice, showing progress
    - Use `onClick={() => doSave()}` pattern inside Radix Dialog (not `<form onSubmit>`)
    - _Requirements: 9.1, 9.10_

  - [ ]* 9.5 Write property tests for reminder email pre-population and button state
    - **Property 13: Reminder email pre-population contains overdue details**
    - **Property 15: Send reminder button enabled only for overdue selection**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4**

- [x] 10. Final checkpoint - Ensure all tests pass for Requirement 9
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Shared components (`InvoicesTable`, `InvoiceDetailDialog`, `ConfirmationDialog`, `InvoiceStatusBadge`) are reused from `@horizon-sync/ui` — no duplication
- The existing `AdminOrganizationService.update()` is reused for suspend/reactivate — no new backend endpoint needed for org status changes
- The existing `/api/v1/admin/invoices` list endpoint already supports org/status/date filtering — only the `/stats` endpoint is new
- Property tests validate universal correctness properties from the design document
- Tasks 8–9 implement Requirement 9 (overdue payment reminder emails) and reuse the existing `SendInvoiceEmailDialog` from `@horizon-sync/ui`
- The `POST /api/v1/admin/invoices/{id}/send-reminder` endpoint validates overdue status before sending, delegating to `CommunicationService.send_email`
