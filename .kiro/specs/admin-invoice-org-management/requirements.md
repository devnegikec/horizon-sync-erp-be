# Requirements Document

## Introduction

This feature adds an Invoice Management page to the admin portal (apps/admin) that allows system_admin users to view, filter, and manage customer invoices across all organizations. It includes overdue invoice detection with per-organization summaries, and the ability to suspend or restrict an organization's features when invoices are overdue. The implementation reuses existing shared UI components from @horizon-sync/ui and follows the same DataTable + stat cards + modal patterns established by the Users and Organizations pages.

## Glossary

- **Admin_Portal**: The standalone React application at apps/admin (port 4300) used by system_admin users to manage the platform
- **System_Admin**: A user with the system_admin role who has cross-organization access to manage invoices and organizations
- **Invoice_List_Page**: The admin portal page that displays a paginated table of all invoices across all organizations
- **Invoice_Detail_View**: A modal dialog that shows full invoice details including line items, party information, and organization context
- **Overdue_Summary**: A set of stat cards and visual indicators that highlight overdue invoice counts and outstanding amounts
- **Organization_Feature_Gate**: The mechanism by which a system_admin can change an organization's status to "suspended" to restrict access due to overdue invoices
- **InvoicesTable**: The shared reusable table component from @horizon-sync/ui that renders invoice rows with sorting and pagination
- **InvoiceDetailDialog**: The shared reusable dialog component from @horizon-sync/ui that renders full invoice details
- **InvoiceStatusBadge**: The shared reusable badge component from @horizon-sync/ui that renders color-coded invoice status labels
- **AdminInvoiceService**: The existing backend service that provides cross-organization invoice queries via /api/v1/admin/invoices
- **AdminOrganizationService**: The existing backend service that manages organization CRUD and status updates via /api/v1/admin/organizations
- **DataTable**: The reusable table component pattern with server-side pagination, column visibility, and sorting used across admin pages
- **SendInvoiceEmailDialog**: The shared reusable dialog component from @horizon-sync/ui that provides an email form (to, subject, body) with invoice summary display, validation, and an `onSend` callback
- **Payment_Reminder_Email**: An email sent by a system_admin to a customer reminding them to pay an overdue invoice, pre-populated with overdue invoice details
- **Days_Overdue**: The number of calendar days between the current date and the invoice due_date, calculated as current_date minus due_date

## Requirements

### Requirement 1: Invoice List Page with Cross-Organization View

**User Story:** As a system_admin, I want to view all invoices across all organizations in a single paginated table, so that I can monitor billing activity platform-wide.

#### Acceptance Criteria

1. WHEN the System_Admin navigates to the /invoices route, THE Admin_Portal SHALL render the Invoice_List_Page with a paginated DataTable of all invoices across all organizations
2. THE Invoice_List_Page SHALL display each invoice row with the following columns: invoice number, organization name, party name, invoice type, posting date, due date, status, grand total, and outstanding amount
3. THE Invoice_List_Page SHALL use the shared InvoicesTable component from @horizon-sync/ui, extended with an organization name column for cross-org context
4. THE Invoice_List_Page SHALL support server-side pagination with a default page size of 20 items, consistent with the Users and Organizations pages

### Requirement 2: Invoice Filtering

**User Story:** As a system_admin, I want to filter invoices by organization, status, and date range, so that I can quickly find specific invoices.

#### Acceptance Criteria

1. THE Invoice_List_Page SHALL provide a search input that filters invoices by invoice number or party name
2. THE Invoice_List_Page SHALL provide an organization dropdown filter that limits results to a single selected organization
3. THE Invoice_List_Page SHALL provide a status dropdown filter with options: All, Draft, Pending, Paid, Partial, Overdue, Cancelled
4. THE Invoice_List_Page SHALL provide date range inputs (from/to) that filter invoices by posting date
5. WHEN any filter value changes, THE Invoice_List_Page SHALL reset pagination to page 1 and fetch filtered results from the AdminInvoiceService endpoint

### Requirement 3: Invoice Detail View

**User Story:** As a system_admin, I want to view full invoice details including line items and organization context, so that I can review billing information.

#### Acceptance Criteria

1. WHEN the System_Admin clicks "View" on an invoice row, THE Admin_Portal SHALL open the Invoice_Detail_View modal displaying the full invoice with line items, party details, and amounts
2. THE Invoice_Detail_View SHALL reuse the shared InvoiceDetailDialog component from @horizon-sync/ui
3. THE Invoice_Detail_View SHALL display the organization name and organization ID as additional context above the invoice details
4. THE Invoice_Detail_View SHALL display the InvoiceStatusBadge component to show the current invoice status with color coding

### Requirement 4: Overdue Invoice Summary Statistics

**User Story:** As a system_admin, I want to see summary statistics highlighting overdue invoices, so that I can quickly assess outstanding billing issues.

#### Acceptance Criteria

1. THE Invoice_List_Page SHALL display stat cards above the DataTable showing: Total Invoices, Overdue Invoices, Total Outstanding Amount, and Total Overdue Amount
2. THE Invoice_List_Page SHALL fetch stat card values from the AdminInvoiceService backend endpoint
3. WHEN an invoice has a due_date earlier than the current date and a status of "pending" or "partial", THE InvoiceStatusBadge SHALL render with an "overdue" visual indicator
4. THE stat cards SHALL follow the same gradient icon styling pattern used on the Dashboard, Users, and Organizations pages

### Requirement 5: Organization Overdue Invoice Summary

**User Story:** As a system_admin, I want to see a per-organization breakdown of overdue invoices, so that I can identify which organizations have billing issues.

#### Acceptance Criteria

1. WHEN the System_Admin filters invoices by a specific organization, THE Invoice_List_Page SHALL display an organization billing summary card showing: organization name, total invoices, overdue count, and total outstanding amount for that organization
2. THE organization billing summary card SHALL include a direct link to the Organization_Feature_Gate action for that organization
3. WHEN no organization filter is selected, THE Invoice_List_Page SHALL hide the organization billing summary card

### Requirement 6: Organization Feature Gating for Overdue Invoices

**User Story:** As a system_admin, I want to suspend an organization's access when invoices are overdue, so that I can enforce payment compliance.

#### Acceptance Criteria

1. WHEN the System_Admin views an organization with overdue invoices, THE Invoice_List_Page SHALL display a "Suspend Organization" action button in the organization billing summary card
2. WHEN the System_Admin clicks "Suspend Organization", THE Admin_Portal SHALL open the existing ConfirmationDialog component from @horizon-sync/ui (the same component used for "Mark as Paid" confirmation in the inventory app's InvoiceManagement) showing the organization name, number of overdue invoices, and total overdue amount
3. THE ConfirmationDialog SHALL display a title of "Suspend Organization", a description with the organization name and overdue details, a "Suspend" confirm button label, and a "Cancel" cancel button label
4. WHEN the System_Admin confirms the suspension, THE Admin_Portal SHALL call the AdminOrganizationService update endpoint to set the organization status to "suspended"
5. IF the AdminOrganizationService update call fails, THEN THE Admin_Portal SHALL display an error toast notification with the failure reason
6. WHEN the organization status is successfully updated to "suspended", THE Admin_Portal SHALL display a success toast notification and refresh the invoice list
7. WHEN the System_Admin views a suspended organization's invoices, THE Invoice_List_Page SHALL display a "Reactivate Organization" action button instead of "Suspend Organization"
8. WHEN the System_Admin clicks "Reactivate Organization", THE Admin_Portal SHALL open the same ConfirmationDialog with title "Reactivate Organization" and a "Reactivate" confirm button label
9. WHEN the System_Admin confirms reactivation, THE Admin_Portal SHALL call the AdminOrganizationService update endpoint to set the organization status to "active"

### Requirement 7: Backend Overdue Invoice Statistics Endpoint

**User Story:** As a system_admin, I want the backend to provide aggregated overdue invoice statistics, so that the frontend can display accurate summary data.

#### Acceptance Criteria

1. THE AdminInvoiceService SHALL expose a statistics endpoint at GET /api/v1/admin/invoices/stats that returns: total invoice count, overdue invoice count, total outstanding amount, and total overdue amount
2. WHEN an organization_id query parameter is provided, THE AdminInvoiceService SHALL scope the statistics to that single organization
3. THE AdminInvoiceService SHALL calculate overdue status by comparing the invoice due_date to the current date for invoices with status "pending" or "partial"

### Requirement 8: UI Consistency with Existing Admin Pages

**User Story:** As a system_admin, I want the invoice management page to look and feel consistent with the existing admin pages, so that the experience is cohesive.

#### Acceptance Criteria

1. THE Invoice_List_Page SHALL use the same page layout structure as the Users and Organizations pages: header with title/description, action buttons, stat cards, filter bar, and DataTable
2. THE Invoice_List_Page SHALL use gradient-styled primary action buttons matching the existing "from-[#3058EE] to-[#7D97F6]" pattern
3. THE Invoice_List_Page SHALL use the same Card, CardContent, SearchInput, Select, and DataTableViewOptions components from @horizon-sync/ui
4. THE Invoice_List_Page SHALL include the same fade-in slide-in-from-bottom animation on page load as the existing admin pages

### Requirement 9: Overdue Payment Reminder Email

**User Story:** As a system_admin, I want to send payment reminder emails to customers with overdue invoices, so that I can prompt them to settle outstanding balances.

#### Acceptance Criteria

1. WHEN the System_Admin selects one or more overdue invoices from the Invoice_List_Page, THE Admin_Portal SHALL enable a "Send Reminder" action button
2. WHEN the System_Admin clicks "Send Reminder" for a single overdue invoice, THE Admin_Portal SHALL open the SendInvoiceEmailDialog from @horizon-sync/ui with the email body pre-populated with the invoice number, grand total amount, due date, and Days_Overdue
3. THE SendInvoiceEmailDialog SHALL pre-populate the subject field with "Payment Reminder: Invoice {invoice_no} — Overdue by {days_overdue} days"
4. THE SendInvoiceEmailDialog SHALL pre-populate the email body with a reminder message containing the invoice number, currency and grand total, original due date, Days_Overdue, and outstanding amount
5. WHEN the System_Admin confirms sending the reminder, THE Admin_Portal SHALL call the backend endpoint POST /api/v1/admin/invoices/{id}/send-reminder with the email form data (to, subject, body)
6. WHEN the backend receives a send-reminder request, THE AdminInvoiceService SHALL validate that the invoice exists and has a status of "pending" or "partial" with a due_date earlier than the current date
7. IF the invoice is not overdue, THEN THE AdminInvoiceService SHALL return a 400 error with the message "Invoice is not overdue"
8. WHEN the reminder email is sent successfully, THE Admin_Portal SHALL display a success toast notification and close the SendInvoiceEmailDialog
9. IF the send-reminder request fails, THEN THE Admin_Portal SHALL display an error toast notification with the failure reason
10. WHEN the System_Admin selects multiple overdue invoices and clicks "Send Reminder", THE Admin_Portal SHALL send reminder emails sequentially for each selected invoice using the same pre-populated template per invoice
