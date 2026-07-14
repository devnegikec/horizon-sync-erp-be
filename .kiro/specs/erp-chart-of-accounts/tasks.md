# Implementation Plan: ERP Chart of Accounts

## Overview

This implementation plan is structured in phases where each phase delivers a testable, working feature that can be reviewed and tested from the UI independently. This approach enables smaller PRs, incremental testing, and easier peer review.

**🔍 CHECKPOINT SYSTEM:**
- Each phase ends with a clearly marked CHECKPOINT task (marked with 🔍)
- When you reach a checkpoint, PAUSE implementation
- Test all functionality from the UI as described in the checkpoint
- Run all tests (backend and frontend)
- Commit your code and optionally create a PR
- Only proceed to the next phase after successful testing

**WORKFLOW:**
1. Complete all tasks in a phase
2. Reach the checkpoint (🔍)
3. Test thoroughly from UI
4. Run test suites
5. Commit code
6. Move to next phase

The implementation follows the existing tech stack:
- **Backend**: Python with FastAPI (in horizon-sync-erp-be/core-service)
- **Frontend**: React with TypeScript (in horizon-sync/apps)
- **Database**: PostgreSQL with Alembic migrations
- **Testing**: pytest for backend, vitest for frontend, fast-check for property-based tests

## Phase 1: Basic Account Management (Backend + UI)

This phase delivers the core account CRUD operations with a working UI for creating, viewing, and managing accounts.

- [x] 1. Set up database schema and models
  - Create Alembic migration for accounts table with all fields (id, account_code, account_name, account_type, parent_account_id, currency, status, is_posting_account, description, timestamps)
  - Create SQLAlchemy model for Account entity
  - Add database indexes for account_code, account_type, parent_account_id, status
  - _Requirements: 1.1, 1.6, 3.1, 3.2_

- [x] 2. Implement account repository layer
  - Create AccountRepository class with methods: create, get_by_id, get_by_code, update, delete, list_all
  - Implement query methods with filtering support
  - Add database constraint handling for unique account codes
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3. Implement account service layer with validation
  - Create AccountService class with business logic
  - Implement account code format validation using configurable regex patterns
  - Implement field length validation (name ≤ 200 chars, code ≤ 50 chars)
  - Add validation for required fields (code, name, type)
  - Implement duplicate code detection
  - _Requirements: 1.1, 1.2, 1.6, 6.1, 6.2, 11.1, 11.2_

- [ ]* 3.1 Write property test for account creation round trip
  - **Property 1: Account creation and retrieval round trip**
  - **Validates: Requirements 1.1, 1.3**

- [ ]* 3.2 Write property test for duplicate code rejection
  - **Property 2: Duplicate account code rejection**
  - **Validates: Requirements 1.2**

- [ ]* 3.3 Write property test for account code format validation
  - **Property 4: Account code format validation**
  - **Validates: Requirements 1.6, 6.2, 6.3**

- [ ]* 3.4 Write property test for field length validation
  - **Property 33: Field length validation**
  - **Validates: Requirements 11.1, 11.2**

- [x] 4. Create REST API endpoints for account management
  - POST /api/v1/accounts - Create account
  - GET /api/v1/accounts/:id - Get account by ID
  - PUT /api/v1/accounts/:id - Update account
  - DELETE /api/v1/accounts/:id - Delete account (with transaction check)
  - GET /api/v1/accounts - List accounts with pagination
  - Add request/response schemas using Pydantic
  - Implement error handling with proper HTTP status codes
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 4.1 Write unit tests for API endpoints
  - Test successful account creation
  - Test duplicate code rejection
  - Test validation errors
  - Test account retrieval and updates

- [x] 5. Implement account status management
  - Add activate_account, deactivate_account, archive_account methods to service
  - PUT /api/v1/accounts/:id/activate endpoint
  - PUT /api/v1/accounts/:id/deactivate endpoint
  - PUT /api/v1/accounts/:id/archive endpoint
  - Implement validation to prevent posting to inactive accounts
  - _Requirements: 1.5_

- [ ]* 5.1 Write property test for account deactivation
  - **Property 3: Account deactivation prevents posting**
  - **Validates: Requirements 1.5**

- [x] 6. Create frontend account management UI
  - Create AccountManagement component in horizon-sync/apps/platform or inventory
  - Build account list view with table showing code, name, type, status
  - Add "Create Account" button and modal form
  - Implement form with fields: account code, name, type dropdown, currency dropdown, description
  - Add form validation matching backend rules
  - Integrate with backend API using fetch or axios
  - Add success/error toast notifications
  - _Requirements: 1.1, 1.3_

- [x] 7. Add account type selection and display
  - Create AccountType enum/constants (ASSET, LIABILITY, EQUITY, REVENUE, EXPENSE)
  - Add type dropdown in create/edit forms
  - Display account type badges with color coding in list view
  - Implement type-based filtering in UI
  - _Requirements: 3.1, 3.2_

- [ ]* 7.1 Write property test for account type requirement
  - **Property 11: Account type requirement**
  - **Validates: Requirements 3.2**

- [x] 8. 🔍 CHECKPOINT - Test Phase 1 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Verify account creation through UI form
  - Test duplicate code rejection shows error message
  - Test field validation (empty fields, length limits)
  - Test account list displays correctly
  - Test account editing and updates
  - Test account status changes (activate/deactivate)
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 1 code before proceeding to Phase 2**

## Phase 2: Account Hierarchy and Tree View

This phase adds parent-child relationships and hierarchical display in the UI.

- [x] 9. Implement hierarchy manager service
  - Create HierarchyManager class with methods: add_child, remove_child, move_account
  - Implement get_children, get_parent, get_ancestors, get_descendants methods
  - Add circular reference detection using graph traversal
  - Implement account path calculation (root to account)
  - Add validation for account type consistency in hierarchy
  - _Requirements: 2.1, 2.2, 2.4, 11.4_

- [ ]* 9.1 Write property test for parent-child relationship
  - **Property 5: Parent-child relationship establishment**
  - **Validates: Requirements 2.1**

- [ ]* 9.2 Write property test for account path calculation
  - **Property 6: Account path calculation**
  - **Validates: Requirements 2.2**

- [ ]* 9.3 Write property test for account type consistency
  - **Property 8: Account type consistency in hierarchy**
  - **Validates: Requirements 2.4, 3.3**

- [ ]* 9.4 Write property test for circular reference prevention
  - **Property 10: Circular reference prevention**
  - **Validates: Requirements 11.4**

- [x] 10. Add hierarchy API endpoints
  - GET /api/v1/accounts/:id/hierarchy - Get account hierarchy
  - GET /api/v1/accounts/:id/children - Get child accounts
  - GET /api/v1/accounts/:id/ancestors - Get ancestor accounts
  - GET /api/v1/accounts/:id/descendants - Get descendant accounts
  - PUT /api/v1/accounts/:id/parent - Move account to new parent
  - _Requirements: 2.1, 2.2_

- [x] 11. Implement parent account posting restriction
  - Add logic to set is_posting_account=false when account has children
  - Add validation to prevent posting transactions to parent accounts
  - Update account service to enforce this rule
  - _Requirements: 2.3_

- [ ]* 11.1 Write property test for parent posting restriction
  - **Property 7: Parent accounts cannot be posting accounts**
  - **Validates: Requirements 2.3**

- [x] 12. Create hierarchical tree view UI component
  - Create AccountTreeView component with expandable/collapsible nodes
  - Display accounts in tree structure showing parent-child relationships
  - Add indentation and visual indicators for hierarchy levels
  - Implement expand/collapse functionality
  - Show account code, name, and type in tree nodes
  - _Requirements: 2.1, 2.2_

- [x] 13. Add parent account selection in forms
  - Add parent account dropdown in create/edit forms
  - Implement parent account search/autocomplete
  - Show account hierarchy path in dropdown
  - Add validation to prevent circular references in UI
  - Display warning when selecting parent (account becomes non-posting)
  - _Requirements: 2.1, 2.4_

- [x] 14. 🔍 CHECKPOINT - Test Phase 2 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Create parent accounts and child accounts through UI
  - Verify tree view displays hierarchy correctly
  - Test expanding/collapsing tree nodes
  - Test moving accounts to different parents
  - Verify circular reference prevention
  - Test that parent accounts cannot receive transactions
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 2 code before proceeding to Phase 3**

## Phase 3: Multi-Currency Support

This phase adds currency handling, exchange rates, and currency conversion.

- [x] 15. Set up currency and exchange rate tables
  - Create Alembic migration for exchange_rates table
  - Create Alembic migration for system_config table
  - Create ExchangeRate SQLAlchemy model
  - Add indexes for currency pairs and effective dates
  - _Requirements: 4.1, 4.5_

- [x] 16. Implement currency service
  - Create CurrencyService class
  - Implement get_exchange_rate, set_exchange_rate methods
  - Implement currency conversion logic
  - Add get_base_currency, set_base_currency methods
  - Implement historical exchange rate queries
  - _Requirements: 4.1, 4.3, 4.5_

- [ ]* 16.1 Write property test for foreign currency conversion
  - **Property 15: Foreign currency conversion**
  - **Validates: Requirements 4.3**

- [ ]* 16.2 Write property test for exchange rate history
  - **Property 17: Exchange rate history preservation**
  - **Validates: Requirements 4.5**

- [x] 17. Add currency support to account service
  - Add currency validation in account creation
  - Implement dual currency balance tracking (account currency + base currency)
  - Update account repository to handle currency fields
  - _Requirements: 4.2, 11.5_

- [ ]* 17.1 Write property test for account currency specification
  - **Property 14: Account currency specification**
  - **Validates: Requirements 4.2**

- [ ]* 17.2 Write property test for currency validation
  - **Property 35: Currency validation**
  - **Validates: Requirements 11.5**

- [x] 18. Create currency management UI
  - Add currency dropdown in account create/edit forms
  - Create ExchangeRateManagement component
  - Build UI for viewing and updating exchange rates
  - Add base currency configuration in settings
  - Display currency symbols and codes properly
  - _Requirements: 4.1, 4.2_

- [x] 19. Add currency display in account views
  - Show account currency in account list and details
  - Display base currency equivalent for balances
  - Add currency filter in account list
  - Show exchange rate information in tooltips
  - _Requirements: 4.2, 4.4_

- [x] 20. 🔍 CHECKPOINT - Test Phase 3 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Create accounts with different currencies
  - Configure base currency in settings
  - Add and update exchange rates
  - Verify currency conversion calculations
  - Test currency filtering in account list
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 3 code before proceeding to Phase 4**

## Phase 4: Account Balances and Calculations

This phase implements balance tracking, calculations, and display.

- [x] 21. Set up account balances infrastructure
  - Create Alembic migration for account_balances table
  - Create AccountBalance SQLAlchemy model
  - Add indexes for account_id and as_of_date
  - Set up Redis cache configuration for balance caching
  - _Requirements: 5.1, 5.5_

- [x] 22. Implement balance calculator service
  - Create BalanceCalculator class
  - Implement calculate_balance method with natural balance direction logic
  - Implement calculate_consolidated_balance for parent accounts
  - Add balance caching logic using Redis
  - Implement cache invalidation on transaction posting
  - Add historical balance calculation (as of specific date)
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 3.5_

- [ ]* 22.1 Write property test for transaction posting updates balance
  - **Property 18: Transaction posting updates balance**
  - **Validates: Requirements 5.1**

- [ ]* 22.2 Write property test for historical balance queries
  - **Property 19: Historical balance queries**
  - **Validates: Requirements 5.2, 5.3**

- [ ]* 22.3 Write property test for debit/credit totals tracking
  - **Property 20: Debit and credit totals tracking**
  - **Validates: Requirements 5.5**

- [ ]* 22.4 Write property test for parent balance aggregation
  - **Property 9: Parent balance aggregation**
  - **Validates: Requirements 2.6, 5.4**

- [ ]* 22.5 Write property test for natural balance direction
  - **Property 13: Natural balance direction**
  - **Validates: Requirements 3.5**

- [x] 23. Add balance API endpoints
  - GET /api/v1/accounts/:id/balance - Get current account balance
  - POST /api/v1/accounts/balances - Get multiple account balances
  - GET /api/v1/accounts/:id/balance/history - Get balance history
  - Add query parameters for as_of_date filtering
  - _Requirements: 5.2, 5.3_

- [ ]* 23.1 Write unit tests for balance endpoints
  - Test current balance retrieval
  - Test historical balance queries
  - Test consolidated balance for parent accounts
  - Test zero balance for accounts with no transactions

- [x] 24. Display balances in account UI
  - Add balance column to account list table
  - Show debit and credit totals in account details
  - Display balance with proper currency formatting
  - Add balance indicators (positive/negative with colors)
  - Show both account currency and base currency balances
  - _Requirements: 4.4, 5.2_

- [ ]* 24.1 Write property test for dual currency balance reporting
  - **Property 16: Dual currency balance reporting**
  - **Validates: Requirements 4.4**

- [x] 25. Add balance history view
  - Create BalanceHistory component showing balance over time
  - Add date range selector for historical balances
  - Display balance trend chart (optional)
  - Show transaction count affecting balance
  - _Requirements: 5.3_

- [x] 26. 🔍 CHECKPOINT - Test Phase 4 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - View account balances in list and details
  - Verify balance calculations are correct
  - Test historical balance queries with date selection
  - Verify parent account balances aggregate children
  - Test dual currency balance display
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 4 code before proceeding to Phase 5**

## Phase 5: Search, Filtering, and Sorting

This phase adds comprehensive search and filtering capabilities.

- [x] 27. Implement search and filter service methods
  - Add search_accounts method to AccountService
  - Implement filtering by account code, name, type, status, parent
  - Add support for combining multiple filters with AND logic
  - Implement case-insensitive name search
  - Add sorting by account code (ascending)
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 6.5_

- [ ]* 27.1 Write property test for account search
  - **Property 21: Account search by code and name**
  - **Validates: Requirements 7.1, 7.2**

- [ ]* 27.2 Write property test for account filtering
  - **Property 22: Account filtering by attributes**
  - **Validates: Requirements 7.3, 7.4, 7.5, 7.6**

- [ ]* 27.3 Write property test for account sorting
  - **Property 23: Account sorting by code**
  - **Validates: Requirements 6.5**

- [x] 28. Add search API endpoint
  - GET /api/v1/accounts/search - Search accounts with query parameter
  - Add filter query parameters (type, status, parent_id, currency)
  - Add sorting and pagination support
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 29. Create search and filter UI components
  - Add search bar to account list view
  - Create filter panel with dropdowns for type, status, currency
  - Add parent account filter with autocomplete
  - Implement real-time search as user types
  - Add "Clear Filters" button
  - Show active filter chips/tags
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 30. Implement sorting in account list
  - Add sortable column headers in account table
  - Implement sort by account code (default)
  - Add sort by name, type, status options
  - Show sort direction indicators (arrows)
  - _Requirements: 6.5_

- [x] 31. 🔍 CHECKPOINT - Test Phase 5 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Search accounts by code and name
  - Test case-insensitive search
  - Apply multiple filters simultaneously
  - Test sorting by different columns
  - Verify filter combinations work correctly
  - Clear filters and verify reset
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 5 code before proceeding to Phase 6**

## Phase 6: Audit Trail and Compliance

This phase implements comprehensive audit logging for compliance.

- [x] 32. Set up audit logging infrastructure
  - Create Alembic migration for account_audit_log table
  - Create AuditLogEntry SQLAlchemy model
  - Add indexes for account_id, timestamp, user_id
  - _Requirements: 10.1_

- [x] 33. Implement audit logger service
  - Create AuditLogger class
  - Implement log_account_change method
  - Capture old and new values for all field changes
  - Record timestamp, user_id, and action type
  - Add methods to query audit trail
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [ ]* 33.1 Write property test for audit log creation
  - **Property 30: Audit log creation**
  - **Validates: Requirements 10.1**

- [ ]* 33.2 Write property test for audit trail ordering
  - **Property 31: Audit trail chronological ordering**
  - **Validates: Requirements 10.2**

- [ ]* 33.3 Write property test for audit field tracking
  - **Property 32: Audit field tracking**
  - **Validates: Requirements 10.3, 10.4**

- [x] 34. Integrate audit logging into account service
  - Add audit logging to create, update, delete, status change operations
  - Capture user context from authentication
  - Log all field changes with before/after values
  - Ensure audit logs are created in same transaction as changes
  - _Requirements: 10.1, 10.3_

- [x] 35. Add audit trail API endpoint
  - GET /api/v1/accounts/:id/audit-trail - Get account audit history
  - Add pagination for audit logs
  - Add filtering by action type and date range
  - _Requirements: 10.2_

- [x] 36. Create audit trail UI component
  - Create AuditTrail component showing change history
  - Display changes in chronological order (newest first)
  - Show timestamp, user, action type, and field changes
  - Highlight changed fields with before/after values
  - Add date range filter for audit logs
  - Format timestamps in user-friendly format
  - _Requirements: 10.2, 10.3, 10.4_

- [x] 37. 🔍 CHECKPOINT - Test Phase 6 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Create, update, and delete accounts
  - View audit trail for each account
  - Verify all changes are logged with correct details
  - Test audit trail filtering by date
  - Verify user information is captured
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 6 code before proceeding to Phase 7**

## Phase 7: Reporting and Export

This phase adds reporting capabilities and data export functionality.

- [x] 38. Implement report generation service
  - Create ReportService class
  - Implement generate_chart_of_accounts_report method
  - Implement generate_hierarchical_report method
  - Implement generate_trial_balance method
  - Add report filtering by type, status, date range
  - _Requirements: 9.1, 9.2, 9.4, 9.5_

- [ ]* 38.1 Write property test for Chart of Accounts report
  - **Property 26: Chart of Accounts report completeness**
  - **Validates: Requirements 9.1**

- [ ]* 38.2 Write property test for hierarchical report
  - **Property 27: Hierarchical report structure**
  - **Validates: Requirements 9.2**

- [ ]* 38.3 Write property test for trial balance
  - **Property 28: Trial balance report accuracy**
  - **Validates: Requirements 9.4**

- [ ]* 38.4 Write property test for report filtering
  - **Property 29: Report filtering**
  - **Validates: Requirements 9.5**

- [x] 39. Implement export service
  - Create ExportService class
  - Implement export_to_csv method
  - Implement export_to_json method
  - Implement export_to_xlsx method using openpyxl
  - Implement export_to_pdf method using reportlab
  - Add proper formatting for each export format
  - _Requirements: 9.3_

- [x] 40. Add reporting API endpoints
  - GET /api/v1/accounts/report/chart - Generate Chart of Accounts report
  - GET /api/v1/accounts/report/trial-balance - Generate trial balance
  - GET /api/v1/accounts/export - Export accounts with format parameter
  - Add query parameters for filtering and format selection
  - Return appropriate content-type headers for downloads
  - _Requirements: 9.1, 9.3, 9.4_

- [x] 41. Create reports UI section
  - Create Reports component with report type selector
  - Add Chart of Accounts report view
  - Add Trial Balance report view
  - Add Hierarchical report view with tree structure
  - Implement report filters (type, status, date range)
  - Add print functionality for reports
  - _Requirements: 9.1, 9.2, 9.4, 9.5_

- [x] 42. Add export functionality to UI
  - Add "Export" button to account list
  - Create export modal with format selection (CSV, JSON, XLSX, PDF)
  - Implement file download on export
  - Add export progress indicator
  - Show success message after export
  - _Requirements: 9.3_

- [x] 43. 🔍 CHECKPOINT - Test Phase 7 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Generate Chart of Accounts report
  - Generate Trial Balance report
  - View Hierarchical report with tree structure
  - Apply filters to reports
  - Export accounts in all formats (CSV, JSON, XLSX, PDF)
  - Verify exported files contain correct data
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 7 code before proceeding to Phase 8**

## Phase 8: Default Accounts and Configuration

This phase adds system configuration for default accounts and account code formats.

- [x] 44. Set up default accounts infrastructure
  - Create Alembic migration for default_accounts table
  - Create DefaultAccount SQLAlchemy model
  - Add indexes for transaction_type and scenario
  - _Requirements: 12.1_

- [x] 45. Implement default account configuration service
  - Create DefaultAccountService class
  - Implement set_default_account method with validation
  - Implement get_default_account method
  - Implement list_default_accounts method
  - Add validation for account type appropriateness
  - Support multiple defaults per transaction type with scenarios
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_

- [ ]* 45.1 Write property test for default account type validation
  - **Property 25: Default account type validation**
  - **Validates: Requirements 8.5, 12.2**

- [ ]* 45.2 Write property test for default account retrieval
  - **Property 37: Default account retrieval**
  - **Validates: Requirements 12.3**

- [ ]* 45.3 Write property test for missing default error
  - **Property 38: Missing default account error**
  - **Validates: Requirements 12.4**

- [ ]* 45.4 Write property test for multiple defaults per type
  - **Property 39: Multiple default accounts per transaction type**
  - **Validates: Requirements 12.5**

- [x] 46. Add default accounts API endpoints
  - GET /api/v1/accounts/config/defaults - Get all default account mappings
  - PUT /api/v1/accounts/config/defaults - Update default account mappings
  - GET /api/v1/accounts/config/format - Get account code format pattern
  - PUT /api/v1/accounts/config/format - Update account code format pattern
  - _Requirements: 12.1, 12.2, 12.3_

- [x] 47. Create system configuration UI
  - Create SystemConfiguration component
  - Add Default Accounts section with transaction type list
  - Implement account selector for each transaction type
  - Add scenario support for multiple defaults
  - Add Account Code Format section with pattern input
  - Show format examples and validation
  - _Requirements: 6.1, 12.1, 12.2_

- [x] 48. Add configuration validation
  - Validate account code format pattern is valid regex
  - Validate default accounts exist and are active
  - Validate default accounts are of appropriate type
  - Show validation errors in UI
  - _Requirements: 6.2, 12.2_

- [x] 49. 🔍 CHECKPOINT - Test Phase 8 from UI (PAUSE HERE FOR TESTING & COMMIT)
  - Configure default accounts for transaction types
  - Set up multiple defaults with scenarios
  - Update account code format pattern
  - Test format validation with valid/invalid patterns
  - Verify default account type validation
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 8 code before proceeding to Phase 9**

## Phase 9: Integration with ERP Modules

This phase implements integration points for other ERP modules.

- [x] 50. Implement transaction posting validation
  - Add validate_posting_account method to AccountService
  - Check account exists, is active, and is a posting account
  - Return descriptive errors for validation failures
  - _Requirements: 8.3_

- [x]* 50.1 Write property test for transaction posting validation
  - **Property 24: Transaction posting validation**
  - **Validates: Requirements 8.3**

- [x] 51. Create integration API for modules
  - POST /api/v1/accounts/validate-posting - Validate account for posting
  - GET /api/v1/accounts/by-code/:code - Get account by code (for lookups)
  - POST /api/v1/accounts/default/:transaction_type - Get default account
  - Add bulk validation endpoint for multiple accounts
  - _Requirements: 8.3, 8.4, 12.3_

- [x] 52. Add account selection components for reuse
  - Create AccountSelector reusable component
  - Create AccountCodeInput with validation
  - Create AccountTypeFilter component
  - Export components for use in other modules
  - Add proper TypeScript types for integration
  - _Requirements: 8.4_

- [x] 53. Document integration APIs
  - Create API documentation for integration endpoints
  - Add code examples for common integration scenarios
  - Document default account configuration requirements
  - Add troubleshooting guide for integration issues
  - _Requirements: 8.4, 8.5_

- [x] 54. 🔍 CHECKPOINT - Test Phase 9 integration (PAUSE HERE FOR TESTING & COMMIT)
  - Test account validation API from Postman
  - Test default account retrieval API
  - Verify account lookup by code works
  - Test bulk validation endpoint
  - Run all backend tests: `pytest tests/`
  - Run all frontend tests: `npm test`
  - **ACTION: Test thoroughly, then commit Phase 9 code before proceeding to Phase 10**

## Phase 10: Advanced Features and Polish

This phase adds remaining features and polishes the UI/UX.

- [x] 55. Implement account type immutability
  - Add validation to prevent type changes when transactions exist
  - Update account service with transaction check
  - Show appropriate error message in UI
  - _Requirements: 11.6_

- [ ]* 55.1 Write property test for account type immutability
  - **Property 36: Account type immutability with transactions**
  - **Validates: Requirements 11.6**

- [x] 56. Add parent account validation
  - Implement parent account existence and status validation
  - Add validation to AccountService
  - Show validation errors in UI forms
  - _Requirements: 11.3_

- [ ]* 56.1 Write property test for parent account validation
  - **Property 34: Parent account validation**
  - **Validates: Requirements 11.3**

- [x] 57. Implement financial statement grouping
  - Add method to group accounts by type for financial statements
  - Ensure proper ordering within each type group
  - _Requirements: 3.4_

- [ ]* 57.1 Write property test for financial statement grouping
  - **Property 12: Financial statement grouping**
  - **Validates: Requirements 3.4**

- [x] 58. Add UI enhancements
  - Add loading states for all async operations
  - Implement optimistic UI updates
  - Add confirmation dialogs for destructive actions
  - Improve error messages with actionable guidance
  - Add keyboard shortcuts for common actions
  - Implement responsive design for mobile/tablet
  - Add tooltips for complex features

- [x] 59. Implement bulk operations
  - Add bulk account status change (activate/deactivate multiple)
  - Add bulk export selection
  - Implement bulk delete with validation
  - Add progress indicators for bulk operations

- [x] 60. Add data seeding and examples
  - Create seed data script for sample Chart of Accounts
  - Add example accounts for each type
  - Create sample hierarchy structure
  - Add documentation for seed data usage

- [x] 61. Performance optimization
  - Add database query optimization with proper indexes
  - Implement pagination for large account lists
  - Add Redis caching for frequently accessed data
  - Optimize hierarchy queries with recursive CTEs
  - Add lazy loading for tree view nodes

- [x] 62. 🔍 FINAL CHECKPOINT - End-to-end testing (PAUSE HERE FOR FINAL TESTING & COMMIT)
  - Test complete account lifecycle (create, update, hierarchy, balance, audit, delete)
  - Test all reports and exports
  - Test integration APIs
  - Verify all property tests pass (100 iterations each)
  - Verify all unit tests pass
  - Test performance with large datasets (1000+ accounts)
  - Conduct accessibility testing
  - Review and address any remaining issues
  - Run full test suite: `pytest tests/ && npm test`
  - **ACTION: Complete final testing, then commit Phase 10 code and create final PR**

## Notes

- Each phase delivers a testable feature that can be reviewed independently
- Tasks marked with `*` are optional property-based tests (can be skipped for faster MVP)
- Each checkpoint ensures the phase is fully functional before moving to the next
- Property tests use fast-check library with minimum 100 iterations
- Unit tests focus on edge cases and specific examples
- All database changes use Alembic migrations for version control
- Frontend components follow existing patterns in horizon-sync project
- Backend follows FastAPI patterns in core-service
- Each phase can be a separate PR for easier review
