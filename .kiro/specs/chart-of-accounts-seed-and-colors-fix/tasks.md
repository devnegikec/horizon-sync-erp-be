# Implementation Plan

## Phase 1: Bug Condition Exploration Tests (BEFORE Fix)

- [ ] 1. Write bug condition exploration tests for all 7 issues
  - **Property 1: Fault Condition** - All Seven Chart of Accounts Bugs
  - **CRITICAL**: These tests MUST FAIL on unfixed code - failures confirm the bugs exist
  - **DO NOT attempt to fix the tests or the code when they fail**
  - **NOTE**: These tests encode the expected behavior - they will validate the fixes when they pass after implementation
  - **GOAL**: Surface counterexamples that demonstrate each bug exists
  - **Scoped PBT Approach**: For deterministic bugs, scope properties to concrete failing cases to ensure reproducibility
  
  - [ ] 1.1 Test Bug 1 & 2: Report download authentication and PDF export
    - Test that clicking "Generate Report" uses window.open (will pass on unfixed code)
    - Test that window.open doesn't include authentication token (will pass on unfixed code)
    - Test that PDF export fails with 401 error (will pass on unfixed code)
    - Document counterexample: "Report download opens new window without auth, redirects to login"
    - _Requirements: 1.1, 1.2, 2.1, 2.2_
  
  - [x] 1.2 Test Bug 3: Configuration page empty
    - Test that SystemConfiguration component renders only placeholder text (will pass on unfixed code)
    - Test that no configuration options are displayed (will pass on unfixed code)
    - Document counterexample: "Configuration page shows 'Configuration settings are coming soon' with no features"
    - _Requirements: 1.3, 2.3_
  
  - [x] 1.3 Test Bug 4: Default accounts UI missing
    - Test that Configuration page has no default accounts UI elements (will pass on unfixed code)
    - Test that no account selectors exist for default accounts (will pass on unfixed code)
    - Document counterexample: "No interface to configure default cash account, default expense account, etc."
    - _Requirements: 1.4, 2.4_
  
  - [x] 1.4 Test Bug 5: Account type color inconsistency
    - Test that LIABILITY shows different colors in AccountsTable vs AccountTypeFilter (will pass on unfixed code)
    - Test that EXPENSE shows different colors across components (will pass on unfixed code)
    - Document counterexample: "LIABILITY is amber in AccountsTable but red in AccountTypeFilter"
    - _Requirements: 1.5, 2.5_
  
  - [x] 1.5 Test Bug 6: Missing parent accounts in seed data
    - Test that admin seed endpoint calls scripts/seed_data.py (will pass on unfixed code)
    - Test that seeded accounts have NULL parent_account_id (will pass on unfixed code)
    - Test that "1100 - Current Assets" has no parent account (will pass on unfixed code)
    - Document counterexample: "Seed creates accounts without parent-child hierarchy"
    - _Requirements: 1.6, 2.6_
  
  - [x] 1.6 Test Bug 7: Empty journal tab
    - Test that Journal Entries tab exists in navigation (will pass on unfixed code)
    - Test that Journal tab shows placeholder "Coming soon - Phase 2" (will pass on unfixed code)
    - Test that Journal tab has no functional controls (will pass on unfixed code)
    - Document counterexample: "Journal tab provides no value, clutters navigation"
    - _Requirements: 1.7, 2.7_
  
  - [ ] 1.7 Run all exploration tests on UNFIXED code
    - **EXPECTED OUTCOME**: All tests FAIL (this is correct - it proves the bugs exist)
    - Document all counterexamples found to understand root causes
    - Mark task complete when tests are written, run, and failures are documented
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

## Phase 2: Preservation Property Tests (BEFORE Fix)

- [ ] 2. Write preservation property tests for non-buggy behavior
  - **Property 2: Preservation** - Existing Functionality Must Remain Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs
  - Write property-based tests capturing observed behavior patterns from Preservation Requirements
  - Property-based testing generates many test cases for stronger guarantees
  
  - [ ] 2.1 Test non-development mode restrictions preserved
    - Observe: Admin seed endpoint returns 403 when DEBUG=false on unfixed code
    - Write property-based test: for all API calls with DEBUG=false, endpoint returns 403
    - Verify test passes on UNFIXED code
    - _Requirements: 3.1_
  
  - [ ] 2.2 Test other export formats preserved
    - Observe: CSV, Excel, JSON exports work correctly on unfixed code
    - Write property-based test: for all non-PDF formats, exports download successfully
    - Test with various filter combinations
    - Verify test passes on UNFIXED code
    - _Requirements: 3.7_
  
  - [ ] 2.3 Test account table interactions preserved
    - Observe: Sorting, filtering, pagination work correctly on unfixed code
    - Write property-based test: for all sort/filter/page combinations, table responds correctly
    - Generate random combinations to test edge cases
    - Verify test passes on UNFIXED code
    - _Requirements: 3.4_
  
  - [ ] 2.4 Test inventory seed script preserved
    - Observe: Direct calls to scripts/seed_data.py create inventory items on unfixed code
    - Write test: calling scripts/seed_data.py directly creates warehouses, item groups, items
    - Verify test passes on UNFIXED code
    - _Requirements: 3.5_
  
  - [ ] 2.5 Test other Books tabs preserved
    - Observe: Chart of Accounts, Reports, Configuration tabs work on unfixed code
    - Write property-based test: for all non-Journal tabs, navigation and functionality work
    - Test tab switching and content rendering
    - Verify test passes on UNFIXED code
    - _Requirements: 3.6_
  
  - [ ] 2.6 Test dark mode color support preserved
    - Observe: Account type badges render correctly in dark mode on unfixed code
    - Write test: for all account types, dark mode variants display correctly
    - Test color contrast and visibility
    - Verify test passes on UNFIXED code
    - _Requirements: 3.8_
  
  - [ ] 2.7 Test default account validation preserved
    - Observe: Backend validates default account selections on unfixed code
    - Write property-based test: for all invalid account selections, backend returns validation errors
    - Test with invalid IDs, wrong types, non-existent accounts
    - Verify test passes on UNFIXED code
    - _Requirements: 3.10_
  
  - [ ] 2.8 Run all preservation tests on UNFIXED code
    - **EXPECTED OUTCOME**: All tests PASS (this confirms baseline behavior to preserve)
    - Mark task complete when tests are written, run, and passing on unfixed code
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

## Phase 3: Implementation

- [ ] 3. Fix Bug 1 & 2: Report download authentication and PDF export

  - [ ] 3.1 Create authenticated download utility
    - Create `horizon-sync/apps/inventory/src/app/utils/downloadUtils.ts`
    - Implement `downloadFileWithAuth(url: string, filename: string)` function
    - Use fetch with credentials and authorization header
    - Handle response as blob
    - Create object URL and trigger download via temporary anchor element
    - Clean up object URL after download
    - _Bug_Condition: isBugCondition(input) where input.action == "GENERATE_REPORT" AND input.method == "window.open" AND NOT hasAuthenticationToken(input.url)_
    - _Expected_Behavior: Downloads file directly using authenticated fetch with blob handling, without opening new window_
    - _Preservation: Other export formats (CSV, Excel, JSON) continue to work correctly_
    - _Requirements: 2.1, 2.2, 3.7_

  - [ ] 3.2 Update Reports component to use authenticated download
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/Reports.tsx`
    - Import `downloadFileWithAuth` utility
    - Replace `window.open(url, '_blank')` with `downloadFileWithAuth(url, filename)`
    - Add loading state during export
    - Add error handling and display error messages
    - Update for both "Generate Report" and "Export PDF" actions
    - _Bug_Condition: Same as 3.1_
    - _Expected_Behavior: Same as 3.1_
    - _Preservation: Report generation in non-PDF formats continues to work_
    - _Requirements: 2.1, 2.2, 3.7_

  - [ ] 3.3 Update useReports hook for authenticated exports
    - Update `horizon-sync/apps/inventory/src/app/hooks/useReports.ts`
    - Add `exportReport` function that handles authenticated API calls
    - Accept format parameter (csv, xlsx, json, pdf)
    - Make authenticated fetch request to export endpoint
    - Return blob response
    - Handle errors and return error state
    - _Bug_Condition: Same as 3.1_
    - _Expected_Behavior: Same as 3.1_
    - _Preservation: Existing report generation functionality continues to work_
    - _Requirements: 2.1, 2.2, 3.7_

  - [ ] 3.4 Verify Bug 1 & 2 exploration test now passes
    - **Property 1: Expected Behavior** - Report Download Works Without Authentication Redirect
    - **IMPORTANT**: Re-run the SAME test from task 1.1 - do NOT write a new test
    - The test from task 1.1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run report download authentication test from step 1.1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bugs are fixed)
    - _Requirements: 2.1, 2.2_

  - [ ] 3.5 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Export Formats Continue Working
    - **IMPORTANT**: Re-run the SAME test from task 2.2 - do NOT write a new test
    - Run other export formats preservation test from step 2.2
    - **EXPECTED OUTCOME**: Test PASSES (confirms no regressions)
    - Confirm CSV, Excel, JSON exports still work after authentication changes

- [ ] 4. Fix Bug 5: Account type color inconsistency

  - [x] 4.1 Create central color constants file
    - Create `horizon-sync/apps/inventory/src/app/utils/accountColors.ts`
    - Define `ACCOUNT_TYPE_COLORS` constant with consistent colors for all account types
    - Use format: `{ ASSET: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400', ... }`
    - Standard colors:
      - ASSET: blue (`bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400`)
      - LIABILITY: red (`bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`)
      - EQUITY: purple (`bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400`)
      - REVENUE: green (`bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`)
      - EXPENSE: orange (`bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400`)
    - Export `getAccountTypeColor(type: AccountType): string` helper function
    - _Bug_Condition: isBugCondition(input) where input.action == "RENDER_ACCOUNT_TYPE_BADGE" AND getColorFromComponent(input.component, input.accountType) != getStandardColor(input.accountType)_
    - _Expected_Behavior: All components use uniform colors from single source of truth_
    - _Preservation: Badge display logic and dark mode support remain functional_
    - _Requirements: 2.5, 3.8_

  - [x] 4.2 Update AccountsTable to use central colors
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/AccountsTable.tsx`
    - Remove local `ACCOUNT_TYPE_COLORS` constant
    - Import `ACCOUNT_TYPE_COLORS` from `../../utils/accountColors`
    - Update all color references to use imported constant
    - Verify dark mode variants are applied correctly
    - _Bug_Condition: Same as 4.1_
    - _Expected_Behavior: Same as 4.1_
    - _Preservation: Table interactions (sorting, filtering, pagination) continue to work_
    - _Requirements: 2.5, 3.4, 3.8_

  - [x] 4.3 Update AccountTreeView to use central colors
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/AccountTreeView.tsx`
    - Remove local `ACCOUNT_TYPE_COLORS` constant
    - Import `ACCOUNT_TYPE_COLORS` from `../../utils/accountColors`
    - Update all color references to use imported constant
    - Verify dark mode variants are applied correctly
    - _Bug_Condition: Same as 4.1_
    - _Expected_Behavior: Same as 4.1_
    - _Preservation: Tree view interactions continue to work_
    - _Requirements: 2.5, 3.8_

  - [x] 4.4 Update AccountDetailDialog to use central colors
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/AccountDetailDialog.tsx`
    - Remove local `ACCOUNT_TYPE_COLORS` constant
    - Import `ACCOUNT_TYPE_COLORS` from `../../utils/accountColors`
    - Update all color references to use imported constant
    - Verify dark mode variants are applied correctly
    - _Bug_Condition: Same as 4.1_
    - _Expected_Behavior: Same as 4.1_
    - _Preservation: Dialog functionality continues to work_
    - _Requirements: 2.5, 3.8_

  - [x] 4.5 Update AccountManagement to use central colors
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/AccountManagement.tsx`
    - Remove local `ACCOUNT_TYPE_COLORS` constant
    - Import `ACCOUNT_TYPE_COLORS` from `../../utils/accountColors`
    - Update all color references to use imported constant
    - Verify dark mode variants are applied correctly
    - _Bug_Condition: Same as 4.1_
    - _Expected_Behavior: Same as 4.1_
    - _Preservation: Account management functionality continues to work_
    - _Requirements: 2.5, 3.8_

  - [x] 4.6 Update AccountTypeFilter to use central colors
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/AccountTypeFilter.tsx`
    - Update `ACCOUNT_TYPES` array to use colors from central definition
    - Or import `ACCOUNT_TYPE_COLORS` and derive `ACCOUNT_TYPES` from it
    - Update `getAccountTypeColor` function to return colors from standard mapping
    - _Bug_Condition: Same as 4.1_
    - _Expected_Behavior: Same as 4.1_
    - _Preservation: Filter functionality continues to work_
    - _Requirements: 2.5, 3.8_

  - [ ] 4.7 Verify Bug 5 exploration test now passes
    - **Property 1: Expected Behavior** - Account Type Colors Uniform Across Components
    - **IMPORTANT**: Re-run the SAME test from task 1.4 - do NOT write a new test
    - The test from task 1.4 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run color inconsistency test from step 1.4
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.5_

  - [ ] 4.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Dark Mode and Table Interactions Preserved
    - **IMPORTANT**: Re-run the SAME tests from tasks 2.3 and 2.6 - do NOT write new tests
    - Run account table interactions test from step 2.3
    - Run dark mode color support test from step 2.6
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm sorting, filtering, pagination still work
    - Confirm dark mode variants still display correctly

- [ ] 5. Fix Bug 6: Missing parent accounts in seed data

  - [x] 5.1 Update admin endpoint to call correct seed script
    - Update `horizon-sync-erp-be/core-service/app/api/v1/endpoints/admin.py`
    - Change line 38 script path from `scripts/seed_data.py` to `seed_chart_of_accounts.py`
    - FROM: `script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "seed_data.py"`
    - TO: `script_path = Path(__file__).parent.parent.parent.parent / "seed_chart_of_accounts.py"`
    - Update success message to reflect chart of accounts seeding
    - Update docstring to clarify this endpoint seeds chart of accounts with parent-child hierarchy
    - _Bug_Condition: isBugCondition(input) where input.action == "SEED_CHART_OF_ACCOUNTS" AND scriptCalled == "scripts/seed_data.py" AND scriptCalled != "seed_chart_of_accounts.py"_
    - _Expected_Behavior: Calls seed_chart_of_accounts.py which creates accounts with proper parent-child hierarchy_
    - _Preservation: Non-development mode restrictions continue to work; inventory seed script continues to work when called directly_
    - _Requirements: 2.6, 3.1, 3.5_

  - [ ] 5.2 Verify Bug 6 exploration test now passes
    - **Property 1: Expected Behavior** - Seed Script Creates Proper Hierarchy
    - **IMPORTANT**: Re-run the SAME test from task 1.5 - do NOT write a new test
    - The test from task 1.5 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run seed script test from step 1.5
    - Call admin seed endpoint
    - Query database for accounts with parent_account_id
    - Verify "1100 - Current Assets" has parent "1000 - Assets"
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.6_

  - [ ] 5.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Development Mode and Inventory Seed Preserved
    - **IMPORTANT**: Re-run the SAME tests from tasks 2.1 and 2.4 - do NOT write new tests
    - Run non-development mode restrictions test from step 2.1
    - Run inventory seed script test from step 2.4
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Confirm admin endpoint returns 403 when DEBUG=false
    - Confirm scripts/seed_data.py still creates inventory items when called directly

- [ ] 6. Fix Bug 7: Empty journal tab

  - [ ] 6.1 Remove Journal Entries tab from Books page
    - Update `horizon-sync/apps/inventory/src/app/pages/BooksPage.tsx`
    - Remove Journal Entries NavItem from navigation
    - Remove `| 'journal_entries'` from ActiveView type definition
    - Remove Journal Entries content section (conditional render block)
    - Ensure default view is still valid after removal
    - _Bug_Condition: isBugCondition(input) where input.action == "NAVIGATE_TO_JOURNAL" AND currentTab == "journal_entries" AND componentContent == "Coming soon - Phase 2"_
    - _Expected_Behavior: Journal tab removed from navigation, no dead UI element_
    - _Preservation: Other Books tabs (Chart of Accounts, Reports, Configuration) continue to function correctly_
    - _Requirements: 2.7, 3.6_

  - [ ] 6.2 Verify Bug 7 exploration test now passes
    - **Property 1: Expected Behavior** - Journal Tab Removed or Implemented
    - **IMPORTANT**: Re-run the SAME test from task 1.6 - do NOT write a new test
    - The test from task 1.6 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run empty journal tab test from step 1.6
    - Verify Journal Entries tab no longer exists in navigation
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - _Requirements: 2.7_

  - [ ] 6.3 Verify preservation tests still pass
    - **Property 2: Preservation** - Other Books Tabs Continue Working
    - **IMPORTANT**: Re-run the SAME test from task 2.5 - do NOT write a new test
    - Run other Books tabs test from step 2.5
    - **EXPECTED OUTCOME**: Test PASSES (confirms no regressions)
    - Confirm Chart of Accounts, Reports, Configuration tabs still work
    - Confirm tab switching and content rendering still work

- [ ] 7. Fix Bug 3 & 4: Configuration page and default accounts UI

  - [ ] 7.1 Create useDefaultAccounts hook
    - Create `horizon-sync/apps/inventory/src/app/hooks/useDefaultAccounts.ts`
    - Implement hook for default accounts management
    - Fetch default accounts from API
    - Provide save function to update default accounts
    - Manage loading and error states
    - Return accounts data and mutation functions
    - _Bug_Condition: isBugCondition(input) where input.action == "NAVIGATE_TO_CONFIGURATION" AND NOT hasConfigurationOptions(componentRendered)_
    - _Expected_Behavior: Configuration page displays system settings and default accounts setup interface_
    - _Preservation: Existing configuration settings continue to save and load correctly; default account validation continues to work_
    - _Requirements: 2.3, 2.4, 3.9, 3.10_

  - [ ] 7.2 Implement SystemConfiguration component
    - Update `horizon-sync/apps/inventory/src/app/components/accounts/SystemConfiguration.tsx`
    - Remove placeholder text
    - Add Default Accounts section with account selectors
    - Import AccountSelector component for account selection
    - Add form fields for each default account type (cash, expense, revenue, etc.)
    - Use AccountSelector with appropriate filters (e.g., only ASSET accounts for default cash)
    - Add Save and Cancel buttons
    - _Bug_Condition: Same as 7.1_
    - _Expected_Behavior: Same as 7.1_
    - _Preservation: Same as 7.1_
    - _Requirements: 2.3, 2.4, 3.9, 3.10_

  - [ ] 7.3 Add API integration to SystemConfiguration
    - Use `useDefaultAccounts` hook to fetch and update default accounts
    - Fetch current default accounts on component mount
    - Implement save handler to POST/PUT default accounts
    - Show success/error messages after save
    - Add loading state with skeleton loader
    - Display error message if fetch fails
    - Disable form during save operation
    - _Bug_Condition: Same as 7.1_
    - _Expected_Behavior: Same as 7.1_
    - _Preservation: Same as 7.1_
    - _Requirements: 2.3, 2.4, 3.9, 3.10_

  - [ ] 7.4 Add System Settings section (optional)
    - Add section for general system settings
    - Add fiscal year configuration
    - Add base currency setting
    - Add accounting method setting (cash vs accrual)
    - These can be placeholders for future implementation
    - _Bug_Condition: Same as 7.1_
    - _Expected_Behavior: Same as 7.1_
    - _Preservation: Same as 7.1_
    - _Requirements: 2.3_

  - [ ] 7.5 Verify Bug 3 & 4 exploration tests now pass
    - **Property 1: Expected Behavior** - Configuration Page Displays Settings
    - **IMPORTANT**: Re-run the SAME tests from tasks 1.2 and 1.3 - do NOT write new tests
    - The tests from tasks 1.2 and 1.3 encode the expected behavior
    - When these tests pass, they confirm the expected behavior is satisfied
    - Run configuration page empty test from step 1.2
    - Run default accounts UI missing test from step 1.3
    - **EXPECTED OUTCOME**: Tests PASS (confirms bugs are fixed)
    - _Requirements: 2.3, 2.4_

  - [ ] 7.6 Verify preservation tests still pass
    - **Property 2: Preservation** - Configuration Settings and Validation Preserved
    - **IMPORTANT**: Re-run the SAME test from task 2.7 - do NOT write a new test
    - Run default account validation test from step 2.7
    - **EXPECTED OUTCOME**: Test PASSES (confirms no regressions)
    - Confirm backend still validates default account selections
    - Confirm validation errors are returned for invalid selections

## Phase 4: Final Checkpoint

- [ ] 8. Checkpoint - Ensure all tests pass
  - Run all exploration tests from Phase 1 - all should now PASS
  - Run all preservation tests from Phase 2 - all should still PASS
  - Verify all 7 bugs are fixed:
    - Bug 1 & 2: Reports download with authentication, PDF export works
    - Bug 3: Configuration page displays settings
    - Bug 4: Default accounts UI is visible and functional
    - Bug 5: Account type colors are uniform across all components
    - Bug 6: Seed script creates proper parent-child hierarchy
    - Bug 7: Journal tab is removed from navigation
  - Verify no regressions in existing functionality
  - Ask user if any questions or issues arise
  - _Requirements: All requirements 1.1-3.10_
