# Implementation Plan

## Phase 1: Bug Condition Exploration Tests (BEFORE Fix)

- [ ] 1. Write bug condition exploration tests for all three bugs
  - **Property 1: Fault Condition** - Missing Invoice Journal Entries, Generic Bank Account Usage, and Outstanding Amount Updates
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failure confirms the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **NOTE**: These tests encode the expected behavior - they will validate the fix when they pass after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bugs exist
  - **Scoped PBT Approach**: For deterministic bugs, scope properties to concrete failing cases to ensure reproducibility

  - [x] 1.1 Bug 1 Exploration: Missing Invoice Journal Entries
    - Test that confirming a sales invoice (status "draft" → "submitted") creates journal entry with Debit AR, Credit Revenue
    - Test that confirming a purchase invoice (status "draft" → "submitted") creates journal entry with Debit Expense, Credit AP
    - Test that invoice.submitted_at is set when status changes to "submitted"
    - Test that invoice.outstanding_amount equals grand_total after confirmation
    - Run tests on UNFIXED code
    - **EXPECTED OUTCOME**: Tests FAIL (no journal entries created, submitted_at not set, outstanding_amount not initialized)
    - Document counterexamples: "Sales invoice INV-001 confirmed but no journal entry exists in journal_entries table"
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.11_

  - [x] 1.2 Bug 2 Exploration: Generic Bank Account Usage
    - Test that customer payment with payment_mode "Bank_Transfer" and bank_account_id uses specific bank account's gl_account_id (not generic "bank" account)
    - Test that supplier payment with payment_mode "Bank_Transfer" and bank_account_id uses specific bank account's gl_account_id
    - Note: PaymentEntry model may not have bank_account_id field yet - test will fail at model level
    - Run tests on UNFIXED code
    - **EXPECTED OUTCOME**: Tests FAIL (PaymentEntry has no bank_account_id field, or journal entries use generic "bank" account)
    - Document counterexamples: "Payment PAY-001 to HDFC account uses generic 'bank' account instead of HDFC's gl_account_id"
    - _Requirements: 2.5, 2.6, 2.7_

  - [x] 1.3 Bug 3 Exploration: Outstanding Amount Not Updated
    - Test that allocating payment to invoice updates invoice.outstanding_amount to (grand_total - total_allocated)
    - Test that cancelling payment allocation increases invoice.outstanding_amount
    - Test that multiple partial payments correctly update outstanding_amount
    - Run tests on UNFIXED code
    - **EXPECTED OUTCOME**: Tests FAIL (outstanding_amount not updated after payment allocation)
    - Document counterexamples: "Invoice INV-001 with grand_total $1000, payment allocated $300, but outstanding_amount still shows $1000"
    - _Requirements: 2.12, 2.13_

## Phase 2: Preservation Property Tests (BEFORE Fix)

- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Bank_Transfer Payment Behavior, Draft Invoice Operations, and Invoice Status Transitions
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code

  - [x] 2.1 Preservation: Cash and Check Payment Flows
    - Observe: Customer payment with payment_mode "Cash" creates journal entry debiting "cash" default account, crediting AR
    - Observe: Customer payment with payment_mode "Check" creates journal entry debiting "checks_received" default account, crediting AR
    - Observe: Supplier payment with payment_mode "Cash" creates journal entry debiting AP, crediting "cash" default account
    - Observe: Supplier payment with payment_mode "Check" creates journal entry debiting AP, crediting "checks_received" default account
    - Write property-based test: for all payments with payment_mode in ["Cash", "Check"], journal entries use appropriate default accounts
    - Verify test passes on UNFIXED code
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 2.2 Preservation: Draft Invoice Operations
    - Observe: Creating draft invoice does not create journal entries
    - Observe: Updating draft invoice does not create journal entries
    - Observe: Deleting draft invoice does not affect journal entries
    - Write property-based test: for all invoices with status "draft", CRUD operations do not create journal entries
    - Verify test passes on UNFIXED code
    - _Requirements: 3.6, 3.7, 3.8_

  - [x] 2.3 Preservation: Invoice Status Transitions
    - Observe: Invoice status changes from "submitted" to "paid" when fully paid (via InvoiceStatusService)
    - Observe: Invoice status changes from "submitted" to "partial" when partially paid
    - Observe: Updating already-submitted invoice (changing remarks) does not create duplicate journal entries
    - Write property-based test: for all invoice status transitions due to payment allocations, status updates automatically without duplicate journal entries
    - Verify test passes on UNFIXED code
    - _Requirements: 3.9, 3.10_

  - [x] 2.4 Preservation: Default Account Validation and Journal Entry Structure
    - Observe: Attempting to confirm invoice without default accounts raises ValidationError
    - Observe: Journal entries validate debits equal credits
    - Observe: Foreign currency amounts convert to base currency
    - Observe: Journal entries include reference_type, reference_id, against_account_id, remarks
    - Write property-based test: for all journal entry operations, validation and structure requirements are enforced
    - Verify test passes on UNFIXED code
    - _Requirements: 3.11, 3.12, 3.13, 3.14, 3.15_

## Phase 3: Database Schema Changes

- [ ] 3. Add bank_account_id field to PaymentEntry model

  - [x] 3.1 Update PaymentEntry model
    - File: `horizon-sync-erp-be/core-service/app/models/payment_entry.py`
    - Add bank_account_id column (UUID, nullable, foreign key to bank_accounts.id)
    - Add relationship to BankAccount model
    - Update __repr__ to include bank_account_id
    - _Requirements: 2.7_

  - [x] 3.2 Create Alembic migration
    - Generate migration: `alembic revision --autogenerate -m "add_bank_account_id_to_payment_entries"`
    - Review migration file to ensure correct column definition
    - Add index on bank_account_id for query performance
    - _Requirements: 2.7_

  - [x] 3.3 Run migration in development environment
    - Execute: `alembic upgrade head`
    - Verify column added successfully
    - Test rollback: `alembic downgrade -1` then `alembic upgrade head`
    - _Requirements: 2.7_

## Phase 4: Service Layer - Invoice Journal Posting

- [ ] 4. Create InvoiceJournalPostingService (NEW FILE)

  - [x] 4.1 Create service file and class structure
    - File: `horizon-sync-erp-be/core-service/app/services/invoice_journal_posting_service.py`
    - Create InvoiceJournalPostingService class
    - Add __init__ method with db session dependency
    - Import required dependencies (DefaultAccountService, JournalEntryService, CurrencyService)
    - _Requirements: 2.1, 2.2_

  - [x] 4.2 Implement _validate_invoice_default_accounts method
    - Validate required default accounts exist for invoice type
    - Sales: accounts_receivable, sales_revenue
    - Purchase: purchase_expense, accounts_payable
    - Raise ValidationError with helpful message if accounts missing
    - _Requirements: 2.1, 2.2_

  - [x] 4.3 Implement _convert_to_base_currency method
    - Accept amount, from_currency, organization_id parameters
    - Use CurrencyService to convert to organization's base currency
    - Handle conversion errors gracefully
    - Return converted amount
    - _Requirements: 2.1, 2.2_

  - [x] 4.4 Implement post_invoice_journal_entry method for sales invoices
    - Accept invoice, organization_id, user_id parameters
    - Validate default accounts configured
    - Convert invoice.grand_total to base currency
    - Build journal entry data:
      - Debit: Accounts Receivable (from DefaultAccountService)
      - Credit: Sales Revenue (from DefaultAccountService)
      - Amount: converted grand_total
      - Reference: reference_type="Invoice", reference_id=invoice.id
      - Remarks: "Invoice confirmation for {invoice_no}"
    - Validate debits equal credits
    - Call JournalEntryService.create()
    - Return journal entry
    - _Requirements: 2.1_

  - [x] 4.5 Implement post_invoice_journal_entry method for purchase invoices
    - Same structure as 4.4 but with different accounts:
      - Debit: Purchase Expense (from DefaultAccountService)
      - Credit: Accounts Payable (from DefaultAccountService)
    - _Requirements: 2.2_

  - [x] 4.6 Add error handling and logging
    - Wrap journal entry creation in try-except
    - Log errors with invoice details
    - Re-raise exceptions for transaction rollback
    - _Requirements: 2.1, 2.2_

  - [x] 4.7 Write unit tests for InvoiceJournalPostingService
    - Test post_invoice_journal_entry for sales invoices
    - Test post_invoice_journal_entry for purchase invoices
    - Test _validate_invoice_default_accounts with missing accounts
    - Test _convert_to_base_currency with foreign currency
    - Test error handling for invalid invoice types
    - _Requirements: 2.1, 2.2_

## Phase 5: Service Layer - Invoice Confirmation

- [ ] 5. Add confirm_invoice method to InvoiceService

  - [x] 5.1 Implement confirm_invoice method
    - File: `horizon-sync-erp-be/core-service/app/services/invoice_service.py`
    - Accept invoice_id, organization_id, user_id parameters
    - Validate invoice exists and belongs to organization
    - Validate invoice.status == "draft" (raise ValidationError if not)
    - Update invoice fields:
      - status = "submitted"
      - submitted_at = current datetime
      - outstanding_amount = grand_total
    - Call InvoiceJournalPostingService.post_invoice_journal_entry()
    - Commit transaction
    - Return updated invoice
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.11_

  - [x] 5.2 Add transaction management
    - Wrap all operations in database transaction
    - If journal entry creation fails, rollback invoice status change
    - Re-raise exception to caller
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.3 Add validation and error handling
    - Validate invoice_type in ["Sales", "Purchase"]
    - Validate grand_total > 0
    - Handle ResourceNotFoundException if invoice not found
    - Handle ValidationError from journal posting service
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 5.4 Write unit tests for confirm_invoice
    - Test confirm_invoice success path for sales invoice
    - Test confirm_invoice success path for purchase invoice
    - Test confirm_invoice with already-submitted invoice (should fail)
    - Test confirm_invoice with missing default accounts (should fail)
    - Test confirm_invoice transaction rollback on journal entry failure
    - Test that submitted_at is set correctly
    - Test that outstanding_amount equals grand_total
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.11_

## Phase 6: API Layer - Invoice Confirmation Endpoint

- [ ] 6. Create invoice confirmation endpoint

  - [x] 6.1 Create POST /api/v1/invoices/{invoice_id}/confirm endpoint
    - File: `horizon-sync-erp-be/core-service/app/api/v1/endpoints/invoices.py`
    - Path parameter: invoice_id (UUID)
    - Extract organization_id from current user context
    - Extract user_id from current user context
    - Call InvoiceService.confirm_invoice()
    - Return updated invoice with 200 status
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 6.2 Add error handling
    - Handle ResourceNotFoundException with 404 status
    - Handle ValidationError with 400 status (include helpful error message)
    - Handle general exceptions with 500 status
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 6.3 Add authorization
    - Require appropriate permissions to confirm invoices
    - Validate user has access to organization
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [x] 6.4 Update response schema
    - Ensure InvoiceResponse includes submitted_at field
    - Ensure InvoiceResponse includes outstanding_amount field
    - _Requirements: 2.4, 2.11_

  - [x] 6.5 Write integration tests for confirmation endpoint
    - Test POST /api/v1/invoices/{invoice_id}/confirm success
    - Test confirmation with invalid invoice_id (404)
    - Test confirmation with already-submitted invoice (400)
    - Test confirmation without default accounts (400)
    - Test confirmation without proper permissions (403)
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

## Phase 7: Service Layer - Payment Bank Account Integration

- [ ] 7. Update JournalPostingService for bank account support

  - [x] 7.1 Update _get_payment_account_by_mode method signature
    - File: `horizon-sync-erp-be/core-service/app/services/journal_posting_service.py`
    - Add optional bank_account_id parameter (UUID | None = None)
    - _Requirements: 2.5, 2.6, 2.8_

  - [x] 7.2 Implement bank account logic in _get_payment_account_by_mode
    - If payment_mode == "Bank_Transfer" AND bank_account_id is not None:
      - Query BankAccount model by bank_account_id
      - Validate bank_account exists (raise ResourceNotFoundException if not)
      - Validate bank_account.organization_id == organization_id (raise ValidationError if not)
      - Validate bank_account.is_active == True (raise ValidationError if not)
      - Return bank_account.gl_account_id
    - Else if payment_mode == "Bank_Transfer" AND bank_account_id is None:
      - Fall back to generic "bank" default account (backward compatibility)
      - Get default account for transaction_type="bank"
      - Return default_account.account_id
    - Else (Cash, Check):
      - Existing logic unchanged
      - Get default account for transaction_type="cash" or "checks_received"
      - Return default_account.account_id
    - _Requirements: 2.5, 2.6, 2.8_

  - [x] 7.3 Update post_payment_journal_entry method
    - Pass payment_entry.bank_account_id to _get_payment_account_by_mode()
    - No other changes needed (method already uses _get_payment_account_by_mode)
    - _Requirements: 2.5, 2.6_

  - [x] 7.4 Verify reverse_payment_journal_entry works correctly
    - No code changes needed (it retrieves and reverses original journal entry)
    - Verify that if original entry used specific bank account, reversal uses same account
    - _Requirements: 2.9, 2.10_

  - [x] 7.5 Write unit tests for updated JournalPostingService
    - Test _get_payment_account_by_mode with bank_account_id (returns specific gl_account_id)
    - Test _get_payment_account_by_mode without bank_account_id (returns generic "bank" account)
    - Test _get_payment_account_by_mode with inactive bank account (raises ValidationError)
    - Test _get_payment_account_by_mode with bank account from different org (raises ValidationError)
    - Test _get_payment_account_by_mode with non-existent bank_account_id (raises ResourceNotFoundException)
    - Test post_payment_journal_entry with bank_account_id
    - Test reverse_payment_journal_entry with bank_account_id
    - _Requirements: 2.5, 2.6, 2.8, 2.9, 2.10_

## Phase 8: Schema Layer - Payment Entry Schemas

- [x] 8. Update payment entry schemas to include bank_account_id

  - [x] 8.1 Update PaymentEntryCreate schema
    - File: `horizon-sync-erp-be/core-service/app/schemas/payment_entry.py`
    - Add bank_account_id field (Optional[UUID] = None)
    - Add field description: "ID of the bank account used for Bank_Transfer payments"
    - _Requirements: 2.7_

  - [x] 8.2 Update PaymentEntryUpdate schema
    - Add bank_account_id field (Optional[UUID] = None)
    - _Requirements: 2.7_

  - [x] 8.3 Update PaymentEntryResponse schema
    - Add bank_account_id field (Optional[UUID] = None)
    - Add nested bank_account object (Optional[BankAccountBasic] = None)
    - BankAccountBasic should include: bank_name, masked_account_number, gl_account_id
    - _Requirements: 2.7_

  - [x] 8.4 Create BankAccountBasic schema (if not exists)
    - Include fields: id, bank_name, masked_account_number, gl_account_id
    - Used for nested representation in PaymentEntryResponse
    - _Requirements: 2.7_

## Phase 9: API Layer - Payment Entry Endpoints

- [x] 9. Update payment entry endpoints to accept bank_account_id

  - [x] 9.1 Update payment creation endpoint
    - File: `horizon-sync-erp-be/core-service/app/api/v1/endpoints/payment_entries.py`
    - Accept bank_account_id in request body (optional)
    - If bank_account_id provided, validate bank account exists
    - Validate bank_account.organization_id == current_user.organization_id
    - Validate bank_account.is_active == True
    - If payment_mode != "Bank_Transfer" and bank_account_id provided, raise ValidationError
    - Pass bank_account_id to PaymentEntryService.create()
    - _Requirements: 2.5, 2.6, 2.7, 2.8_

  - [x] 9.2 Update payment update endpoint
    - Accept bank_account_id in request body (optional)
    - Same validation as 9.1
    - Pass bank_account_id to PaymentEntryService.update()
    - _Requirements: 2.5, 2.6, 2.7, 2.8_

  - [x] 9.3 Update payment response to include bank_account details
    - Ensure response includes bank_account_id
    - Ensure response includes nested bank_account object with basic details
    - _Requirements: 2.7_

  - [x] 9.4 Write integration tests for payment endpoints with bank_account_id
    - Test creating customer payment with bank_account_id
    - Test creating supplier payment with bank_account_id
    - Test creating payment with invalid bank_account_id (404)
    - Test creating payment with bank_account from different org (403)
    - Test creating payment with inactive bank_account (400)
    - Test creating Cash payment with bank_account_id (400 - should fail)
    - Test creating Bank_Transfer payment without bank_account_id (success - backward compatibility)
    - _Requirements: 2.5, 2.6, 2.7, 2.8_

## Phase 10: Service Layer - Outstanding Amount Updates

- [x] 10. Fix InvoiceStatusService to update outstanding_amount

  - [x] 10.1 Update update_invoice_status method
    - File: `horizon-sync-erp-be/core-service/app/services/invoice_status_service.py`
    - After calculating outstanding_balance, add line: `invoice.outstanding_amount = outstanding_balance`
    - Ensure invoice is committed to database
    - _Requirements: 2.12, 2.13_

  - [x] 10.2 Write unit tests for outstanding_amount update
    - Test update_invoice_status updates outstanding_amount correctly
    - Test with no allocations (outstanding_amount == grand_total)
    - Test with partial allocations (outstanding_amount == grand_total - total_allocated)
    - Test with full payment (outstanding_amount == 0)
    - Test with overpayment (outstanding_amount < 0)
    - _Requirements: 2.12, 2.13_

  - [x] 10.3 Verify automatic trigger on payment allocation
    - Verify PaymentReferenceService.create() calls InvoiceStatusService.update_invoice_status()
    - Verify PaymentReferenceService.delete() calls InvoiceStatusService.update_invoice_status()
    - If not present, add these calls
    - _Requirements: 2.12, 2.13_

## Phase 11: Implementation Complete - Verify Bug Condition Tests Pass

- [x] 11. Re-run bug condition exploration tests (from Phase 1)

  - [x] 11.1 Verify Bug 1 exploration tests now pass
    - **Property 1: Expected Behavior** - Invoice Journal Entries Created on Confirmation
    - **IMPORTANT**: Re-run the SAME tests from task 1.1 - do NOT write new tests
    - The tests from task 1.1 encode the expected behavior
    - When these tests pass, it confirms the expected behavior is satisfied
    - Run bug condition exploration tests for invoice confirmation
    - **EXPECTED OUTCOME**: Tests PASS (journal entries created, submitted_at set, outstanding_amount initialized)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.11_

  - [x] 11.2 Verify Bug 2 exploration tests now pass
    - **Property 1: Expected Behavior** - Specific Bank Account Used in Payment Journal Entries
    - **IMPORTANT**: Re-run the SAME tests from task 1.2 - do NOT write new tests
    - Run bug condition exploration tests for bank account usage
    - **EXPECTED OUTCOME**: Tests PASS (PaymentEntry has bank_account_id field, journal entries use specific bank account's gl_account_id)
    - _Requirements: 2.5, 2.6, 2.7, 2.8_

  - [x] 11.3 Verify Bug 3 exploration tests now pass
    - **Property 1: Expected Behavior** - Outstanding Amount Updated on Payment Allocation
    - **IMPORTANT**: Re-run the SAME tests from task 1.3 - do NOT write new tests
    - Run bug condition exploration tests for outstanding amount updates
    - **EXPECTED OUTCOME**: Tests PASS (outstanding_amount updated after payment allocation and cancellation)
    - _Requirements: 2.12, 2.13_

  - [x] 11.4 Verify preservation tests still pass
    - **Property 2: Preservation** - All Preservation Requirements
    - **IMPORTANT**: Re-run the SAME tests from Phase 2 - do NOT write new tests
    - Run all preservation property tests from Phase 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm Cash/Check payment flows unchanged
    - Confirm draft invoice operations unchanged
    - Confirm invoice status transitions unchanged
    - Confirm default account validation unchanged
    - _Requirements: 3.1-3.15_

## Phase 12: End-to-End Integration Tests

- [x] 12. Write and run end-to-end integration tests

  - [x] 12.1 End-to-end sales invoice flow
    - Create draft sales invoice
    - Confirm invoice → Verify journal entry created (Debit AR, Credit Revenue)
    - Verify submitted_at timestamp set
    - Verify outstanding_amount equals grand_total
    - Create customer payment with bank_account_id → Verify journal entry created (Debit Bank GL Account, Credit AR)
    - Allocate payment to invoice → Verify outstanding_amount updated, status changed to "paid"
    - Verify journal entries are correct and debits equal credits
    - _Requirements: 2.1, 2.3, 2.4, 2.5, 2.11, 2.12_

  - [x] 12.2 End-to-end purchase invoice flow
    - Create draft purchase invoice
    - Confirm invoice → Verify journal entry created (Debit Expense, Credit AP)
    - Verify submitted_at timestamp set
    - Verify outstanding_amount equals grand_total
    - Create supplier payment with bank_account_id → Verify journal entry created (Debit AP, Credit Bank GL Account)
    - Allocate payment to invoice → Verify outstanding_amount updated, status changed to "paid"
    - Verify journal entries are correct and debits equal credits
    - _Requirements: 2.2, 2.3, 2.4, 2.6, 2.11, 2.12_

  - [x] 12.3 Payment cancellation flow
    - Create invoice and confirm it
    - Create payment with bank_account_id and allocate to invoice
    - Cancel payment → Verify reversing entry created using specific bank account's gl_account_id
    - Verify outstanding_amount restored to original value
    - Verify invoice status changed back to "submitted"
    - _Requirements: 2.9, 2.10, 2.13_

  - [x] 12.4 Multi-currency flow
    - Create sales invoice in EUR with grand_total €800
    - Confirm invoice → Verify journal entry uses base currency (USD) amount
    - Create payment in EUR with bank_account_id
    - Allocate payment → Verify outstanding_amount calculated correctly in base currency
    - _Requirements: 2.1, 2.5, 2.12_

  - [x] 12.5 Partial payment flow
    - Create invoice with grand_total $1,000
    - Confirm invoice
    - Create and allocate payment $300 → Verify outstanding_amount = $700, status = "partial"
    - Create and allocate payment $400 → Verify outstanding_amount = $300, status = "partial"
    - Create and allocate payment $300 → Verify outstanding_amount = $0, status = "paid"
    - _Requirements: 2.11, 2.12_

  - [x] 12.6 Error handling flow
    - Attempt to confirm invoice without default accounts → Verify ValidationError with helpful message
    - Attempt to create payment with inactive bank account → Verify ValidationError
    - Attempt to allocate payment exceeding unallocated amount → Verify ValidationError
    - Simulate journal entry creation failure → Verify invoice status not changed (transaction rollback)
    - _Requirements: 2.1, 2.2, 2.5, 2.6_

## Phase 13: Data Migration (Optional)

- [ ] 13. Create data migration scripts for historical data

  - [ ] 13.1 Create backfill script for invoice journal entries
    - File: `horizon-sync-erp-be/core-service/scripts/backfill_invoice_journal_entries.py`
    - Identify all invoices with status in ["submitted", "paid", "partial"] without journal entries
    - For each invoice, create journal entry using InvoiceJournalPostingService logic
    - Use invoice.submitted_at or invoice.posting_date as posting_date
    - Add remark: "Backfilled journal entry for historical invoice"
    - Run in transaction with rollback on any error
    - Log progress and any errors
    - _Note: This is optional - discuss with stakeholders before running_

  - [ ] 13.2 Create recalculation script for outstanding amounts
    - File: `horizon-sync-erp-be/core-service/scripts/recalculate_outstanding_amounts.py`
    - Iterate through all invoices with status in ["submitted", "paid", "partial"]
    - For each invoice, call InvoiceStatusService.update_invoice_status()
    - This recalculates outstanding_amount and status based on current payment allocations
    - Run in transaction with rollback on any error
    - Log progress and any errors
    - _Note: This is recommended to correct any incorrect outstanding amounts_

  - [ ] 13.3 Test migration scripts in staging environment
    - Run backfill_invoice_journal_entries.py in staging
    - Verify journal entries created correctly
    - Verify debits equal credits for all backfilled entries
    - Run recalculate_outstanding_amounts.py in staging
    - Verify outstanding amounts corrected
    - Generate financial reports and compare with pre-migration reports
    - Document any discrepancies

  - [ ] 13.4 Create rollback plan for migrations
    - Document how to delete backfilled journal entries (by remarks containing "Backfilled")
    - Document how to restore outstanding amounts from backup (if needed)
    - Test rollback in staging environment

## Phase 14: Documentation and Deployment

- [ ] 14. Finalize documentation and deploy

  - [x] 14.1 Update API documentation
    - Document new POST /api/v1/invoices/{invoice_id}/confirm endpoint
    - Document bank_account_id parameter in payment endpoints
    - Document error responses and validation rules
    - Update OpenAPI/Swagger specs

  - [ ] 14.2 Update user documentation
    - Document invoice confirmation workflow
    - Document bank account selection in payment flow
    - Document outstanding amount tracking
    - Create user guide with screenshots

  - [ ] 14.3 Create release notes
    - Document all three bug fixes
    - Explain impact on financial reports
    - Document backward compatibility (Bank_Transfer without bank_account_id)
    - Document data migration options
    - Include cutover date for bank account tracking

  - [ ] 14.4 Deploy to staging environment
    - Run database migrations
    - Deploy code changes
    - Run smoke tests
    - Verify all tests pass

  - [ ] 14.5 Deploy to production
    - Schedule maintenance window if running data migrations
    - Run database migrations
    - Deploy code changes
    - Run smoke tests
    - Monitor error logs for any issues
    - Verify financial reports are accurate

## Phase 15: Checkpoint

- [ ] 15. Final checkpoint - Ensure all tests pass and system is stable
  - Verify all unit tests pass
  - Verify all integration tests pass
  - Verify all property-based tests pass
  - Verify all end-to-end tests pass
  - Generate financial reports and verify accuracy
  - Monitor production for any issues
  - Ask the user if questions arise or if additional changes are needed
