# Implementation Plan: Payment Flow System

## Overview

This implementation plan breaks down the Payment Flow system into 12 phases that can be checked in independently. Each phase builds on previous phases and includes specific tasks for creating reusable components, hooks, utilities, and helper methods. The plan follows clean code practices with meaningful variable names and leverages existing UI components from the shared library.

The system implements manual payment capture (Cash, Check, Bank Transfer) with automatic journal entry posting, invoice allocation, and comprehensive audit trails. It integrates with existing Chart of Accounts, Journal Entries, and multi-tenancy infrastructure.

## Implementation Language

- **Backend**: Python (FastAPI, SQLAlchemy, Pydantic)
- **Frontend**: TypeScript (React)

## Tasks

### Phase 1: Database Schema and Models

- [ ] 1. Create database migrations and core models
  - [x] 1.1 Create Alembic migration for payment_entries table
    - Use CREATE TABLE IF NOT EXISTS for idempotent migrations
    - Add all fields: id, organization_id, payment_type, party_id, amount, currency_code, payment_date, payment_mode, reference_no, status, source, gateway_transaction_id, receipt_number, cancellation_reason, cancelled_by, cancelled_at, created_by, updated_by, created_at, updated_at
    - Add check constraints for amount > 0, status enum, payment_mode enum, payment_type enum
    - Add conditional constraints for reference_no and gateway_transaction_id
    - Add foreign key constraints to organizations and users tables
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 15.1_

  - [x] 1.2 Create Alembic migration for payment_references table
    - Use CREATE TABLE IF NOT EXISTS for idempotent migrations
    - Add fields: id, organization_id, payment_id, invoice_id, allocated_amount, exchange_rate, allocated_amount_invoice_currency, created_by, created_at
    - Add check constraint for allocated_amount > 0
    - Add unique constraint on (payment_id, invoice_id)
    - Add foreign key constraints to payment_entries, invoices, organizations, users
    - _Requirements: 2.5, 10.3, 10.4_


  - [x] 1.3 Create Alembic migration for payment_audit_log table
    - Use CREATE TABLE IF NOT EXISTS for idempotent migrations
    - Add fields: id, organization_id, payment_id, action, user_id, old_values, new_values, timestamp
    - Add check constraint for action enum (CREATE, UPDATE, CONFIRM, CANCEL, ALLOCATE, DEALLOCATE)
    - Add foreign key constraints to payment_entries, organizations, users
    - Use JSONB type for old_values and new_values fields
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [x] 1.4 Add database indexes for performance
    - Use CREATE INDEX IF NOT EXISTS for idempotent migrations
    - Create index on payment_entries(organization_id, payment_date)
    - Create index on payment_entries(organization_id, party_id)
    - Create index on payment_entries(organization_id, status)
    - Create index on payment_entries(reference_no)
    - Create index on payment_entries(receipt_number)
    - Create index on payment_references(payment_id)
    - Create index on payment_references(invoice_id)
    - Create index on payment_references(organization_id)
    - Create index on payment_audit_log(payment_id, timestamp)
    - Create index on payment_audit_log(organization_id, timestamp)
    - _Requirements: 19.6_

  - [x] 1.5 Implement PaymentEntry SQLAlchemy model
    - Create model class with all fields from migration
    - Add relationship to payment_references (one-to-many)
    - Add relationship to audit_logs (one-to-many)
    - Add computed property for unallocated_amount
    - Add __repr__ method for debugging
    - _Requirements: 1.1, 1.4, 1.5, 1.6, 9.1_

  - [x] 1.6 Implement PaymentReference SQLAlchemy model
    - Create model class with all fields from migration
    - Add relationship to payment_entry (many-to-one)
    - Add relationship to invoice (many-to-one)
    - Add __repr__ method for debugging
    - _Requirements: 2.5, 10.3, 10.4_

  - [x] 1.7 Implement PaymentAuditLog SQLAlchemy model
    - Create model class with all fields from migration
    - Add relationship to payment_entry (many-to-one)
    - Add __repr__ method for debugging
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ]* 1.8 Write unit tests for model constraints
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_payment_models.py`
    - Test amount validation (must be > 0)
    - Test status enum validation
    - Test payment_mode enum validation
    - Test conditional reference_no requirement
    - Test unique constraint on (payment_id, invoice_id)
    - _Requirements: 1.7, 13.3, 13.4_

- [ ] 2. Checkpoint - Verify database schema
  - Run migrations on test database
  - Verify all tables created with correct columns and constraints
  - Verify indexes created successfully
  - Ensure all tests pass, ask the user if questions arise



### Phase 2: Pydantic Schemas and Validation

- [ ] 3. Create Pydantic schemas for API validation
  - [x] 3.1 Create PaymentEntry schemas
    - Implement PaymentEntryBase with all common fields
    - Implement PaymentEntryCreate for creation requests
    - Implement PaymentEntryUpdate for update requests
    - Implement PaymentEntryResponse for API responses
    - Implement PaymentEntryListItem for list views
    - Implement PaymentEntryListResponse with pagination
    - Add field validators for currency_code (ISO 4217), amount (2 decimals), payment_date (not > 30 days future)
    - _Requirements: 1.1, 1.2, 1.3, 1.7, 1.8, 1.9, 13.1, 13.2, 13.3, 13.6_

  - [x] 3.2 Create PaymentReference schemas
    - Implement PaymentReferenceBase with common fields
    - Implement PaymentReferenceCreate for allocation requests
    - Implement PaymentReferenceResponse for API responses
    - Add field validator for allocated_amount (must be > 0, max 2 decimals)
    - _Requirements: 2.5, 10.3, 10.4_

  - [x] 3.3 Create supporting schemas
    - Implement CancelPaymentRequest with reason field
    - Implement BatchPaymentCreate with list of payments
    - Implement BatchProcessResult with success/error counts
    - Implement PaymentFilters for search and filtering
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 12.6, 17.1, 17.5_

  - [ ]* 3.4 Write property test for schema validation
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_payment_schema_properties.py`
    - **Property 1: Payment Entry Validation**
    - **Validates: Requirements 1.7, 1.8, 1.9, 13.1, 13.2, 13.3, 13.6**
    - Test that amount > 0, payment_date not > 30 days future, amount has max 2 decimals, currency_code is valid ISO 4217

  - [ ]* 3.5 Write property test for conditional reference requirement
    - **Property 2: Conditional Reference Number Requirement**
    - **Validates: Requirements 1.2, 1.3**
    - Test that reference_no is required when payment_mode is Check or Bank_Transfer

- [ ] 4. Checkpoint - Verify schema validation
  - Test schema validation with valid and invalid data
  - Verify field validators work correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 3: Repository Layer

- [ ] 5. Implement repository classes for data access
  - [x] 5.1 Create PaymentEntryRepository
    - Implement create() method with organization_id validation
    - Implement get_by_id() with organization_id filtering
    - Implement list_with_filters() supporting all filter types (status, payment_mode, party_id, date_range, search)
    - Implement update() method for draft payments only
    - Implement delete() method for draft payments only
    - Implement get_by_receipt_number() method
    - Add eager loading for payment_references relationship
    - Use SQLAlchemy query optimization techniques
    - _Requirements: 5.2, 5.3, 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 13.1, 13.8, 20.11_

  - [x] 5.2 Create PaymentReferenceRepository
    - Implement create() method with validation
    - Implement get_by_payment_id() method
    - Implement get_by_invoice_id() method
    - Implement delete() method
    - Implement get_total_allocated_for_invoice() helper method
    - Implement get_total_allocated_for_payment() helper method
    - _Requirements: 2.5, 4.1, 4.7, 9.1_

  - [x] 5.3 Create PaymentAuditLogRepository
    - Implement create() method for audit entries
    - Implement get_by_payment_id() method with timestamp ordering
    - Implement list_by_organization() method with date filtering
    - Ensure audit logs are append-only (no update or delete methods)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7_

  - [ ]* 5.4 Write unit tests for repository methods
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_payment_repository.py`
    - Test CRUD operations for each repository
    - Test filtering and pagination
    - Test eager loading performance
    - Test organization_id isolation

  - [ ]* 5.5 Write property test for multi-tenancy isolation
    - **Property 4: Multi-Tenancy Isolation**
    - **Validates: Requirements 1.4, 3.7, 7.5**
    - Test that organization_id is consistent across related entities

- [ ] 6. Checkpoint - Verify repository layer
  - Test all repository methods with test database
  - Verify multi-tenancy isolation works correctly
  - Verify query performance with indexes
  - Ensure all tests pass, ask the user if questions arise



### Phase 4: Core Service Layer - Payment Entry Service

- [ ] 7. Implement PaymentEntryService with business logic
  - [x] 7.1 Create PaymentEntryService class structure
    - Initialize with dependencies (repository, audit_logger, currency_service)
    - Create helper method _validate_party_belongs_to_organization()
    - Create helper method _validate_payment_date()
    - Create helper method _validate_amount()
    - Create helper method _validate_currency_code()
    - Create helper method _validate_cash_limit()
    - _Requirements: 1.9, 13.1, 13.2, 13.3, 13.5, 13.6_

  - [x] 7.2 Implement create_payment_entry() method
    - Validate all input fields using helper methods
    - Set default status to Draft
    - Set default source to Manual
    - Set unallocated_amount to payment amount initially
    - Create audit log entry for CREATE action
    - Return PaymentEntryResponse
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 7.1_

  - [x] 7.3 Implement update_payment_entry() method
    - Validate payment is in Draft status
    - Validate updated fields using helper methods
    - Update payment entry
    - Create audit log entry for UPDATE action with old/new values
    - Return updated PaymentEntryResponse
    - _Requirements: 5.2, 7.2, 7.7_

  - [x] 7.4 Implement get_payment_entry() method
    - Retrieve payment by ID with organization_id filtering
    - Eager load payment_references with invoice details
    - Calculate unallocated_amount
    - Return PaymentEntryResponse with allocations
    - _Requirements: 9.1, 9.2, 20.3, 20.11_

  - [x] 7.5 Implement list_payment_entries() method
    - Apply filters (status, payment_mode, party_id, date_range, search, has_unallocated)
    - Apply sorting (payment_date, amount, party_name)
    - Apply pagination
    - Return PaymentEntryListResponse with pagination metadata
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 9.3, 9.6_

  - [x] 7.6 Implement delete_payment_entry() method
    - Validate payment is in Draft status
    - Delete payment entry (cascade deletes references and audit logs)
    - _Requirements: 5.3_

  - [ ]* 7.7 Write unit tests for PaymentEntryService
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_payment_entry_service.py`
    - Test create with valid and invalid data
    - Test update for draft vs confirmed payments
    - Test delete for draft vs confirmed payments
    - Test list with various filters
    - Test validation error messages

  - [ ]* 7.8 Write property test for payment entry defaults
    - **Property 3: Payment Entry Defaults**
    - **Validates: Requirements 1.5, 1.6**
    - Test that status defaults to Draft and source defaults to Manual

  - [ ]* 7.9 Write property test for draft payment mutability
    - **Property 14: Draft Payment Mutability**
    - **Validates: Requirements 5.2, 5.3**
    - Test that draft payments can be modified and deleted

- [ ] 8. Checkpoint - Verify payment entry service
  - Test all service methods with various scenarios
  - Verify validation rules work correctly
  - Verify audit logging captures all changes
  - Ensure all tests pass, ask the user if questions arise



### Phase 5: Allocation Service

- [ ] 9. Implement AllocationService for payment-to-invoice linking
  - [x] 9.1 Create AllocationService class structure
    - Initialize with dependencies (payment_repo, reference_repo, invoice_repo, audit_logger)
    - Create helper method _validate_allocation_amount()
    - Create helper method _validate_invoice_belongs_to_party()
    - Create helper method _validate_invoice_belongs_to_organization()
    - Create helper method _calculate_invoice_outstanding_balance()
    - _Requirements: 2.3, 2.4, 13.7, 13.8_

  - [x] 9.2 Implement create_allocation() method
    - Validate payment is in Draft status
    - Validate invoice belongs to same party as payment
    - Validate invoice belongs to same organization
    - Validate allocated_amount does not exceed payment unallocated_amount
    - Validate allocated_amount does not exceed invoice outstanding balance
    - Calculate exchange_rate if currencies differ
    - Calculate allocated_amount_invoice_currency
    - Create payment_reference record
    - Update payment unallocated_amount
    - Create audit log entry for ALLOCATE action
    - Return PaymentReferenceResponse
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 7.4, 10.3, 10.4_

  - [x] 9.3 Implement create_bulk_allocations() method
    - Validate total allocated amounts do not exceed payment amount
    - Validate all invoices belong to same party and organization
    - Create all allocations within a transaction
    - Create audit log entries for all allocations
    - Return list of PaymentReferenceResponse
    - _Requirements: 2.3, 2.4, 13.7, 13.8_

  - [x] 9.4 Implement remove_allocation() method
    - Validate payment is in Draft status
    - Delete payment_reference record
    - Update payment unallocated_amount
    - Create audit log entry for DEALLOCATE action
    - _Requirements: 7.4, 9.4_

  - [x] 9.5 Implement get_payment_allocations() method
    - Retrieve all payment_references for a payment
    - Include invoice details (number, date, amount, outstanding balance)
    - Return list of PaymentReferenceResponse
    - _Requirements: 2.7, 9.2_

  - [x] 9.6 Implement get_invoice_allocations() method
    - Retrieve all payment_references for an invoice
    - Include payment details
    - Return list of PaymentReferenceResponse
    - _Requirements: 4.1, 4.7_

  - [ ]* 9.7 Write unit tests for AllocationService
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_allocation_service.py`
    - Test allocation creation with valid and invalid amounts
    - Test bulk allocation validation
    - Test allocation removal
    - Test multi-currency allocation with exchange rates

  - [ ]* 9.8 Write property test for allocation amount constraints
    - Add to test file: `horizon-sync-erp-be/core-service/tests/test_payment_properties.py`
    - **Property 5: Allocation Amount Constraints**
    - **Validates: Requirements 2.3, 2.4**
    - Test that total allocated amounts do not exceed payment amount and individual allocations do not exceed invoice outstanding balance

  - [ ]* 9.9 Write property test for unallocated amount calculation
    - **Property 6: Unallocated Amount Calculation**
    - **Validates: Requirements 2.8, 9.1**
    - Test that unallocated_amount equals payment amount minus sum of allocated amounts

  - [ ]* 9.10 Write property test for same-party invoice allocation
    - **Property 36: Same-Party Invoice Allocation**
    - **Validates: Requirements 13.7**
    - Test that all allocated invoices belong to same party as payment

  - [ ]* 9.11 Write property test for same-organization invoice allocation
    - **Property 37: Same-Organization Invoice Allocation**
    - **Validates: Requirements 13.8**
    - Test that all allocated invoices belong to same organization as payment

- [ ] 10. Checkpoint - Verify allocation service
  - Test allocation creation and removal
  - Verify validation rules prevent invalid allocations
  - Verify unallocated_amount calculation is correct
  - Ensure all tests pass, ask the user if questions arise



### Phase 6: Invoice Status Service

- [ ] 11. Implement InvoiceStatusService for automatic status updates
  - [x] 11.1 Create InvoiceStatusService class structure
    - Initialize with dependencies (invoice_repo, reference_repo)
    - Create helper method _calculate_total_allocated()
    - Create helper method _determine_invoice_status()
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.7_

  - [x] 11.2 Implement update_invoice_status() method
    - Calculate total allocated payments for invoice
    - Calculate outstanding balance (invoice amount - total allocated)
    - Determine new status based on allocation (Unpaid, Partially_Paid, Paid, Overpaid)
    - Update invoice status and outstanding_balance fields
    - Return updated invoice
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

  - [x] 11.3 Implement calculate_outstanding_balance() method
    - Get invoice amount
    - Get total allocated payments
    - Return invoice amount minus total allocated
    - _Requirements: 4.7, 13.3_

  - [x] 11.4 Integrate with AllocationService
    - Call update_invoice_status() after create_allocation()
    - Call update_invoice_status() after remove_allocation()
    - Ensure status updates happen within same transaction as allocation changes
    - _Requirements: 4.6, 5.7_

  - [ ]* 11.5 Write unit tests for InvoiceStatusService
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_invoice_status_service.py`
    - Test status calculation for various allocation scenarios
    - Test outstanding balance calculation
    - Test status updates are atomic with allocations

  - [ ]* 11.6 Write property test for invoice status calculation
    - **Property 12: Invoice Status Calculation**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
    - Test that status is calculated correctly based on total allocated payments

  - [ ]* 11.7 Write property test for outstanding balance calculation
    - **Property 13: Outstanding Balance Calculation**
    - **Validates: Requirements 4.7**
    - Test that outstanding balance equals invoice amount minus total allocated

  - [ ]* 11.8 Write property test for invoice status recalculation
    - **Property 18: Invoice Status Recalculation on Changes**
    - **Validates: Requirements 4.1, 5.7, 12.5**
    - Test that invoice status is recalculated when payment references are created or deleted

- [ ] 12. Checkpoint - Verify invoice status service
  - Test status updates for various allocation scenarios
  - Verify status changes are atomic with allocations
  - Verify outstanding balance calculations are correct
  - Ensure all tests pass, ask the user if questions arise



### Phase 7: Journal Posting Service

- [ ] 13. Implement JournalPostingService for general ledger integration
  - [x] 13.1 Create JournalPostingService class structure
    - Initialize with dependencies (journal_entry_service, default_account_service, currency_service)
    - Create helper method _get_payment_account_by_mode()
    - Create helper method _validate_default_accounts_configured()
    - Create helper method _convert_to_base_currency()
    - _Requirements: 3.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.7, 6.8, 10.5, 10.6_

  - [x] 13.2 Implement post_payment_journal_entry() method for customer payments
    - Validate required default accounts are configured (Bank/Cash/Checks_Received, Accounts_Receivable)
    - Determine debit account based on payment_mode (Cash → Cash account, Check → Checks_Received, Bank_Transfer → Bank)
    - Convert payment amount to base currency if needed
    - Create journal entry with reference_type="PaymentEntry" and reference_id=payment_id
    - Add debit line to Bank/Cash/Checks_Received account
    - Add credit line to Accounts_Receivable account
    - Validate debits equal credits
    - Post journal entry
    - Return journal entry
    - _Requirements: 3.1, 3.2, 3.3, 3.6, 3.7, 3.8, 3.9, 10.5, 10.6_

  - [x] 13.3 Implement post_payment_journal_entry() method for supplier payments
    - Validate required default accounts are configured (Bank/Cash, Accounts_Payable)
    - Determine credit account based on payment_mode
    - Convert payment amount to base currency if needed
    - Create journal entry with reference_type="PaymentEntry" and reference_id=payment_id
    - Add debit line to Accounts_Payable account
    - Add credit line to Bank/Cash account
    - Validate debits equal credits
    - Post journal entry
    - Return journal entry
    - _Requirements: 3.1, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 15.4, 15.5_

  - [x] 13.4 Implement reverse_payment_journal_entry() method
    - Retrieve original journal entry for payment
    - Create reversing journal entry with opposite debits and credits
    - Set reference_type="PaymentEntry" and reference_id=payment_id
    - Post reversing journal entry
    - Return reversing journal entry
    - _Requirements: 12.2, 12.3, 16.6_

  - [ ]* 13.5 Write unit tests for JournalPostingService
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_journal_posting_service.py`
    - Test customer payment journal entry structure
    - Test supplier payment journal entry structure
    - Test reversing journal entry creation
    - Test validation of default accounts
    - Test currency conversion

  - [ ]* 13.6 Write property test for journal entry balance
    - **Property 8: Journal Entry Balance**
    - **Validates: Requirements 3.9**
    - Test that sum of debits equals sum of credits for all journal entries

  - [ ]* 13.7 Write property test for customer payment journal structure
    - **Property 9: Customer Payment Journal Entry Structure**
    - **Validates: Requirements 3.2, 3.3, 3.6**
    - Test that customer payments debit Bank/Cash/Checks_Received and credit Accounts_Receivable

  - [ ]* 13.8 Write property test for supplier payment journal structure
    - **Property 10: Supplier Payment Journal Entry Structure**
    - **Validates: Requirements 3.4, 3.5, 3.6**
    - Test that supplier payments debit Accounts_Payable and credit Bank/Cash

  - [ ]* 13.9 Write property test for journal entry reference tracking
    - **Property 11: Journal Entry Reference Tracking**
    - **Validates: Requirements 3.8**
    - Test that journal entries have reference_type="PaymentEntry" and reference_id=payment_id

  - [ ]* 13.10 Write property test for base currency posting
    - **Property 29: Base Currency Journal Posting**
    - **Validates: Requirements 10.5, 10.6**
    - Test that journal entries are posted in organization base currency with exchange rate conversion

- [ ] 14. Checkpoint - Verify journal posting service
  - Test journal entry creation for customer and supplier payments
  - Verify debits equal credits
  - Verify reversing entries are correct
  - Verify currency conversion works correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 8: Payment Confirmation and Cancellation

- [ ] 15. Implement payment status transitions
  - [x] 15.1 Add confirm_payment() method to PaymentEntryService
    - Validate payment is in Draft status
    - Validate at least one allocation exists
    - Validate required default accounts are configured
    - Generate unique receipt_number (format: RCP-{year}-{sequence})
    - Update payment status to Confirmed
    - Call JournalPostingService.post_payment_journal_entry()
    - Create audit log entry for CONFIRM action
    - Return confirmed PaymentEntryResponse
    - _Requirements: 3.1, 3.10, 5.1, 5.4, 5.8, 5.9, 6.7, 6.8, 7.3, 14.1, 14.2_

  - [x] 15.2 Add cancel_payment() method to PaymentEntryService
    - Validate payment is in Confirmed status
    - Validate cancellation_reason is provided
    - Update payment status to Cancelled
    - Set cancellation_reason, cancelled_by, cancelled_at fields
    - Call JournalPostingService.reverse_payment_journal_entry()
    - Remove all payment_references (triggers invoice status recalculation)
    - Create audit log entry for CANCEL action with reason
    - Return cancelled PaymentEntryResponse
    - _Requirements: 5.1, 5.6, 7.3, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

  - [ ]* 15.3 Write unit tests for status transitions
    - Test confirm with and without allocations
    - Test confirm with missing default accounts
    - Test cancel with and without reason
    - Test that confirmed payments cannot be modified
    - Test that cancelled payments cannot be modified

  - [ ]* 15.4 Write property test for confirmed payment immutability
    - **Property 15: Confirmed Payment Immutability**
    - **Validates: Requirements 5.4, 5.5**
    - Test that confirmed payments cannot be modified or deleted

  - [ ]* 15.5 Write property test for confirmation requires allocations
    - **Property 16: Confirmation Requires Allocations**
    - **Validates: Requirements 5.8, 5.9**
    - Test that payments cannot be confirmed without at least one allocation

  - [ ]* 15.6 Write property test for cancellation reversal
    - **Property 17: Cancellation Reversal**
    - **Validates: Requirements 5.6, 12.2, 12.3, 12.4**
    - Test that cancellation creates reversing journal entry and removes allocations

  - [ ]* 15.7 Write property test for cancellation metadata
    - **Property 33: Cancellation Metadata Recording**
    - **Validates: Requirements 12.6, 12.7**
    - Test that cancellation_reason, cancelled_by, cancelled_at are populated

  - [ ]* 15.8 Write property test for confirmation with unallocated amount
    - **Property 27: Confirmation with Unallocated Amount**
    - **Validates: Requirements 9.5**
    - Test that payments can be confirmed even with unallocated_amount > 0

- [ ] 16. Checkpoint - Verify status transitions
  - Test payment confirmation flow end-to-end
  - Test payment cancellation flow end-to-end
  - Verify journal entries are created/reversed correctly
  - Verify invoice statuses are updated correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 9: Receipt Service and Batch Processing

- [ ] 17. Implement ReceiptService and BatchPaymentProcessor
  - [x] 17.1 Create ReceiptService class
    - Initialize with dependencies (payment_repo, organization_service)
    - Implement generate_receipt_number() method (format: RCP-{year}-{sequence})
    - Implement generate_receipt_pdf() method with organization branding
    - Implement generate_receipt_qr_code() method with receipt_number and verification URL
    - Include payment details, allocated invoices, unallocated amount in receipt
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8_

  - [x] 17.2 Create BatchPaymentProcessor class
    - Initialize with dependencies (payment_service, allocation_service)
    - Implement validate_batch() method to validate all entries before processing
    - Implement process_batch() method to create all payments in single transaction
    - Implement import_from_csv() method with CSV parsing and validation
    - Return BatchProcessResult with success/error counts and details
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

  - [ ]* 17.3 Write unit tests for ReceiptService
    - Test receipt number generation uniqueness
    - Test receipt PDF generation
    - Test QR code generation
    - Test receipt content completeness

  - [ ]* 17.4 Write unit tests for BatchPaymentProcessor
    - Test batch validation with valid and invalid entries
    - Test transaction rollback on validation failure
    - Test CSV import with valid and invalid data

  - [ ]* 17.5 Write property test for receipt number generation
    - **Property 38: Receipt Number Generation**
    - **Validates: Requirements 14.1, 14.2**
    - Test that receipt numbers are unique and follow format RCP-{year}-{sequence}

  - [ ]* 17.6 Write property test for receipt content completeness
    - **Property 39: Receipt Content Completeness**
    - **Validates: Requirements 14.3, 14.4, 14.5**
    - Test that receipts include all required information

  - [ ]* 17.7 Write property test for batch validation
    - **Property 47: Batch Payment Validation**
    - **Validates: Requirements 17.2, 17.3**
    - Test that if any payment fails validation, no payments are created

- [ ] 18. Checkpoint - Verify receipt and batch services
  - Test receipt generation for various payment scenarios
  - Test batch processing with valid and invalid data
  - Verify transaction rollback works correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 10: API Endpoints

- [ ] 19. Implement FastAPI endpoints for payment operations
  - [x] 19.1 Create payment API router and dependencies
    - Create router at /api/v1/payments
    - Add authentication dependency
    - Add organization_id extraction from authenticated user
    - Add error handling middleware
    - _Requirements: 20.10, 20.11_

  - [x] 19.2 Implement POST /api/v1/payments endpoint
    - Accept PaymentEntryCreate schema
    - Call PaymentEntryService.create_payment_entry()
    - Return 201 Created with PaymentEntryResponse
    - Handle validation errors with 400 Bad Request
    - _Requirements: 20.1_

  - [x] 19.3 Implement GET /api/v1/payments endpoint
    - Accept query parameters for filtering (status, payment_mode, party_id, date_from, date_to, search, has_unallocated)
    - Accept pagination parameters (page, page_size)
    - Accept sorting parameters (sort_by, sort_order)
    - Call PaymentEntryService.list_payment_entries()
    - Return 200 OK with PaymentEntryListResponse
    - _Requirements: 20.2_

  - [x] 19.4 Implement GET /api/v1/payments/{id} endpoint
    - Accept payment_id path parameter
    - Call PaymentEntryService.get_payment_entry()
    - Return 200 OK with PaymentEntryResponse including allocations
    - Return 404 Not Found if payment doesn't exist
    - _Requirements: 20.3_

  - [x] 19.5 Implement PUT /api/v1/payments/{id} endpoint
    - Accept payment_id path parameter and PaymentEntryUpdate schema
    - Call PaymentEntryService.update_payment_entry()
    - Return 200 OK with updated PaymentEntryResponse
    - Return 409 Conflict if payment is not in Draft status
    - _Requirements: 20.4_

  - [x] 19.6 Implement POST /api/v1/payments/{id}/confirm endpoint
    - Accept payment_id path parameter
    - Call PaymentEntryService.confirm_payment()
    - Return 200 OK with confirmed PaymentEntryResponse
    - Return 409 Conflict if payment cannot be confirmed
    - _Requirements: 20.5_

  - [x] 19.7 Implement POST /api/v1/payments/{id}/cancel endpoint
    - Accept payment_id path parameter and CancelPaymentRequest schema
    - Call PaymentEntryService.cancel_payment()
    - Return 200 OK with cancelled PaymentEntryResponse
    - Return 409 Conflict if payment cannot be cancelled
    - _Requirements: 20.6_

  - [x] 19.8 Implement POST /api/v1/payments/{id}/allocations endpoint
    - Accept payment_id path parameter and PaymentReferenceCreate schema
    - Call AllocationService.create_allocation()
    - Return 201 Created with PaymentReferenceResponse
    - Handle validation errors with 400 Bad Request
    - _Requirements: 20.7_

  - [x] 19.9 Implement DELETE /api/v1/payments/allocations/{allocation_id} endpoint
    - Accept allocation_id path parameter
    - Call AllocationService.remove_allocation()
    - Return 204 No Content
    - Return 404 Not Found if allocation doesn't exist
    - _Requirements: 20.8_

  - [x] 19.10 Implement GET /api/v1/payments/{id}/receipt endpoint
    - Accept payment_id path parameter
    - Call ReceiptService.generate_receipt_pdf()
    - Return 200 OK with PDF content-type
    - Return 404 Not Found if payment doesn't exist or is not confirmed
    - _Requirements: 20.9_

  - [ ]* 19.11 Write API integration tests
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_payment_api_integration.py`
    - Test complete payment flow (create → allocate → confirm)
    - Test error handling for all endpoints
    - Test authentication and authorization
    - Test multi-tenancy isolation

  - [ ]* 19.12 Write property test for API organization isolation
    - **Property 50: API Organization Isolation**
    - **Validates: Requirements 20.11**
    - Test that API endpoints only return data for authenticated user's organization

- [ ] 20. Checkpoint - Verify API endpoints
  - Test all endpoints with Postman or similar tool
  - Verify error responses are correct
  - Verify authentication and authorization work
  - Ensure all tests pass, ask the user if questions arise



### Phase 11: Data Seeding

- [ ] 21. Create comprehensive seed data for testing
  - [x] 21.1 Create seed_payments.py script
    - Seed 2-3 test organizations with different configurations
    - Seed 10 customers and 10 suppliers per organization
    - Seed complete chart of accounts with required accounts
    - Configure default accounts for each organization
    - Seed 50 customer invoices with various statuses (Unpaid, Partially_Paid, Paid)
    - Seed 30 supplier invoices
    - _Requirements: All requirements for testing_

  - [x] 21.2 Seed draft payment scenarios
    - Create 10 draft customer payments with no allocations
    - Create 5 draft customer payments with partial allocations
    - Create 5 draft supplier payments
    - Mix of payment modes (Cash, Check, Bank_Transfer)
    - Mix of currencies
    - _Requirements: 1.1, 1.2, 1.3, 1.5, 9.1_

  - [x] 21.3 Seed confirmed payment scenarios
    - Create 15 confirmed customer payments with full allocations
    - Create 10 confirmed customer payments with partial allocations (unallocated amount > 0)
    - Create 5 confirmed supplier payments
    - Create 3 multi-invoice allocations (payment allocated to 3+ invoices)
    - Create 2 multi-currency payments
    - Generate receipt numbers for all confirmed payments
    - _Requirements: 2.2, 5.1, 9.5, 10.1, 14.1_

  - [x] 21.4 Seed cancelled payment scenarios
    - Create 3 cancelled customer payments with cancellation reasons
    - Create 2 cancelled supplier payments
    - Ensure reversing journal entries exist
    - _Requirements: 5.1, 12.1, 12.6_

  - [x] 21.5 Seed special scenarios
    - Create 2 overpayment scenarios (allocation exceeds invoice amount)
    - Create 1 refund payment (negative amount)
    - Create 2 payments with unallocated amounts
    - Create 1 payment allocated to multiple invoices
    - _Requirements: 9.1, 16.1, 16.3, 16.5_

  - [ ] 21.6 Verify seed data integrity
    - Run script and verify all data created successfully
    - Verify invoice statuses are correct based on allocations
    - Verify journal entries balance (debits = credits)
    - Verify audit logs exist for all operations
    - _Requirements: All requirements_

- [ ] 22. Checkpoint - Verify seed data
  - Run seed script on clean database
  - Verify all scenarios are represented
  - Test API endpoints with seeded data
  - Ensure all tests pass, ask the user if questions arise



### Phase 12: Frontend Types and API Utilities

- [x] 23. Create TypeScript types and API utilities
  - [x] 23.1 Create payment.types.ts with type definitions
    - Define PaymentType, PaymentMode, PaymentStatus, PaymentSource enums
    - Define PaymentEntry interface matching backend schema
    - Define PaymentReference interface
    - Define CreatePaymentPayload interface
    - Define UpdatePaymentPayload interface
    - Define AllocationCreate interface
    - Define PaymentFilters interface
    - Define PaymentsResponse interface with pagination
    - Define CancelPaymentPayload interface
    - Define BatchProcessResult interface
    - _Requirements: 1.1, 2.5, 8.1, 12.6, 17.5_

  - [x] 23.2 Create api/payments.ts with API utility functions
    - Implement fetchPayments(filters?: PaymentFilters): Promise<PaymentsResponse>
    - Implement fetchPaymentById(id: string): Promise<PaymentEntry>
    - Implement createPaymentEntry(data: CreatePaymentPayload): Promise<PaymentEntry>
    - Implement updatePaymentEntry(id: string, data: UpdatePaymentPayload): Promise<PaymentEntry>
    - Implement confirmPaymentEntry(id: string): Promise<PaymentEntry>
    - Implement cancelPaymentEntry(id: string, reason: string): Promise<PaymentEntry>
    - Implement createAllocation(paymentId: string, data: AllocationCreate): Promise<PaymentReference>
    - Implement deleteAllocation(allocationId: string): Promise<void>
    - Implement downloadReceipt(paymentId: string): Promise<Blob>
    - Add proper error handling and type safety
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8, 20.9_

  - [ ]* 23.3 Write unit tests for API utilities
    - Create test file: `horizon-sync/apps/inventory/src/app/utility/api/payments.test.ts`
    - Test API functions with mocked responses
    - Test error handling
    - Test query parameter construction

- [x] 24. Checkpoint - Verify types and API utilities
  - Verify types match backend schemas
  - Test API utilities with backend
  - Ensure all tests pass, ask the user if questions arise



### Phase 13: Frontend Hooks

- [x] 25. Create reusable React hooks for payment operations
  - [x] 25.1 Create usePayments.ts hook
    - Use React Query for data fetching
    - Accept PaymentFilters parameter
    - Return payments array, pagination metadata, loading state, error state, refetch function
    - Implement automatic refetching on filter changes
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 25.2 Create usePaymentActions.ts hook
    - Use React Query mutations for create, update, confirm, cancel operations
    - Implement createPayment mutation with optimistic updates
    - Implement updatePayment mutation
    - Implement confirmPayment mutation
    - Implement cancelPayment mutation
    - Invalidate queries on success
    - Handle errors with toast notifications
    - _Requirements: 1.1, 5.1, 5.2, 12.1, 20.1, 20.4, 20.5, 20.6_

  - [x] 25.3 Create useInvoiceAllocations.ts hook
    - Accept paymentId parameter
    - Fetch allocations for payment
    - Implement createAllocation mutation
    - Implement removeAllocation mutation
    - Calculate remaining unallocated amount
    - Invalidate payment queries on allocation changes
    - _Requirements: 2.2, 2.8, 9.1, 9.4, 20.7, 20.8_

  - [x] 25.4 Create usePaymentValidation.ts hook
    - Implement validation rules for payment form fields
    - Validate amount > 0 and max 2 decimals
    - Validate payment_date not > 30 days in future
    - Validate reference_no required for Check and Bank_Transfer
    - Validate currency_code format
    - Return validation errors and isValid flag
    - _Requirements: 1.2, 1.3, 1.7, 1.8, 13.2, 13.3, 13.6_

  - [x]* 25.5 Write unit tests for hooks
    - Create test files co-located with hooks:
      - `horizon-sync/apps/inventory/src/app/hooks/usePayments.test.ts`
      - `horizon-sync/apps/inventory/src/app/hooks/usePaymentActions.test.ts`
      - `horizon-sync/apps/inventory/src/app/hooks/useInvoiceAllocations.test.ts`
    - Test usePayments with various filters
    - Test usePaymentActions mutations
    - Test useInvoiceAllocations calculations
    - Test usePaymentValidation rules

- [x] 26. Checkpoint - Verify frontend hooks
  - Test hooks in isolation with mocked API
  - Verify query invalidation works correctly
  - Verify error handling works correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 14: Core Frontend Components

- [x] 27. Implement core payment management components
  - [x] 27.1 Create PaymentManagement.tsx container component
    - Use existing Card component from shared UI library
    - Integrate PaymentTable, PaymentFilters, and PaymentDialog components
    - Use usePayments hook for data fetching
    - Use usePaymentActions hook for mutations
    - Handle loading and error states
    - Add "New Payment" button to open dialog
    - Follow patterns from AccountManagement.tsx
    - _Requirements: 1.1, 8.1, 8.7_

  - [x] 27.2 Create PaymentTable.tsx component
    - Use DataTable component from libs/shared/ui/src/components/data-table
    - Define columns: receipt_number, payment_date, party_name, amount, payment_mode, status, actions
    - Implement sorting by payment_date, amount, party_name
    - Add row actions: View, Edit (draft only), Confirm (draft only), Cancel (confirmed only)
    - Use Badge component for status display
    - Use Button component for actions
    - Follow patterns from AccountsTable.tsx
    - _Requirements: 8.7, 8.8, 5.1, 5.2, 5.4_

  - [x] 27.3 Create PaymentFilters.tsx component
    - Use Select component from shared UI library for status, payment_mode, payment_type filters
    - Use DateRangePicker component for date filtering
    - Use Input component for search by reference_no
    - Use Checkbox component for has_unallocated filter
    - Implement filter state management
    - Add "Clear Filters" button
    - Follow patterns from existing filter components
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 9.3, 9.6_

  - [x] 27.4 Create PaymentForm.tsx component
    - Use Form components from shared UI library
    - Add fields: payment_type (Select), party_id (Select with search), amount (Input), currency_code (Select), payment_date (DatePicker), payment_mode (Select), reference_no (Input, conditional)
    - Use usePaymentValidation hook for validation
    - Show/hide reference_no field based on payment_mode
    - Display validation errors inline
    - Disable submit button when validation fails
    - _Requirements: 1.1, 1.2, 1.3, 1.7, 1.8, 1.9, 13.1, 13.2, 13.3, 13.6_

  - [x] 27.5 Create PaymentDialog.tsx component
    - Use Dialog component from shared UI library
    - Integrate PaymentForm component
    - Support create and edit modes
    - Call createPayment or updatePayment mutation on submit
    - Show success/error toast notifications
    - Close dialog on success
    - Follow patterns from AccountDialog.tsx
    - _Requirements: 1.1, 5.2, 20.1, 20.4_

  - [ ]* 27.6 Write component tests
    - Create test files co-located with components:
      - `horizon-sync/apps/inventory/src/app/components/payments/PaymentManagement.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/PaymentTable.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/PaymentFilters.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/PaymentForm.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/PaymentDialog.test.tsx`
    - Test PaymentManagement rendering and interactions
    - Test PaymentTable sorting and actions
    - Test PaymentFilters state management
    - Test PaymentForm validation
    - Test PaymentDialog create and edit modes

- [x] 28. Checkpoint - Verify core components
  - Test components in browser with seeded data
  - Verify UI matches design patterns from existing components
  - Verify all interactions work correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 15: Invoice Allocation Components

- [ ] 29. Implement invoice allocation and linking components
  - [x] 29.1 Create InvoiceLinker.tsx component
    - Use DataTable component for invoice list
    - Display columns: invoice_number, invoice_date, total_amount, outstanding_balance, allocated_amount (input)
    - Filter invoices by status (Unpaid, Partially_Paid) and party_id
    - Add Input field for allocated_amount per invoice
    - Calculate and display remaining unallocated amount in real-time
    - Validate total allocations do not exceed payment amount
    - Validate individual allocations do not exceed invoice outstanding balance
    - Use useInvoiceAllocations hook
    - Add "Save Allocations" button
    - Show validation errors
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.7, 2.8, 9.1, 9.4_

  - [x] 29.2 Create AllocationList.tsx component
    - Display list of existing allocations for a payment
    - Show invoice_number, allocated_amount, invoice_currency
    - Add "Remove" button for each allocation (draft payments only)
    - Calculate and display total allocated amount
    - Use Badge component for invoice status
    - _Requirements: 2.5, 2.7, 9.2_

  - [x] 29.3 Create helper utility calculateUnallocatedAmount()
    - Accept payment amount and allocations array
    - Calculate sum of allocated amounts
    - Return payment amount minus total allocated
    - Export from utility file for reuse
    - _Requirements: 2.8, 9.1_

  - [x] 29.4 Create helper utility validateAllocation()
    - Accept allocation amount, payment unallocated amount, invoice outstanding balance
    - Validate allocation > 0
    - Validate allocation <= unallocated amount
    - Validate allocation <= outstanding balance
    - Return validation result with error messages
    - Export from utility file for reuse
    - _Requirements: 2.3, 2.4, 13.3_

  - [ ]* 29.5 Write component tests
    - Create test files co-located with components:
      - `horizon-sync/apps/inventory/src/app/components/payments/InvoiceLinker.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/AllocationList.test.tsx`
    - Test InvoiceLinker invoice filtering
    - Test InvoiceLinker allocation validation
    - Test InvoiceLinker unallocated amount calculation
    - Test AllocationList rendering and removal
    - Test helper utilities

  - [ ]* 29.6 Write property test for invoice filtering
    - **Property 7: Invoice Filtering for Allocation**
    - **Validates: Requirements 2.1**
    - Test that only Unpaid and Partially_Paid invoices for same party are displayed

- [ ] 30. Checkpoint - Verify allocation components
  - Test invoice linking with various scenarios
  - Verify validation prevents invalid allocations
  - Verify unallocated amount calculation is correct
  - Ensure all tests pass, ask the user if questions arise



### Phase 16: Payment Detail and Receipt Components

- [x] 31. Implement payment detail and receipt viewing components
  - [x] 31.1 Create PaymentDetailDialog.tsx component
    - Use Dialog component from shared UI library
    - Display payment information section (amount, date, mode, status, party, reference_no)
    - Display allocated invoices section using AllocationList component
    - Display unallocated amount if > 0
    - Display journal entry reference link
    - Display audit trail section with timeline
    - Add action buttons: Edit (draft only), Confirm (draft only), Cancel (confirmed only), Download Receipt (confirmed only)
    - Use Tabs component for organizing sections
    - Follow patterns from AccountDetailDialog.tsx
    - _Requirements: 2.7, 3.8, 7.1, 7.2, 7.3, 9.2, 14.6_

  - [x] 31.2 Create AuditTrail.tsx component
    - Display audit log entries in timeline format
    - Show action, user, timestamp, old/new values
    - Use Timeline or List component from shared UI library
    - Format timestamps in user's timezone
    - Highlight important actions (CONFIRM, CANCEL)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.7_

  - [x] 31.3 Create ReceiptViewer.tsx component
    - Use Dialog component for receipt preview
    - Display receipt content: organization details, party details, payment info, allocated invoices, unallocated amount
    - Show QR code for verification
    - Add "Download PDF" button
    - Add "Print" button
    - Use downloadReceipt API utility
    - Format currency amounts properly
    - _Requirements: 14.3, 14.4, 14.5, 14.6, 14.7, 20.9_

  - [x] 31.4 Create StatusBadge.tsx helper component
    - Accept status prop (Draft, Confirmed, Cancelled)
    - Return Badge component with appropriate color
    - Draft: yellow/warning, Confirmed: green/success, Cancelled: red/destructive
    - Export for reuse across payment components
    - _Requirements: 5.1, 8.7_

  - [ ]* 31.5 Write component tests
    - Create test files co-located with components:
      - `horizon-sync/apps/inventory/src/app/components/payments/PaymentDetailDialog.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/AuditTrail.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/ReceiptViewer.test.tsx`
      - `horizon-sync/apps/inventory/src/app/components/payments/StatusBadge.test.tsx`
    - Test PaymentDetailDialog rendering for different statuses
    - Test PaymentDetailDialog action buttons visibility
    - Test AuditTrail timeline rendering
    - Test ReceiptViewer content and actions
    - Test StatusBadge color mapping

- [ ] 32. Checkpoint - Verify detail and receipt components
  - Test payment detail dialog with various payment scenarios
  - Verify audit trail displays correctly
  - Test receipt download and print functionality
  - Ensure all tests pass, ask the user if questions arise



### Phase 17: Reporting Components

- [ ] 33. Implement reconciliation report components
  - [x] 33.1 Create ReconciliationReportService (backend)
    - Implement generate_report() method accepting date range, filters
    - Calculate total_payments_received, total_allocated, total_unallocated
    - Group payments by status, payment_mode
    - Include payment details and allocated invoices
    - Return report data structure
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5_

  - [x] 33.2 Create ExportService (backend)
    - Implement export_to_excel() method for reconciliation report
    - Implement export_to_pdf() method for reconciliation report
    - Use openpyxl for Excel export
    - Use reportlab for PDF export
    - Include organization branding in exports
    - _Requirements: 18.6_

  - [x] 33.3 Add report API endpoints
    - Implement GET /api/v1/payments/reports/reconciliation endpoint
    - Accept query parameters: date_from, date_to, party_id, payment_mode, status
    - Return report data as JSON
    - Implement GET /api/v1/payments/reports/reconciliation/export endpoint
    - Accept format parameter (excel, pdf)
    - Return file download
    - _Requirements: 18.1, 18.5, 18.6, 18.7_

  - [x] 33.4 Create ReconciliationReport.tsx component
    - Use Card component for report container
    - Add date range picker and filters
    - Display summary statistics (total payments, total allocated, total unallocated)
    - Use DataTable for payment list with allocations
    - Highlight payments with unallocated amounts
    - Add export buttons (Excel, PDF)
    - Use Chart component for visual summaries (optional)
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_

  - [ ]* 33.5 Write tests for reporting
    - Create test files:
      - `horizon-sync-erp-be/core-service/tests/test_reconciliation_report_service.py`
      - `horizon-sync-erp-be/core-service/tests/test_export_service_payments.py`
      - `horizon-sync/apps/inventory/src/app/components/payments/ReconciliationReport.test.tsx`
    - Test report generation with various filters
    - Test export to Excel and PDF
    - Test report calculations
    - Test ReconciliationReport component

  - [ ]* 33.6 Write property test for reconciliation report calculations
    - **Property 49: Reconciliation Report Calculations**
    - **Validates: Requirements 18.4**
    - Test that total_payments_received equals sum of payment amounts and total_allocated equals sum of allocation amounts

- [ ] 34. Checkpoint - Verify reporting components
  - Test report generation with various date ranges and filters
  - Verify export functionality works correctly
  - Verify calculations are accurate
  - Ensure all tests pass, ask the user if questions arise



### Phase 18: Integration and Routing

- [x] 35. Integrate payment components into application
  - [x] 35.1 Create PaymentsPage.tsx page component
    - Import PaymentManagement component
    - Add page title and breadcrumbs
    - Add page-level error boundary
    - Follow patterns from BooksPage.tsx
    - _Requirements: 1.1, 8.1_

  - [x] 35.2 Add payment routes to AppRoutes.tsx
    - Add route for /payments (list view)
    - Add route for /payments/:id (detail view)
    - Add route for /payments/reports/reconciliation (report view)
    - Ensure routes are protected with authentication
    - _Requirements: 1.1, 18.1_

  - [x] 35.3 Add payment navigation to sidebar/menu
    - Add "Payments" menu item under Finance section
    - Add icon for payments
    - Add "Reconciliation Report" submenu item
    - Follow existing navigation patterns
    - _Requirements: 1.1, 18.1_

  - [x] 35.4 Export payment API utilities from api.ts
    - Export all payment API functions from utility/api.ts
    - Ensure consistent API interface
    - Follow patterns from existing API exports
    - _Requirements: 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8, 20.9_

  - [ ]* 35.5 Write integration tests
    - Create test file: `horizon-sync/apps/inventory/e2e/payments-integration.spec.ts`
    - Test navigation to payment pages
    - Test complete payment workflow (create → allocate → confirm)
    - Test error handling across components

- [ ] 36. Checkpoint - Verify integration
  - Test navigation to all payment pages
  - Test complete payment workflows end-to-end
  - Verify error boundaries work correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 19: Performance Optimization

- [ ] 37. Optimize performance for production
  - [x] 37.1 Add database query optimization
    - Review and optimize N+1 query issues with eager loading
    - Add database query logging to identify slow queries
    - Verify all indexes are being used effectively
    - Add query result caching where appropriate
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

  - [x] 37.2 Add frontend performance optimization
    - Implement React.memo for expensive components
    - Use useMemo for expensive calculations (unallocated amount)
    - Use useCallback for event handlers
    - Implement virtual scrolling for large payment lists
    - Add loading skeletons for better perceived performance
    - _Requirements: 19.1, 19.2, 19.4_

  - [x] 37.3 Add API response caching
    - Implement Redis caching for frequently accessed data
    - Cache payment list results with appropriate TTL
    - Cache invoice lists for allocation
    - Invalidate cache on data changes
    - _Requirements: 19.2, 19.4_

  - [ ]* 37.4 Write performance tests
    - Create test file: `horizon-sync-erp-be/core-service/tests/test_payment_performance.py`
    - Test payment creation time (< 500ms)
    - Test invoice loading time (< 300ms for 1000 invoices)
    - Test journal posting time (< 1s)
    - Test payment list loading time (< 400ms for 50 entries)
    - Test report generation time (< 5s for 10000 payments)

  - [ ]* 37.5 Write property test for performance requirements
    - **Property 19.1-19.5: Performance Requirements**
    - **Validates: Requirements 19.1, 19.2, 19.3, 19.4, 19.5**
    - Test that operations complete within specified time limits

- [ ] 38. Checkpoint - Verify performance
  - Run performance tests and verify all pass
  - Profile slow operations and optimize
  - Verify caching works correctly
  - Ensure all tests pass, ask the user if questions arise



### Phase 20: Additional Features

- [ ] 39. Implement supplier payments and special scenarios
  - [ ] 39.1 Add supplier payment support
    - Verify payment_type field supports "Supplier_Payment"
    - Update PaymentForm to show supplier selector when payment_type is "Supplier_Payment"
    - Update InvoiceLinker to show supplier invoices for supplier payments
    - Verify JournalPostingService handles supplier payment journal entries correctly
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7_

  - [ ] 39.2 Add overpayment handling
    - Allow allocations that exceed invoice amount
    - Update InvoiceStatusService to set status to "Overpaid"
    - Display overpayment_amount in invoice detail
    - Add customer overpayment balance calculation
    - _Requirements: 16.1, 16.2, 16.3, 16.4_

  - [ ] 39.3 Add refund payment support
    - Allow negative amounts for refund payments
    - Update JournalPostingService to reverse debit/credit for refunds
    - Add "Refund" payment type option in UI
    - _Requirements: 16.5, 16.6_

  - [ ] 39.4 Add multi-currency support
    - Display payment currency and base currency amounts
    - Show exchange rate in allocation details
    - Calculate allocated_amount_invoice_currency when currencies differ
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7_

  - [ ]* 39.5 Write tests for additional features
    - Add tests to existing test files in `horizon-sync-erp-be/core-service/tests/`
    - Test supplier payment flow
    - Test overpayment scenarios
    - Test refund payment creation
    - Test multi-currency allocations

  - [ ]* 39.6 Write property tests for additional features
    - **Property 41: Supplier Payment Validation**
    - **Property 42: Supplier Payment Invoice Filtering**
    - **Property 43: Supplier Payment Journal Entry Structure**
    - **Property 44: Overpayment Allocation**
    - **Property 45: Customer Overpayment Balance Calculation**
    - **Property 46: Refund Payment Reversal**
    - **Property 28: Multi-Currency Exchange Rate Recording**

- [ ] 40. Checkpoint - Verify additional features
  - Test supplier payment flow end-to-end
  - Test overpayment and refund scenarios
  - Test multi-currency payments
  - Ensure all tests pass, ask the user if questions arise



### Phase 21: End-to-End Testing

- [ ] 41. Comprehensive end-to-end testing
  - [ ] 41.1 Write E2E tests for customer payment flow
    - Create test file: `horizon-sync/apps/inventory/e2e/payments-customer-flow.spec.ts`
    - Test create draft payment
    - Test allocate to single invoice
    - Test allocate to multiple invoices
    - Test confirm payment
    - Test download receipt
    - Test cancel payment
    - Verify invoice status updates
    - Verify journal entries created
    - _Requirements: All customer payment requirements_

  - [ ] 41.2 Write E2E tests for supplier payment flow
    - Create test file: `horizon-sync/apps/inventory/e2e/payments-supplier-flow.spec.ts`
    - Test create supplier payment
    - Test allocate to supplier invoices
    - Test confirm supplier payment
    - Verify journal entries for supplier payments
    - _Requirements: All supplier payment requirements_

  - [ ] 41.3 Write E2E tests for error scenarios
    - Create test file: `horizon-sync/apps/inventory/e2e/payments-error-scenarios.spec.ts`
    - Test validation errors in payment form
    - Test allocation exceeding payment amount
    - Test allocation exceeding invoice balance
    - Test confirm without allocations
    - Test modify confirmed payment (should fail)
    - Test multi-tenancy isolation
    - _Requirements: All validation requirements_

  - [ ] 41.4 Write E2E tests for special scenarios
    - Create test file: `horizon-sync/apps/inventory/e2e/payments-special-scenarios.spec.ts`
    - Test unallocated payment confirmation
    - Test overpayment scenario
    - Test refund payment
    - Test multi-currency payment
    - Test batch payment processing
    - _Requirements: 9.5, 16.1, 16.5, 10.1, 17.1_

  - [ ] 41.5 Write E2E tests for reporting
    - Create test file: `horizon-sync/apps/inventory/e2e/payments-reporting.spec.ts`
    - Test reconciliation report generation
    - Test report filtering
    - Test report export to Excel
    - Test report export to PDF
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6_

- [ ] 42. Checkpoint - Verify E2E tests
  - Run all E2E tests and verify they pass
  - Fix any issues found during E2E testing
  - Ensure all tests pass, ask the user if questions arise



### Phase 22: Documentation and Deployment

- [ ] 43. Create documentation and prepare for deployment
  - [ ] 43.1 Write API documentation
    - Document all API endpoints with request/response examples
    - Document authentication and authorization
    - Document error codes and messages
    - Add OpenAPI/Swagger documentation
    - _Requirements: 20.1-20.11_

  - [ ] 43.2 Write user guide
    - Document how to create payments
    - Document how to allocate payments to invoices
    - Document how to confirm and cancel payments
    - Document how to generate receipts
    - Document how to use reconciliation reports
    - Add screenshots and examples
    - _Requirements: All user-facing requirements_

  - [ ] 43.3 Write developer guide
    - Document architecture and design decisions
    - Document database schema
    - Document service layer structure
    - Document how to extend the system (e.g., add new payment gateways)
    - Document testing strategy
    - _Requirements: All requirements_

  - [ ] 43.4 Create deployment checklist
    - Database migration steps
    - Environment variable configuration
    - Default account configuration requirements
    - Seed data setup
    - Performance tuning recommendations
    - Monitoring and alerting setup
    - _Requirements: All requirements_

  - [ ] 43.5 Prepare for deployment
    - Run all migrations on staging environment
    - Run seed data script on staging
    - Verify all features work on staging
    - Run performance tests on staging
    - Get user acceptance sign-off
    - _Requirements: All requirements_

- [ ] 44. Final checkpoint - Ready for production
  - All tests passing (unit, integration, E2E, property-based)
  - All documentation complete
  - Staging environment validated
  - User acceptance testing complete
  - Performance requirements met
  - Ready for production deployment

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP delivery
- Each phase should be independently testable and deployable
- Checkpoints ensure incremental validation and allow for user feedback
- Property tests validate universal correctness properties across all input scenarios
- Integration tests validate complete workflows across components
- Follow existing patterns from Chart of Accounts and Purchase Orders implementations
- Use existing shared UI components to maintain consistency
- Create reusable hooks and utilities for code reuse
- Implement comprehensive error handling and validation
- Ensure multi-tenancy isolation at all layers
- Optimize for performance from the start

## Implementation Order Summary

1. **Phase 1-2**: Database and schemas (backend foundation)
2. **Phase 3**: Repository layer (data access)
3. **Phase 4-6**: Core services (business logic)
4. **Phase 7-8**: Journal posting and status transitions (integration)
5. **Phase 9**: Receipt and batch processing (additional services)
6. **Phase 10**: API endpoints (backend complete)
7. **Phase 11**: Data seeding (testing infrastructure)
8. **Phase 12-13**: Frontend types and hooks (frontend foundation)
9. **Phase 14-16**: Core UI components (user interface)
10. **Phase 17**: Reporting (analytics)
11. **Phase 18**: Integration and routing (frontend complete)
12. **Phase 19**: Performance optimization (production ready)
13. **Phase 20**: Additional features (supplier, overpayment, refund, multi-currency)
14. **Phase 21**: E2E testing (quality assurance)
15. **Phase 22**: Documentation and deployment (production release)

Each phase builds on previous phases and can be checked in independently, allowing for continuous integration and early feedback.
