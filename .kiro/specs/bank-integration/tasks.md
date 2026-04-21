# Implementation Plan: Bank Integration Module

## Overview

This plan implements a comprehensive banking layer for the ERP system following the Shadow Ledger pattern. The implementation uses Python/FastAPI for backend services and React/TypeScript for frontend components. The system maintains three distinct layers: Raw (bank_transactions), Reconciliation (bank_reconciliations), and Final (journal_entries).

## Tasks

- [x] 1. Set up database schema and models
  - [x] 1.1 Create bank_accounts table with encryption support
    - Create SQLAlchemy model with all fields (account_number, iban, routing_number, swift_code, etc.)
    - Add foreign key to accounts table (GL_Account)
    - Implement unique constraint on organization_id and iban
    - Add indexes for organization_id, gl_account_id, and is_active
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12_
  
  - [ ]* 1.2 Write property test for bank_accounts table structure
    - **Property 1: Default Bank Account Creation**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**
  
  - [x] 1.3 Create bank_transactions table
    - Create SQLAlchemy model with foreign key to bank_accounts
    - Add fields: statement_date, transaction_amount, transaction_description, bank_reference
    - Add status field with enum: pending, cleared, reconciled, void
    - Add type field with enum: debit, credit
    - Add indexes for organization_id, bank_account_id, statement_date, status, and bank_reference
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11_
  
  - [x] 1.4 Create bank_reconciliations table
    - Create SQLAlchemy model with foreign keys to bank_transactions and journal_entries
    - Add reconciliation_type enum: manual, auto_exact, auto_fuzzy, many_to_one
    - Add reconciliation_status enum: suggested, confirmed, rejected
    - Add match_confidence decimal field (0.00 to 1.00)
    - Add exchange_rate and converted_amount for multi-currency support
    - Add unique constraint on bank_transaction_id and journal_entry_id where is_active = TRUE
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10_
  
  - [x] 1.5 Create bank_account_history table
    - Create SQLAlchemy model with foreign key to bank_accounts
    - Add action_type enum: created, updated, activated, deactivated
    - Add JSONB fields for old_values and new_values
    - Add audit fields: changed_by, changed_at, reason
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8_
  
  - [ ]* 1.6 Write property test for Shadow Ledger isolation
    - **Property 28: Shadow Ledger Isolation**
    - **Validates: Requirements 14.1, 14.2**

- [x] 2. Implement encryption service
  - [x] 2.1 Create EncryptionService class with AES-256
    - Implement encrypt_field and decrypt_field methods using cryptography.fernet
    - Use PBKDF2 key derivation from master key
    - Store master key in environment variables
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6_
  
  - [x] 2.2 Implement field masking methods
    - Implement mask_account_number (show last 4 digits)
    - Implement mask_iban (show first 4 and last 4 characters)
    - _Requirements: 15.7, 15.8_
  
  - [ ]* 2.3 Write property test for encryption round-trip
    - **Property 33: Sensitive Field Encryption**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**
  
  - [ ]* 2.4 Write property tests for masking
    - **Property 34: Account Number Masking**
    - **Property 35: IBAN Masking**
    - **Validates: Requirements 15.7, 15.8**

- [x] 3. Implement country validation service
  - [x] 3.1 Create CountryValidator class with validation rules
    - Define COUNTRY_BANKING_RULES configuration for US, GB, DE, IN, AU
    - Implement validate_banking_info method
    - Implement get_required_fields and get_field_patterns methods
    - Return descriptive error messages for validation failures
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10_
  
  - [ ]* 3.2 Write property tests for country-specific validation
    - **Property 3: US Banking Validation**
    - **Property 4: EU Banking Validation**
    - **Property 5: India Banking Validation**
    - **Property 6: UK Banking Validation**
    - **Property 7: Australia Banking Validation**
    - **Property 8: Validation Error Messages**
    - **Validates: Requirements 5.1-5.10**

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement Bank Account Manager service
  - [x] 5.1 Create BankAccountManager class
    - Implement create_bank_account method with encryption and validation
    - Implement create_default_bank_account method with skip_on_error flag
    - Implement update_bank_account method with history tracking
    - Implement deactivate_bank_account method
    - Implement get_bank_account_history method
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 2.1-2.12_
  
  - [x] 5.2 Implement audit trail for bank account changes
    - Create history records on create, update, activate, deactivate
    - Store old_values and new_values as JSON
    - Prevent deletion or modification of history records
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 18.9, 18.10_
  
  - [ ]* 5.3 Write property test for default bank account creation
    - **Property 1: Default Bank Account Creation**
    - **Property 2: Default Bank Account Creation Failure Handling**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.7**
  
  - [ ]* 5.4 Write property tests for audit trail
    - **Property 38: Bank Account History Creation**
    - **Property 39: Bank Account History Content**
    - **Property 40: Bank Account History Immutability**
    - **Validates: Requirements 18.1-18.10**

- [x] 6. Implement Transaction Importer service
  - [x] 6.1 Create TransactionImporter class with CSV support
    - Implement import_csv method
    - Validate required columns: date, amount, description, reference, type
    - Validate date format (ISO 8601), amount format (numeric with 2 decimals), type values
    - Create bank_transaction records with status "cleared"
    - Return import summary with imported, skipped, and failed counts
    - _Requirements: 11.1, 11.3, 11.4, 11.5, 11.6, 11.11, 11.12, 11.15_
  
  - [x] 6.2 Implement duplicate detection
    - Check for existing transactions with same bank_account_id, statement_date, transaction_amount, bank_reference
    - Skip duplicates and log warnings
    - Support force import with is_duplicate flag
    - _Requirements: 11.13, 11.14, 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7, 20.8_
  
  - [ ]* 6.3 Write property tests for CSV import
    - **Property 20: CSV Column Validation**
    - **Property 21: CSV Data Validation**
    - **Property 22: Import Status Assignment**
    - **Property 23: Import Validation Error Reporting**
    - **Property 24: Duplicate Transaction Detection**
    - **Property 25: Duplicate Transaction Handling**
    - **Property 26: Force Import Duplicate Flagging**
    - **Validates: Requirements 11.3-11.15, 20.1-20.8**
  
  - [x] 6.3 Implement PDF import support
    - Implement import_pdf method using PyPDF2 or pdfplumber
    - Extract text and parse transaction data using regex patterns
    - Detect transaction type from amount sign or column position
    - Handle multi-page statements
    - Return error if PDF format not supported
    - _Requirements: 11.2, 11.7, 11.8, 11.9, 11.10, 11.16, 11.17_
  
  - [x] 6.4 Implement MT940 import support
    - Implement import_mt940 method
    - Parse opening balance (:60F:), transactions (:61:), details (:86:), closing balance (:62F:)
    - Extract statement_date, transaction_amount, transaction_description, transaction_type
    - Create bank_transaction records with status "cleared"
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 12.10, 12.11_
  
  - [ ]* 6.5 Write property test for MT940 parsing
    - **Property 27: MT940 Parsing Round-Trip**
    - **Validates: Requirements 12.1-12.11**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement Auto-Reconciliation Service
  - [x] 8.1 Create AutoReconciliationService class
    - Implement run_auto_reconciliation method
    - Filter bank transactions with status "cleared" and reconciled_at is null
    - _Requirements: 8.1_
  
  - [x] 8.2 Implement exact match algorithm
    - Implement find_exact_matches method
    - Match on: amount equals exactly, date equals exactly, reference equals exactly
    - Create reconciliation with type "auto_exact", status "confirmed", confidence 1.0
    - Update bank transaction status to "reconciled"
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.10_
  
  - [ ]* 8.3 Write property test for exact match reconciliation
    - **Property 11: Auto-Reconciliation Filtering**
    - **Property 12: Exact Match Reconciliation**
    - **Validates: Requirements 8.1-8.10**
  
  - [x] 8.4 Implement fuzzy match algorithm
    - Implement find_fuzzy_matches method
    - Match criteria: amount equals exactly (required), date within 3 days, reference partial match
    - Calculate confidence: 0.8 for amount + date, 0.95 for amount + date + reference
    - Create reconciliation with type "auto_fuzzy", status "suggested"
    - Do not update bank transaction status
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 9.8, 9.9, 9.10_
  
  - [ ]* 8.5 Write property tests for fuzzy match reconciliation
    - **Property 13: Fuzzy Match Confidence Calculation (Date + Amount)**
    - **Property 14: Fuzzy Match Confidence Calculation (Date + Amount + Reference)**
    - **Property 15: Fuzzy Match Status**
    - **Validates: Requirements 9.1-9.10**
  
  - [x] 8.6 Implement many-to-one detection algorithm
    - Implement find_many_to_one_matches method
    - Find combinations of journal entries within 7-day date range that sum to bank transaction amount
    - Use subset sum algorithm with 0.01 tolerance
    - _Requirements: 10.10_
  
  - [ ]* 8.7 Write property test for many-to-one detection
    - **Property 19: Many-to-One Auto-Detection**
    - **Validates: Requirements 10.10**

- [x] 9. Implement Reconciliation Engine service
  - [x] 9.1 Create ReconciliationEngine class
    - Implement get_unreconciled_transactions method
    - Implement get_unreconciled_journal_entries method
    - Implement calculate_reconciliation_difference method
    - _Requirements: 14.8, 14.9_
  
  - [x] 9.2 Implement manual reconciliation
    - Implement create_manual_match method
    - Check if transaction already reconciled (prevent double reconciliation)
    - Create reconciliation with type "manual", status "confirmed"
    - Update bank transaction status to "reconciled"
    - Set reconciled_at and reconciled_by
    - Support notes parameter
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10_
  
  - [ ]* 9.3 Write property tests for manual reconciliation
    - **Property 9: Manual Reconciliation Creation**
    - **Property 10: Prevent Double Reconciliation**
    - **Validates: Requirements 7.3-7.10**
  
  - [x] 9.4 Implement many-to-one reconciliation
    - Implement create_many_to_one_match method
    - Calculate sum of selected journal entries
    - Validate sum equals bank transaction amount (with 0.01 tolerance)
    - Create multiple reconciliation records with type "many_to_one"
    - Update bank transaction status to "reconciled"
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9_
  
  - [ ]* 9.5 Write property tests for many-to-one reconciliation
    - **Property 16: Many-to-One Sum Calculation**
    - **Property 17: Many-to-One Amount Matching**
    - **Property 18: Many-to-One Reconciliation Creation**
    - **Validates: Requirements 10.1-10.9**
  
  - [x] 9.6 Implement reconciliation undo
    - Implement undo_reconciliation method
    - Update reconciliation status to "rejected"
    - Update bank transaction status back to "cleared"
    - Set reconciled_at and reconciled_by to null
    - Preserve reconciliation record (do not delete)
    - Log undo action with user and timestamp
    - Check 90-day restriction for non-elevated users
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 17.9, 17.10_
  
  - [ ]* 9.7 Write property tests for reconciliation undo
    - **Property 36: Reconciliation Undo State Reversion**
    - **Property 37: Reconciliation Undo Time Restriction**
    - **Validates: Requirements 17.1-17.10**
  
  - [x] 9.8 Implement multi-currency reconciliation
    - Implement reconcile_with_currency_conversion method
    - Require exchange_rate parameter when currencies differ
    - Calculate converted_amount as transaction_amount × exchange_rate
    - Validate converted amount matches journal entry amount within 0.01 tolerance
    - Store exchange_rate in reconciliation record
    - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8, 19.9, 19.10_
  
  - [ ]* 9.9 Write property tests for multi-currency reconciliation
    - **Property 41: Transaction Currency Inheritance**
    - **Property 42: Cross-Currency Reconciliation Exchange Rate Requirement**
    - **Property 43: Currency Conversion Calculation**
    - **Property 44: Currency Conversion Tolerance Matching**
    - **Property 45: Exchange Rate Persistence**
    - **Validates: Requirements 19.1-19.10**
  
  - [x] 9.10 Implement balance calculations
    - Implement calculate_bank_balance method (from bank_transactions)
    - Implement calculate_gl_balance method (from journal_entries)
    - Implement calculate_unreconciled_amount method (difference between balances)
    - _Requirements: 14.8, 14.9_
  
  - [ ]* 9.11 Write property test for balance calculations
    - **Property 31: Balance Calculation Separation**
    - **Validates: Requirements 14.8, 14.9**
  
  - [x] 9.12 Implement reconciled transaction deletion prevention
    - Add check in delete methods to prevent deletion of reconciled transactions
    - _Requirements: 14.10_
  
  - [ ]* 9.13 Write property test for deletion prevention
    - **Property 32: Reconciled Transaction Deletion Prevention**
    - **Validates: Requirements 14.10**
  
  - [x] 9.14 Implement confirm and reject suggested matches
    - Implement confirm_suggested_match method
    - Implement reject_suggested_match method
    - Update reconciliation status and bank transaction status accordingly
    - _Requirements: 9.10_
  
  - [ ]* 9.15 Write property tests for reconciliation linking
    - **Property 29: Reconciliation Linking (Not Creation)**
    - **Property 30: Reconciliation Status Update**
    - **Validates: Requirements 14.3, 14.4, 14.5**

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Implement Banking API Service stubs
  - [x] 11.1 Create BankingAPIProvider abstract base class
    - Define abstract methods: authenticate, fetch_transactions, fetch_balance
    - _Requirements: 13.1_
  
  - [x] 11.2 Create PlaidProvider stub implementation
    - Implement stub methods that raise NotImplementedError
    - Document expected credentials: client_id, secret, access_token
    - _Requirements: 13.2, 13.4_
  
  - [x] 11.3 Create SaltEdgeProvider stub implementation
    - Implement stub methods that raise NotImplementedError
    - Document expected credentials: app_id, secret, customer_id
    - _Requirements: 13.3, 13.5_
  
  - [x] 11.4 Add API integration fields to bank_accounts
    - Add bank_api_enabled, bank_api_credentials_id, last_sync_date fields
    - _Requirements: 13.6, 13.7, 13.8, 13.9, 13.10_

- [x] 12. Implement backend API endpoints
  - [x] 12.1 Create bank account endpoints
    - POST /api/bank-accounts - create bank account
    - GET /api/bank-accounts - list bank accounts
    - GET /api/bank-accounts/{id} - get bank account details
    - PUT /api/bank-accounts/{id} - update bank account
    - DELETE /api/bank-accounts/{id} - deactivate bank account
    - GET /api/bank-accounts/{id}/history - get audit history
    - _Requirements: 1.1-1.8, 2.1-2.12, 18.1-18.10_
  
  - [x] 12.2 Create transaction import endpoints
    - POST /api/bank-accounts/{id}/import/csv - import CSV file
    - POST /api/bank-accounts/{id}/import/pdf - import PDF file
    - POST /api/bank-accounts/{id}/import/mt940 - import MT940 file
    - GET /api/bank-accounts/{id}/transactions - list transactions
    - _Requirements: 11.1-11.17, 12.1-12.11_
  
  - [x] 12.3 Create reconciliation endpoints
    - GET /api/reconciliations/unreconciled-transactions - list unreconciled transactions
    - GET /api/reconciliations/unreconciled-journal-entries - list unreconciled journal entries
    - POST /api/reconciliations/manual - create manual reconciliation
    - POST /api/reconciliations/many-to-one - create many-to-one reconciliation
    - POST /api/reconciliations/auto-run - run auto-reconciliation
    - POST /api/reconciliations/{id}/confirm - confirm suggested match
    - POST /api/reconciliations/{id}/reject - reject suggested match
    - POST /api/reconciliations/{id}/undo - undo reconciliation
    - GET /api/reconciliations/suggested - list suggested matches
    - _Requirements: 7.1-7.10, 8.1-8.10, 9.1-9.10, 10.1-10.10, 17.1-17.10_
  
  - [x] 12.4 Create reporting endpoints
    - GET /api/reconciliations/report - generate reconciliation report
    - GET /api/reconciliations/report/export/csv - export report to CSV
    - GET /api/reconciliations/report/export/pdf - export report to PDF
    - GET /api/bank-accounts/{id}/balance - get bank and GL balances
    - _Requirements: 16.1-16.10_

- [x] 13. Implement frontend components - Bank Account Management
  - [x] 13.1 Create BankAccountForm component (React/TypeScript)
    - Implement country selector dropdown
    - Implement dynamic field display based on country selection
    - Show US fields (routing_number, account_number) for country_code "US"
    - Show EU fields (iban, swift_code) for EU countries
    - Show India fields (ifsc_code, account_number) for country_code "IN"
    - Show UK fields (sort_code, account_number) for country_code "GB"
    - Show Australia fields (bsb_number, account_number) for country_code "AU"
    - Clear country-specific fields when country changes
    - Implement real-time validation using country validation rules
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8_
  
  - [x] 13.2 Create BankAccountList component
    - Display list of bank accounts with masked sensitive fields
    - Show account_holder_name, bank_name, masked account_number, currency, status
    - Implement filter by status (active/inactive)
    - Implement actions: view, edit, deactivate
    - _Requirements: 2.1-2.12, 15.7, 15.8_
  
  - [x] 13.3 Create BankAccountDetail component
    - Display full bank account details with masked sensitive fields
    - Show audit history timeline
    - Implement "View Full Account Number" with permission check
    - _Requirements: 15.7, 15.8, 15.9, 15.10, 18.9_

- [x] 14. Implement frontend components - Transaction Import
  - [x] 14.1 Create TransactionImportDialog component
    - Implement file upload for CSV, PDF, MT940 formats
    - Display file format instructions
    - Show import progress indicator
    - Display import summary (imported, skipped, failed counts)
    - Show validation errors with row and column details
    - Show duplicate warnings with option to force import
    - _Requirements: 11.1-11.17, 12.1-12.11, 20.1-20.8_
  
  - [x] 14.2 Create TransactionList component
    - Display list of bank transactions
    - Show statement_date, amount, description, reference, status, type
    - Implement filter by status (pending, cleared, reconciled, void)
    - Implement filter by date range
    - Implement sort by date, amount
    - Highlight duplicates with is_duplicate flag
    - _Requirements: 3.1-3.11_

- [x] 15. Implement frontend components - Reconciliation Interface
  - [x] 15.1 Create ReconciliationWorkspace component
    - Display two-panel layout: unreconciled transactions on left, unreconciled journal entries on right
    - Implement date range filter
    - Implement bank account selector
    - Show bank balance, GL balance, and unreconciled amount
    - _Requirements: 7.1, 7.2, 14.8, 14.9_
  
  - [x] 15.2 Create ManualReconciliationDialog component
    - Allow selection of one bank transaction and one or more journal entries
    - Display selected items with amounts
    - Calculate and display sum of journal entries
    - Show difference if sum doesn't match bank transaction amount
    - Implement notes field
    - Implement confirm button (enabled only when amounts match)
    - _Requirements: 7.3-7.10, 10.1-10.9_
  
  - [x] 15.3 Create SuggestedMatchesList component
    - Display list of suggested matches from auto-reconciliation
    - Show match confidence score
    - Show matching criteria (amount, date, reference)
    - Implement actions: confirm, reject
    - _Requirements: 9.1-9.10_
  
  - [x] 15.4 Create ReconciliationHistoryList component
    - Display list of reconciliations with status
    - Show reconciliation_type, reconciled_by, reconciled_at
    - Implement undo action with confirmation dialog
    - Show undo history (rejected reconciliations)
    - _Requirements: 17.1-17.10_
  
  - [x] 15.5 Create AutoReconciliationButton component
    - Implement "Run Auto-Reconciliation" button
    - Show progress indicator during execution
    - Display results summary (exact matches, fuzzy matches, many-to-one matches)
    - _Requirements: 8.1-8.10, 9.1-9.10, 10.10_

- [x] 16. Implement frontend components - Reporting
  - [x] 16.1 Create ReconciliationReport component
    - Display reconciliation report with filters (bank_account, date_range, status)
    - Show transaction list with columns: date, amount, description, status, matched_journal_entry
    - Display summary: total_imported, total_reconciled, total_unreconciled
    - Group transactions by status
    - Implement export buttons (CSV, PDF)
    - Show report generation timestamp and generated_by
    - _Requirements: 16.1-16.10_

- [x] 17. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 18. Integration and wiring
  - [x] 18.1 Wire backend services together
    - Connect BankAccountManager with EncryptionService and CountryValidator
    - Connect TransactionImporter with duplicate detection
    - Connect ReconciliationEngine with AutoReconciliationService
    - Add error handling and logging throughout
    - _Requirements: All_
  
  - [x] 18.2 Wire frontend components with API
    - Connect all forms to backend endpoints
    - Implement error handling and user feedback
    - Add loading states and progress indicators
    - Implement permission checks for sensitive operations
    - _Requirements: All_
  
  - [x] 18.3 Add default bank account creation to organization setup
    - Integrate create_default_bank_account into organization creation flow
    - Add optional step in organization setup wizard
    - Implement skip option
    - Handle creation failures gracefully
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8_
  
  - [ ]* 18.4 Write integration tests for end-to-end flows
    - Test complete flow: create bank account → import transactions → auto-reconcile → manual reconcile → undo
    - Test multi-currency reconciliation flow
    - Test many-to-one reconciliation flow
    - Test duplicate detection and force import flow

- [x] 19. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- The implementation follows the Shadow Ledger pattern: bank transactions remain isolated until explicitly reconciled
- Encryption is applied at the application level before database storage
- All sensitive operations require audit logging
- Multi-currency support is built into the reconciliation engine
- The system supports three reconciliation types: manual, auto-exact, auto-fuzzy, and many-to-one
