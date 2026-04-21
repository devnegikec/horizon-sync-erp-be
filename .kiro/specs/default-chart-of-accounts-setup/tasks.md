# Implementation Plan: Default Chart of Accounts Setup

## Overview

This implementation creates automatic default chart of accounts creation when organizations are registered. The feature involves service-to-service communication between the Identity Service and Core Service, with a focus on reliability, idempotency, and graceful error handling.

The implementation follows a layered approach: Core Service components first (API, service, repository), then Identity Service integration, followed by comprehensive testing including property-based tests for universal correctness properties.

## Tasks

- [x] 1. Set up Core Service foundation for default chart creation
  - [x] 1.1 Create request/response schemas for chart setup API
    - Create `DefaultChartSetupRequest` schema with organization_id, currency, created_by fields
    - Create `DefaultChartSetupResponse` schema with success, accounts_created, mappings_created fields
    - Create `ManualTriggerRequest` schema with currency and force_recreate fields
    - Create `DefaultChartResult` internal model for service layer
    - Add Pydantic validators for currency code format (3 uppercase letters)
    - _Requirements: 5.3, 5.4, 8.1_
  
  - [x] 1.2 Create default account structure template
    - Define `AccountTemplate` dataclass with account_code, account_name, account_type, parent_code, is_group, is_posting_account, description, level fields
    - Implement `get_default_account_structure()` function returning list of 25+ standard accounts
    - Include accounts for all five account types (ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE)
    - Follow standard numbering scheme: 1000-1999 ASSET, 2000-2999 LIABILITY, 3000-3999 EQUITY, 4000-4999 REVENUE, 5000-5999 EXPENSE
    - Include hierarchical structure with parent-child relationships
    - Cache the template using `@lru_cache` for performance
    - _Requirements: 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 9.2_
  
  - [x] 1.3 Create default account mappings configuration
    - Define `DEFAULT_MAPPINGS` dictionary with transaction type mappings
    - Include mappings for payment_cash, payment_bank, accounts_receivable, accounts_payable, sales_revenue, purchase_expense
    - Map each transaction type to appropriate account code from default structure
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

- [x] 2. Implement Core Service repository layer extensions
  - [x] 2.1 Extend AccountRepository with helper methods
    - Add `check_default_accounts_exist()` method to check for existing default accounts
    - Add `get_accounts_by_codes()` method to retrieve accounts by code list
    - Use existing `create()` method for account creation
    - Use existing `get_by_code()` method for lookups
    - _Requirements: 1.4, 6.1, 9.1_
  
  - [ ]* 2.2 Write unit tests for repository extensions
    - Test default accounts existence check
    - Test get accounts by codes
    - _Requirements: 1.4, 6.1, 9.1_

- [x] 3. Implement Core Service default chart setup service
  - [x] 3.1 Create DefaultChartSetupService class
    - Initialize with database session
    - Inject existing AccountRepository, ChartOfAccountService, and DefaultAccountService
    - _Requirements: 1.1_
  
  - [x] 3.2 Implement create_default_chart_of_accounts method
    - Check if default accounts already exist using AccountRepository (idempotency)
    - If exists, return existing accounts without creating duplicates
    - Begin database transaction
    - Create accounts using existing ChartOfAccountService.create() method
    - Create accounts in dependency order (parents before children)
    - Create default account mappings using existing DefaultAccountService.set_default_account() method
    - Commit transaction
    - Log creation event with structured logging
    - Handle errors with rollback
    - Return DefaultChartResult with accounts, mappings, already_existed flag
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 6.1, 6.2, 10.1_
  
  - [x] 3.3 Implement currency validation and handling
    - Validate currency code format (3 uppercase letters)
    - Default to USD if currency not specified or invalid
    - Apply same currency to all created accounts
    - Log warnings for invalid currency codes
    - _Requirements: 1.6, 8.1, 8.2, 8.3_
  
  - [x] 3.4 Implement hierarchical account creation
    - Sort account templates by level to ensure parents created first
    - Track created accounts by code for parent reference lookup
    - Pass parent_account_id when creating child accounts via ChartOfAccountService
    - Validate parent exists before creating child
    - _Requirements: 2.6_
  
  - [ ]* 3.5 Write unit tests for DefaultChartSetupService
    - Test successful chart creation with all account types
    - Test idempotency (multiple calls don't create duplicates)
    - Test currency validation and defaulting
    - Test hierarchical account creation order
    - Test transaction rollback on partial failure
    - Test default mappings creation using DefaultAccountService
    - Mock ChartOfAccountService and DefaultAccountService for isolated testing
    - _Requirements: 1.1, 1.2, 6.1, 6.2, 8.1, 8.2_

- [x] 4. Implement Core Service chart setup API endpoints
  - [x] 4.1 Create chart_of_accounts_setup.py endpoint file
    - Create FastAPI router for chart setup endpoints
    - Add router to main API router registration
    - _Requirements: 1.1_
  
  - [x] 4.2 Implement POST /api/v1/setup/default-chart-of-accounts endpoint
    - Accept DefaultChartSetupRequest in request body
    - Inject database session dependency
    - Call DefaultChartSetupService.create_default_chart_of_accounts()
    - Return DefaultChartSetupResponse with creation results
    - Handle exceptions and return appropriate error responses
    - Return 200 OK for both new creation and already exists cases
    - _Requirements: 1.1, 5.1, 5.4, 6.1_
  
  - [x] 4.3 Implement POST /api/v1/setup/default-chart-of-accounts/{organization_id}/trigger endpoint
    - Accept organization_id as path parameter
    - Accept ManualTriggerRequest in request body
    - Require admin permissions using dependency
    - Support force_recreate option to delete and recreate accounts
    - Call DefaultChartSetupService.create_default_chart_of_accounts()
    - Return DefaultChartSetupResponse with creation results
    - _Requirements: 6.4_
  
  - [ ]* 4.4 Write integration tests for chart setup API
    - Test POST /setup/default-chart-of-accounts with valid request
    - Test idempotent behavior (calling twice returns success)
    - Test manual trigger endpoint with admin permissions
    - Test manual trigger with force_recreate option
    - Test error responses for invalid requests
    - Use test database with rollback after each test
    - _Requirements: 1.1, 5.4, 6.1, 6.4_

- [x] 5. Checkpoint - Verify Core Service implementation
  - Ensure all Core Service tests pass
  - Verify API endpoints are registered and accessible
  - Test chart creation manually using API client
  - Ask the user if questions arise

- [x] 6. Implement Identity Service HTTP client for Core Service
  - [x] 6.1 Create CoreServiceClient class
    - Initialize with base_url and timeout configuration
    - Use httpx.AsyncClient for async HTTP requests
    - Implement `create_default_chart_of_accounts()` method
    - Accept organization_id, currency, created_by parameters
    - Make POST request to Core Service chart setup endpoint
    - Return response dictionary with success status and counts
    - Raise httpx.RequestError for connection failures
    - Raise httpx.HTTPStatusError for HTTP error responses
    - _Requirements: 5.1, 5.3_
  
  - [x] 6.2 Add Core Service configuration to Identity Service settings
    - Add CORE_SERVICE_URL environment variable
    - Add CORE_SERVICE_TIMEOUT environment variable (default 10 seconds)
    - Add ENABLE_AUTO_CHART_CREATION feature flag (default true)
    - Add CHART_CREATION_RETRY_ATTEMPTS configuration (default 3)
    - Update Settings class in config.py
    - _Requirements: 5.1_
  
  - [ ]* 6.3 Write unit tests for CoreServiceClient
    - Test successful chart creation request
    - Test connection error handling
    - Test HTTP error response handling
    - Test timeout handling
    - Mock httpx responses for isolated testing
    - _Requirements: 5.1, 5.2_

- [x] 7. Integrate chart creation into Identity Service organization creation
  - [x] 7.1 Modify OrganizationService to trigger chart creation
    - Inject CoreServiceClient into OrganizationService
    - After organization creation and role assignment, call core_client.create_default_chart_of_accounts()
    - Pass organization_id, base_currency, and owner_id to client
    - Use try-except to catch and log errors without failing organization creation
    - Log success with organization_id and creation counts
    - Log errors with organization_id, error type, and error message
    - Use structured logging with extra fields for searchability
    - _Requirements: 1.1, 5.1, 5.2, 6.3, 10.1_
  
  - [x] 7.2 Implement retry logic with exponential backoff
    - Create `create_with_retry()` helper method in CoreServiceClient
    - Retry up to CHART_CREATION_RETRY_ATTEMPTS times
    - Use exponential backoff: 1s, 2s, 4s between retries
    - Log each retry attempt with attempt number
    - Return None if all retries fail
    - Call from OrganizationService after organization creation
    - _Requirements: 5.2_
  
  - [ ]* 7.3 Write integration tests for organization creation flow
    - Test organization creation triggers chart creation
    - Test organization creation succeeds when Core Service unavailable
    - Test organization creation succeeds when chart creation fails
    - Test retry logic with transient failures
    - Test logging of success and failure events
    - Mock CoreServiceClient for controlled testing
    - _Requirements: 1.1, 5.1, 5.2, 6.3_

- [x] 8. Implement database migrations and indexes
  - [x] 8.1 Create Alembic migration for performance indexes
    - Add index on accounts(organization_id, account_code) for faster lookups
    - Add index on default_accounts(organization_id, transaction_type) for faster queries
    - No schema changes needed (using existing tables)
    - _Requirements: Performance optimization_
  
  - [x] 8.2 Verify migration runs successfully
    - Run migration on test database
    - Verify indexes created correctly
    - Test rollback functionality
    - _Requirements: Performance optimization_

- [x] 9. Implement audit logging and monitoring
  - [x] 9.1 Add structured logging throughout chart creation flow
    - Log chart_creation_initiated event in Identity Service
    - Log chart_creation_started event in Core Service
    - Log chart_creation_completed event with duration and counts
    - Log chart_creation_failed event with error details
    - Include organization_id, currency, created_by in all log entries
    - Use ISO 8601 timestamps
    - _Requirements: 10.1, 10.3_
  
  - [x] 9.2 Add audit log entries for created accounts
    - Create AccountAuditLog entry for each created account
    - Set action to CREATE
    - Include account details in changes field
    - Set source to "default_chart_setup" for traceability
    - _Requirements: 10.1, 10.2, 10.3_
  
  - [ ]* 9.3 Write tests for audit logging
    - Test audit log entries created for each account
    - Test structured log format and fields
    - Test log entries include required information
    - Verify timestamps populated correctly
    - _Requirements: 10.1, 10.2, 10.3_

- [x] 10. Checkpoint - Verify end-to-end integration
  - Test complete flow: organization creation → chart creation
  - Verify accounts created with correct structure
  - Verify default mappings created
  - Verify audit logs captured
  - Test failure scenarios and recovery
  - Ask the user if questions arise

- [ ] 11. Write property-based tests for correctness properties
  - [ ]* 11.1 Write property test for Property 2: Complete Account Type Coverage
    - **Property 2: Complete Account Type Coverage**
    - **Validates: Requirements 1.2, 1.3, 3.1, 3.2**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - Verify at least one account of each type (ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE)
    - Verify at least one ASSET account suitable for bank linking
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.2 Write property test for Property 3: Account Code Uniqueness
    - **Property 3: Account Code Uniqueness**
    - **Validates: Requirements 1.4, 9.1**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - Verify all account codes are unique within organization
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.3 Write property test for Property 4: Active Status Invariant
    - **Property 4: Active Status Invariant**
    - **Validates: Requirements 1.5**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - Verify all created accounts have status = ACTIVE
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.4 Write property test for Property 5: Currency Consistency
    - **Property 5: Currency Consistency**
    - **Validates: Requirements 1.6, 8.1, 8.3**
    - Generate random organization_id and currency from common currencies
    - Create default chart of accounts
    - Verify all accounts use the same currency
    - Verify currency matches the specified currency
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.5 Write property test for Property 6: Hierarchical Integrity
    - **Property 6: Hierarchical Integrity**
    - **Validates: Requirements 2.6**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - For each account with parent_account_id, verify parent exists
    - Verify parent account has is_group = true
    - Verify parent is in same organization
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.6 Write property test for Property 7: Default Mappings Creation
    - **Property 7: Default Mappings Creation**
    - **Validates: Requirements 4.1, 4.2**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - Verify default mappings created for payment transaction types
    - Verify each mapping references valid GL account in organization
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.7 Write property test for Property 10: Idempotency
    - **Property 10: Idempotency**
    - **Validates: Requirements 6.1**
    - Generate random organization_id and currency
    - Create default chart of accounts twice
    - Verify second call returns already_existed = true
    - Verify no duplicate accounts created
    - Verify account counts match between calls
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.8 Write property test for Property 12: Account Code Numbering Scheme
    - **Property 12: Account Code Numbering Scheme**
    - **Validates: Requirements 9.2**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - Verify ASSET accounts have codes 1000-1999
    - Verify LIABILITY accounts have codes 2000-2999
    - Verify EQUITY accounts have codes 3000-3999
    - Verify REVENUE accounts have codes 4000-4999
    - Verify EXPENSE accounts have codes 5000-5999
    - Use hypothesis with 100+ iterations
  
  - [ ]* 11.9 Write property test for Property 14: Timestamp Population
    - **Property 14: Timestamp Population**
    - **Validates: Requirements 10.2**
    - Generate random organization_id and currency
    - Create default chart of accounts
    - Verify all accounts have created_at timestamp
    - Verify all accounts have updated_at timestamp
    - Verify timestamps are valid datetime values
    - Use hypothesis with 100+ iterations

- [ ] 12. Write example-based tests for specific scenarios
  - [ ]* 12.1 Write tests for specific account structure
    - Test default chart includes Cash and Bank Accounts (1000)
    - Test default chart includes Accounts Receivable (1200)
    - Test default chart includes Accounts Payable (2000)
    - Test default chart includes Owner's Equity (3000)
    - Test default chart includes Sales Revenue (4000)
    - Test default chart includes Operating Expenses (5100)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_
  
  - [ ]* 12.2 Write tests for specific default mappings
    - Test payment_cash mapping points to account 1000
    - Test payment_bank mapping points to account 1000
    - Test accounts_receivable mapping points to account 1200
    - Test accounts_payable mapping points to account 2000
    - Test sales_revenue mapping points to account 4000
    - Test purchase_expense mapping points to account 5100
    - _Requirements: 4.3, 4.4_
  
  - [ ]* 12.3 Write tests for edge cases
    - Test missing currency defaults to USD
    - Test invalid currency code defaults to USD
    - Test manual trigger endpoint with admin permissions
    - Test manual trigger endpoint rejects non-admin users
    - Test force_recreate deletes and recreates accounts
    - _Requirements: 6.4, 8.2_
  
  - [ ]* 12.4 Write tests for error scenarios
    - Test partial failure rolls back all accounts
    - Test duplicate account code raises error
    - Test missing parent account raises error
    - Test service communication error logged but doesn't fail org creation
    - _Requirements: 5.2, 6.2, 6.3_

- [ ] 13. Final checkpoint and documentation
  - [ ] 13.1 Run all tests and verify coverage
    - Run unit tests for all components
    - Run integration tests for API endpoints
    - Run property-based tests for correctness properties
    - Run example-based tests for specific scenarios
    - Verify test coverage meets 90% threshold
    - Fix any failing tests
  
  - [ ] 13.2 Update API documentation
    - Document POST /api/v1/setup/default-chart-of-accounts endpoint
    - Document POST /api/v1/setup/default-chart-of-accounts/{organization_id}/trigger endpoint
    - Include request/response examples
    - Document error responses
    - Add to OpenAPI/Swagger documentation
  
  - [ ] 13.3 Create deployment checklist
    - Verify environment variables configured
    - Verify Core Service URL accessible from Identity Service
    - Verify database migrations applied
    - Verify feature flag settings
    - Document rollback procedure
  
  - [ ] 13.4 Final verification
    - Test complete flow in staging environment
    - Verify existing organizations unaffected
    - Verify new organizations get default chart
    - Verify manual trigger works for existing organizations
    - Ensure all tests pass, ask the user if questions arise

## Notes

- Tasks marked with `*` are optional testing tasks and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- The implementation prioritizes reliability: organization creation succeeds even if chart creation fails
- Idempotency ensures safe retries and prevents duplicate data
- Comprehensive audit logging enables troubleshooting and compliance
