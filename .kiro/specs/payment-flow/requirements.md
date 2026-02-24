# Requirements Document: Payment Flow System

## Introduction

This document specifies requirements for a Payment Flow system in an ERP application that treats money movements as separate entities from invoices. The system implements a two-phase approach: Phase 1 focuses on manual payment capture (Cash, Check, Bank Transfer), while Phase 2 will integrate third-party payment gateways (Stripe, Razorpay). The core philosophy separates "What is Owed" (Invoices) from "Money Received" (Payment Entries), linked through reconciliation.

The system integrates with existing infrastructure including Chart of Accounts, Journal Entries, multi-tenancy, and audit logging.

## Glossary

- **Payment_Entry**: A record representing actual money received or paid, independent of invoices
- **Transaction_Ledger**: The journal entry system that records all money movements as debits and credits
- **Payment_Reference**: A link between a Payment_Entry and an Invoice showing how much of the payment was allocated
- **Reconciliation**: The process of matching Payment_Entries to Invoices through Payment_References
- **Payment_Mode**: The method of payment (Cash, Bank_Transfer, Check, Gateway)
- **Allocation**: The distribution of a payment amount across one or more invoices
- **Accounts_Receivable**: The Chart of Accounts account tracking money owed by customers
- **Accounts_Payable**: The Chart of Accounts account tracking money owed to suppliers
- **Default_Account**: A system-configured Chart of Accounts account used for specific transaction types
- **Organization**: A tenant in the multi-tenant system
- **Invoice_Status**: The payment state of an invoice (Unpaid, Partially_Paid, Paid, Overpaid)

## Requirements

### Requirement 1: Payment Entry Creation

**User Story:** As an accountant, I want to record manual payments received from customers or made to suppliers, so that I can track actual money movements independently of invoices.

#### Acceptance Criteria

1. THE Payment_Entry_Form SHALL capture customer_id, amount, payment_date, payment_mode, and reference_no
2. WHEN payment_mode is Check, THE Payment_Entry_Form SHALL require reference_no for the check number
3. WHEN payment_mode is Bank_Transfer, THE Payment_Entry_Form SHALL require reference_no for the bank UTR
4. THE Payment_Entry SHALL include organization_id for multi-tenancy isolation
5. THE Payment_Entry SHALL default status to Draft upon creation
6. THE Payment_Entry SHALL record source as "Manual" for manually captured payments
7. THE Payment_Entry SHALL validate that amount is greater than zero
8. THE Payment_Entry SHALL validate that payment_date is not in the future
9. THE Payment_Entry SHALL validate that customer_id exists and belongs to the same organization

### Requirement 2: Payment Allocation to Invoices

**User Story:** As an accountant, I want to allocate payment amounts to specific invoices, so that I can track which invoices have been paid and which remain outstanding.

#### Acceptance Criteria

1. WHEN a Payment_Entry is in Draft status, THE Invoice_Linker SHALL display all unpaid and partially_paid invoices for the selected customer
2. THE Invoice_Linker SHALL allow allocation of payment amounts to one or more invoices
3. THE Invoice_Linker SHALL validate that total allocated_amount does not exceed the Payment_Entry amount
4. THE Invoice_Linker SHALL validate that allocated_amount for each invoice does not exceed the invoice outstanding balance
5. THE Payment_Reference SHALL record payment_id, invoice_id, and allocated_amount for each allocation
6. THE Invoice_Linker SHALL allow partial allocation, leaving unallocated payment amounts
7. THE Invoice_Linker SHALL display invoice number, invoice date, total amount, and outstanding balance for each invoice
8. THE Invoice_Linker SHALL calculate and display remaining unallocated payment amount in real-time

### Requirement 3: Journal Entry Posting

**User Story:** As an accountant, I want payment entries to automatically post to the general ledger, so that financial reports reflect actual cash positions.

#### Acceptance Criteria

1. WHEN a Payment_Entry status changes to Confirmed, THE Transaction_Ledger SHALL create a journal entry
2. FOR customer payments, THE Transaction_Ledger SHALL debit the configured Bank or Cash account based on payment_mode
3. FOR customer payments, THE Transaction_Ledger SHALL credit the Accounts_Receivable account
4. FOR supplier payments, THE Transaction_Ledger SHALL debit the Accounts_Payable account
5. FOR supplier payments, THE Transaction_Ledger SHALL credit the configured Bank or Cash account based on payment_mode
6. THE Transaction_Ledger SHALL use the Default_Account configuration to determine which Chart of Accounts accounts to use
7. THE Transaction_Ledger SHALL include organization_id in all journal entries for multi-tenancy
8. THE Transaction_Ledger SHALL record payment_entry_id as a reference in the journal entry
9. THE Transaction_Ledger SHALL validate that debits equal credits before posting
10. IF journal entry posting fails, THEN THE Payment_Entry SHALL remain in Draft status and return an error message

### Requirement 4: Invoice Status Updates

**User Story:** As an accountant, I want invoice payment status to update automatically when payments are allocated, so that I can see which invoices require follow-up.

#### Acceptance Criteria

1. WHEN a Payment_Reference is created, THE Status_Updater SHALL recalculate the invoice payment status
2. WHEN total allocated payments equal invoice amount, THE Status_Updater SHALL set invoice status to Paid
3. WHEN total allocated payments are less than invoice amount and greater than zero, THE Status_Updater SHALL set invoice status to Partially_Paid
4. WHEN total allocated payments exceed invoice amount, THE Status_Updater SHALL set invoice status to Overpaid
5. WHEN all Payment_References for an invoice are deleted, THE Status_Updater SHALL set invoice status to Unpaid
6. THE Status_Updater SHALL update invoice status atomically with Payment_Reference creation
7. THE Status_Updater SHALL calculate outstanding balance as invoice amount minus total allocated payments

### Requirement 5: Payment Entry State Management

**User Story:** As an accountant, I want to control when payments are finalized, so that I can review and correct entries before they affect the general ledger.

#### Acceptance Criteria

1. THE Payment_Entry SHALL support three status values: Draft, Confirmed, Cancelled
2. WHEN status is Draft, THE Payment_Entry SHALL allow modifications to all fields
3. WHEN status is Draft, THE Payment_Entry SHALL allow deletion
4. WHEN status changes from Draft to Confirmed, THE Payment_Entry SHALL become immutable
5. WHEN status is Confirmed, THE Payment_Entry SHALL not allow modifications or deletion
6. WHEN status changes to Cancelled, THE Payment_Entry SHALL reverse any posted journal entries
7. WHEN status changes to Cancelled, THE Status_Updater SHALL recalculate affected invoice statuses
8. THE Payment_Entry SHALL validate that at least one Payment_Reference exists before allowing Confirmed status
9. IF a Payment_Entry has no allocations, THEN THE Payment_Entry SHALL remain in Draft status

### Requirement 6: Default Account Configuration

**User Story:** As a system administrator, I want to configure which Chart of Accounts accounts are used for payment transactions, so that payments post to the correct ledger accounts.

#### Acceptance Criteria

1. THE Default_Account_Configuration SHALL define a Cash account for cash payments
2. THE Default_Account_Configuration SHALL define a Bank account for bank transfer payments
3. THE Default_Account_Configuration SHALL define a Checks_Received account for check payments
4. THE Default_Account_Configuration SHALL define an Accounts_Receivable account for customer payments
5. THE Default_Account_Configuration SHALL define an Accounts_Payable account for supplier payments
6. THE Default_Account_Configuration SHALL be organization-specific for multi-tenancy
7. THE Payment_Entry_Service SHALL validate that required Default_Accounts are configured before allowing payment confirmation
8. IF required Default_Accounts are not configured, THEN THE Payment_Entry_Service SHALL return a descriptive error message

### Requirement 7: Payment Entry Audit Trail

**User Story:** As an auditor, I want to see a complete history of payment entry changes, so that I can verify financial controls and compliance.

#### Acceptance Criteria

1. WHEN a Payment_Entry is created, THE Audit_Logger SHALL record the creation event with user_id and timestamp
2. WHEN a Payment_Entry is modified, THE Audit_Logger SHALL record the modification event with changed fields
3. WHEN a Payment_Entry status changes, THE Audit_Logger SHALL record the status change event
4. WHEN a Payment_Reference is created or deleted, THE Audit_Logger SHALL record the allocation event
5. THE Audit_Logger SHALL record organization_id for all audit events
6. THE Audit_Trail SHALL be immutable and append-only
7. THE Audit_Trail SHALL include before and after values for modified fields

### Requirement 8: Payment Entry Search and Filtering

**User Story:** As an accountant, I want to search and filter payment entries, so that I can quickly find specific transactions.

#### Acceptance Criteria

1. THE Payment_Entry_List SHALL support filtering by customer_id
2. THE Payment_Entry_List SHALL support filtering by payment_date range
3. THE Payment_Entry_List SHALL support filtering by payment_mode
4. THE Payment_Entry_List SHALL support filtering by status
5. THE Payment_Entry_List SHALL support filtering by organization_id for multi-tenancy
6. THE Payment_Entry_List SHALL support text search on reference_no
7. THE Payment_Entry_List SHALL display payment amount, payment date, customer name, payment mode, and status
8. THE Payment_Entry_List SHALL support sorting by payment_date, amount, and customer name

### Requirement 9: Unallocated Payment Handling

**User Story:** As an accountant, I want to track payments that haven't been fully allocated to invoices, so that I can apply them to future invoices or issue refunds.

#### Acceptance Criteria

1. THE Payment_Entry SHALL calculate unallocated_amount as payment amount minus sum of allocated amounts
2. THE Payment_Entry_Detail SHALL display unallocated_amount prominently
3. THE Payment_Entry_List SHALL support filtering by unallocated_amount greater than zero
4. WHEN a Payment_Entry has unallocated_amount greater than zero, THE Invoice_Linker SHALL allow adding additional allocations
5. THE Payment_Entry SHALL allow confirmation even when unallocated_amount is greater than zero
6. THE Payment_Entry_Report SHALL list all payments with unallocated amounts

### Requirement 10: Multi-Currency Payment Support

**User Story:** As an accountant, I want to record payments in different currencies, so that I can handle international transactions.

#### Acceptance Criteria

1. THE Payment_Entry SHALL include a currency_code field
2. THE Payment_Entry SHALL default currency_code to the organization base currency
3. WHEN currency_code differs from invoice currency, THE Payment_Reference SHALL record the exchange_rate used
4. WHEN currency_code differs from invoice currency, THE Payment_Reference SHALL calculate allocated_amount in invoice currency
5. THE Transaction_Ledger SHALL post journal entries in the organization base currency
6. THE Transaction_Ledger SHALL use the Exchange_Rate_Service to convert payment amounts when needed
7. THE Payment_Entry_Detail SHALL display both payment currency and base currency amounts

### Requirement 11: Payment Gateway Integration Foundation

**User Story:** As a developer, I want a consistent interface for payment capture regardless of source, so that future gateway integrations require minimal changes to allocation and posting logic.

#### Acceptance Criteria

1. THE Payment_Entry SHALL include a source field indicating payment origin
2. THE Payment_Entry SHALL support source values: "Manual", "Stripe", "Razorpay"
3. WHEN source is "Stripe" or "Razorpay", THE Payment_Entry SHALL include a gateway_transaction_id field
4. THE Payment_Entry_Service SHALL provide a create_payment_entry method accepting source-agnostic parameters
5. THE Invoice_Linker SHALL operate identically regardless of Payment_Entry source
6. THE Transaction_Ledger SHALL post journal entries identically regardless of Payment_Entry source
7. THE Payment_Entry_Form SHALL disable manual editing when source is not "Manual"

### Requirement 12: Payment Reversal and Corrections

**User Story:** As an accountant, I want to reverse incorrect payments, so that I can correct mistakes without deleting historical records.

#### Acceptance Criteria

1. WHEN a Payment_Entry status is Confirmed, THE Payment_Entry SHALL allow status change to Cancelled
2. WHEN status changes to Cancelled, THE Transaction_Ledger SHALL create a reversing journal entry
3. THE reversing journal entry SHALL have opposite debit and credit entries from the original
4. WHEN status changes to Cancelled, THE Status_Updater SHALL remove all Payment_References
5. WHEN Payment_References are removed, THE Status_Updater SHALL recalculate affected invoice statuses
6. THE Payment_Entry SHALL record cancellation_reason when status changes to Cancelled
7. THE Payment_Entry SHALL record cancelled_by user_id and cancelled_at timestamp
8. THE Audit_Logger SHALL record the cancellation event with reason

### Requirement 13: Payment Entry Validation Rules

**User Story:** As an accountant, I want the system to prevent invalid payment entries, so that financial data remains accurate.

#### Acceptance Criteria

1. THE Payment_Entry_Service SHALL validate that customer_id belongs to the same organization
2. THE Payment_Entry_Service SHALL validate that payment_date is not more than 30 days in the future
3. THE Payment_Entry_Service SHALL validate that amount has at most 2 decimal places
4. THE Payment_Entry_Service SHALL validate that payment_mode is one of the allowed enum values
5. WHEN payment_mode is Cash, THE Payment_Entry_Service SHALL validate that amount does not exceed a configurable cash_limit
6. THE Payment_Entry_Service SHALL validate that currency_code is a valid ISO 4217 code
7. THE Payment_Entry_Service SHALL validate that all referenced invoices belong to the same customer
8. THE Payment_Entry_Service SHALL validate that all referenced invoices belong to the same organization

### Requirement 14: Payment Receipt Generation

**User Story:** As an accountant, I want to generate payment receipts, so that I can provide proof of payment to customers.

#### Acceptance Criteria

1. WHEN a Payment_Entry status is Confirmed, THE Receipt_Generator SHALL generate a unique receipt_number
2. THE Receipt_Generator SHALL format receipt_number as "RCP-{year}-{sequence}"
3. THE Payment_Receipt SHALL include organization details, customer details, payment date, amount, and payment mode
4. THE Payment_Receipt SHALL list all allocated invoices with allocated amounts
5. THE Payment_Receipt SHALL display unallocated amount if greater than zero
6. THE Payment_Receipt SHALL support PDF export
7. THE Payment_Receipt SHALL include a QR code containing receipt_number and verification URL
8. THE Receipt_Generator SHALL use the organization logo and branding configuration

### Requirement 15: Supplier Payment Support

**User Story:** As an accountant, I want to record payments made to suppliers, so that I can track accounts payable and cash outflows.

#### Acceptance Criteria

1. THE Payment_Entry SHALL include a payment_type field with values: "Customer_Payment", "Supplier_Payment"
2. WHEN payment_type is "Supplier_Payment", THE Payment_Entry_Form SHALL require supplier_id instead of customer_id
3. WHEN payment_type is "Supplier_Payment", THE Invoice_Linker SHALL display supplier purchase invoices
4. WHEN payment_type is "Supplier_Payment", THE Transaction_Ledger SHALL debit Accounts_Payable
5. WHEN payment_type is "Supplier_Payment", THE Transaction_Ledger SHALL credit the Bank or Cash account
6. THE Payment_Entry_Service SHALL validate that supplier_id belongs to the same organization
7. THE Payment_Entry_List SHALL support filtering by payment_type

### Requirement 16: Overpayment Handling

**User Story:** As an accountant, I want to track when customers pay more than the invoice amount, so that I can apply the excess to future invoices or issue refunds.

#### Acceptance Criteria

1. WHEN total allocated payments exceed invoice amount, THE Status_Updater SHALL set invoice status to Overpaid
2. THE Invoice_Detail SHALL display overpayment_amount when status is Overpaid
3. THE Payment_Entry SHALL allow allocation of overpayment amounts to other invoices for the same customer
4. THE Customer_Account_Statement SHALL display total overpayment balance across all invoices
5. THE Payment_Entry_Service SHALL support creating a refund Payment_Entry with negative amount
6. WHEN a refund Payment_Entry is created, THE Transaction_Ledger SHALL reverse the debit and credit accounts

### Requirement 17: Batch Payment Processing

**User Story:** As an accountant, I want to process multiple payments at once, so that I can efficiently handle high transaction volumes.

#### Acceptance Criteria

1. THE Batch_Payment_Processor SHALL accept a list of payment entry data
2. THE Batch_Payment_Processor SHALL validate all entries before processing any
3. IF any entry validation fails, THEN THE Batch_Payment_Processor SHALL return all validation errors without creating any payments
4. THE Batch_Payment_Processor SHALL create all Payment_Entries within a single database transaction
5. THE Batch_Payment_Processor SHALL return a summary of created payments and any errors
6. THE Batch_Payment_Processor SHALL support CSV import for payment data
7. THE Batch_Payment_Processor SHALL validate CSV format and required columns before processing

### Requirement 18: Payment Reconciliation Report

**User Story:** As an accountant, I want to see a reconciliation report showing payments matched to invoices, so that I can verify that all payments are properly allocated.

#### Acceptance Criteria

1. THE Reconciliation_Report SHALL list all Payment_Entries for a specified date range
2. THE Reconciliation_Report SHALL display allocated invoices for each payment
3. THE Reconciliation_Report SHALL highlight payments with unallocated amounts
4. THE Reconciliation_Report SHALL calculate total payments received and total allocated
5. THE Reconciliation_Report SHALL support filtering by customer, payment_mode, and status
6. THE Reconciliation_Report SHALL support export to Excel and PDF formats
7. THE Reconciliation_Report SHALL include organization_id filter for multi-tenancy

### Requirement 19: Payment Entry Performance Requirements

**User Story:** As a system administrator, I want payment operations to complete quickly, so that users have a responsive experience.

#### Acceptance Criteria

1. THE Payment_Entry_Service SHALL create a payment entry within 500 milliseconds
2. THE Invoice_Linker SHALL load unpaid invoices within 300 milliseconds for customers with up to 1000 invoices
3. THE Transaction_Ledger SHALL post journal entries within 1 second
4. THE Payment_Entry_List SHALL load and display 50 entries within 400 milliseconds
5. THE Reconciliation_Report SHALL generate reports for up to 10000 payments within 5 seconds
6. THE Payment_Entry_Service SHALL use database indexes on customer_id, payment_date, and organization_id

### Requirement 20: Payment Entry API Endpoints

**User Story:** As a frontend developer, I want RESTful API endpoints for payment operations, so that I can build user interfaces for payment management.

#### Acceptance Criteria

1. THE Payment_API SHALL provide POST /api/v1/payments to create payment entries
2. THE Payment_API SHALL provide GET /api/v1/payments to list payment entries with filtering
3. THE Payment_API SHALL provide GET /api/v1/payments/{id} to retrieve payment entry details
4. THE Payment_API SHALL provide PUT /api/v1/payments/{id} to update draft payment entries
5. THE Payment_API SHALL provide POST /api/v1/payments/{id}/confirm to change status to Confirmed
6. THE Payment_API SHALL provide POST /api/v1/payments/{id}/cancel to change status to Cancelled
7. THE Payment_API SHALL provide POST /api/v1/payments/{id}/allocations to create Payment_References
8. THE Payment_API SHALL provide DELETE /api/v1/payments/{id}/allocations/{allocation_id} to remove allocations
9. THE Payment_API SHALL provide GET /api/v1/payments/{id}/receipt to generate payment receipt
10. THE Payment_API SHALL return appropriate HTTP status codes and error messages
11. THE Payment_API SHALL enforce organization_id isolation for all endpoints
