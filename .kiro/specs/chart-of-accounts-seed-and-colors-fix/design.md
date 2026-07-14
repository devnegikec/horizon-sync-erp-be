# Chart of Accounts Seed and Colors Fix - Bugfix Design

## Overview

This design addresses seven critical issues in the Chart of Accounts feature that prevent proper functionality, data integrity, and UI consistency. The issues span authentication, export functionality, UI visibility, color theming, data seeding, and navigation structure. The fix approach involves targeted changes to authentication handling, component implementation, color standardization, seed script correction, and UI cleanup.

## Glossary

- **Bug_Condition (C)**: The conditions that trigger each of the seven bugs - authentication redirect, PDF export failure, empty configuration page, missing default accounts UI, inconsistent colors, missing parent accounts, and empty journal tab
- **Property (P)**: The desired behavior for each bug - proper authentication, working PDF export, visible configuration, default accounts UI, uniform colors, correct hierarchy, and clean navigation
- **Preservation**: Existing functionality that must remain unchanged - non-development mode restrictions, other export formats, account table interactions, inventory seed script, other Books tabs, and existing configuration settings
- **Report Service**: The backend service in `app/services/report_service.py` that generates report data
- **Export Service**: The backend service in `app/services/export_service.py` that handles PDF, CSV, XLSX, and JSON exports
- **Admin Endpoint**: The API endpoint in `app/api/v1/endpoints/admin.py` that triggers data seeding
- **SystemConfiguration Component**: The React component in `SystemConfiguration.tsx` that displays configuration settings
- **ACCOUNT_TYPE_COLORS**: Color mapping constants defined in multiple frontend components with inconsistent values
- **seed_data.py**: Inventory seed script that creates warehouses, item groups, and items (NOT chart of accounts)
- **seed_chart_of_accounts.py**: Chart of accounts seed script that creates accounts with proper parent-child hierarchy

## Bug Details

### Fault Condition

The bugs manifest in seven distinct scenarios:

**1. Report Download Authentication Bug:**
When a user clicks "Generate Report" or "Export PDF" buttons, the system redirects to login page instead of downloading. The Reports component uses `window.open(url, '_blank')` which opens a new browser window without authentication cookies/tokens.

**2. PDF Export Failure:**
When a user tries to export reports as PDF, the export fails or produces no output. The backend PDF export service exists and works, but the frontend doesn't properly trigger it or handle authentication.

**3. Empty Configuration Page:**
When a user navigates to Configuration tab, the SystemConfiguration component only shows a placeholder message "Configuration settings are coming soon" with no actual configuration options.

**4. Missing Default Accounts UI:**
There is no visible interface in the Configuration page to set up default accounts (default cash account, default expense account, etc.) even though the backend infrastructure exists (DefaultAccount model, service, and API).

**5. Inconsistent Account Type Colors:**
Account type badges display different colors across components:
- AccountTypeFilter: `ASSET: 'bg-blue-100'`, `LIABILITY: 'bg-red-100'`, `EXPENSE: 'bg-orange-100'`
- AccountsTable: `ASSET: 'bg-blue-100'`, `LIABILITY: 'bg-amber-100'`, `EXPENSE: 'bg-red-100'`
- AccountTreeView: `ASSET: 'bg-blue-100'`, `LIABILITY: 'bg-amber-100'`, `EXPENSE: 'bg-red-100'`
- AccountDetailDialog: `ASSET: 'bg-blue-100'`, `LIABILITY: 'bg-red-100'`, `EQUITY: 'bg-indigo-100'`

**6. Missing Parent Accounts:**
When viewing chart of accounts after seeding, most child accounts show empty parent account field. The admin seed endpoint at `/api/v1/admin/seed-data` calls `scripts/seed_data.py` which creates inventory items (warehouses, item groups, items) instead of calling `seed_chart_of_accounts.py` which creates accounts with proper parent-child hierarchy.

**7. Empty Journal Tab:**
When user clicks on Journal Entries tab in Books page, it shows an empty placeholder with "Coming soon - Phase 2" message, providing no value to users.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type UserAction
  OUTPUT: boolean
  
  RETURN (
    // Bug 1: Report download redirects to login
    (input.action == "GENERATE_REPORT" OR input.action == "EXPORT_PDF")
    AND input.method == "window.open"
    AND NOT hasAuthenticationToken(input.url)
  ) OR (
    // Bug 2: PDF export not working (same root cause as Bug 1)
    input.action == "EXPORT_PDF"
    AND input.format == "pdf"
    AND NOT canDownloadFile(input)
  ) OR (
    // Bug 3: Configuration page empty
    input.action == "NAVIGATE_TO_CONFIGURATION"
    AND componentRendered == "SystemConfiguration"
    AND NOT hasConfigurationOptions(componentRendered)
  ) OR (
    // Bug 4: Default accounts UI missing
    input.action == "LOOK_FOR_DEFAULT_ACCOUNTS"
    AND currentPage == "Configuration"
    AND NOT hasDefaultAccountsUI(currentPage)
  ) OR (
    // Bug 5: Inconsistent colors
    input.action == "RENDER_ACCOUNT_TYPE_BADGE"
    AND input.accountType IN ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE']
    AND getColorFromComponent(input.component, input.accountType) != getStandardColor(input.accountType)
  ) OR (
    // Bug 6: Missing parent accounts
    input.action == "SEED_CHART_OF_ACCOUNTS"
    AND input.endpoint == "/api/v1/admin/seed-data"
    AND scriptCalled == "scripts/seed_data.py"
    AND scriptCalled != "seed_chart_of_accounts.py"
  ) OR (
    // Bug 7: Empty journal tab
    input.action == "NAVIGATE_TO_JOURNAL"
    AND currentTab == "journal_entries"
    AND componentContent == "Coming soon - Phase 2"
  )
END FUNCTION
```

### Examples

**Bug 1 - Report Download Authentication:**
- User clicks "Generate Reports" button → Browser opens new tab → Redirects to login page
- User clicks "Export PDF" button → Browser opens new tab → Redirects to login page
- Expected: Report downloads directly without authentication redirect

**Bug 2 - PDF Export Failure:**
- User clicks "Export PDF" button → New tab opens → Shows login page or 401 error
- Expected: PDF file downloads directly to user's computer

**Bug 3 - Empty Configuration Page:**
- User clicks "Configuration" tab → Page shows only "Configuration settings are coming soon"
- Expected: Page shows system settings, default accounts setup, and other configuration options

**Bug 4 - Missing Default Accounts UI:**
- User navigates to Configuration page → No interface to set default accounts
- Backend has DefaultAccount model and API but no frontend UI
- Expected: Configuration page includes Default Accounts section with account selectors

**Bug 5 - Inconsistent Colors:**
- ASSET account in AccountsTable shows blue badge
- ASSET account in AccountManagement stat card shows blue icon background
- LIABILITY account in AccountsTable shows amber badge
- LIABILITY account in AccountTypeFilter shows red badge
- Expected: All components use same color for each account type

**Bug 6 - Missing Parent Accounts:**
- Admin clicks seed data button → Accounts created but parent_account_id is NULL
- "1100 - Current Assets" should have parent "1000 - Assets" but shows no parent
- Root cause: `/api/v1/admin/seed-data` runs `scripts/seed_data.py` (inventory) instead of `seed_chart_of_accounts.py` (accounts)
- Expected: Accounts created with proper parent-child hierarchy

**Bug 7 - Empty Journal Tab:**
- User clicks "Journal Entries" tab → Shows placeholder "Coming soon - Phase 2"
- Tab provides no functionality and clutters navigation
- Expected: Either implement journal entry UI or remove the tab from navigation

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Non-development mode restrictions: Admin seed endpoint must continue to return 403 error when DEBUG=false
- Other export formats: CSV, Excel, and JSON exports must continue to work correctly
- Account table interactions: Sorting, filtering, pagination must remain functional with any UI updates
- Inventory seed script: `scripts/seed_data.py` must continue to create inventory items when called directly
- Other Books tabs: Chart of Accounts, Reports, Payments, Configuration tabs must continue to function correctly
- Existing configuration settings: Any existing configuration data must continue to save and load correctly
- Account type badge rendering: Badge display logic must remain functional with color updates
- Dark mode support: All color changes must maintain dark mode variants
- Default account validation: Backend must continue to validate that selected accounts exist and are appropriate types
- Seed script error handling: Timeout and failure error messages must continue to work

**Scope:**
All inputs that do NOT involve the seven specific bug scenarios should be completely unaffected by this fix. This includes:
- Mouse clicks on account table rows, sort headers, pagination controls
- Other keyboard inputs and navigation actions
- Report generation in non-PDF formats
- Direct calls to inventory seed script for testing purposes
- Navigation to other pages and features outside Books page
- Existing API endpoints for account CRUD operations
- Balance calculations and audit trail functionality

## Hypothesized Root Cause

Based on the bug descriptions and code analysis, the root causes are:

**1. Report Download Authentication Issue:**
- **Root Cause**: The Reports component uses `window.open(url, '_blank')` to download reports, which opens a new browser window/tab without including authentication cookies or bearer tokens
- **Evidence**: Line in Reports.tsx: `window.open(url, '_blank');` - this creates a new browsing context without credentials
- **Solution**: Use authenticated fetch with blob download or include token in URL query parameters

**2. PDF Export Failure:**
- **Root Cause**: Same as Bug 1 - authentication issue prevents PDF download
- **Evidence**: Same `window.open` pattern used for PDF export
- **Solution**: Same as Bug 1 - use authenticated download mechanism

**3. Empty Configuration Page:**
- **Root Cause**: SystemConfiguration component is a placeholder stub with no implementation
- **Evidence**: SystemConfiguration.tsx only contains: `<p className="text-sm text-muted-foreground">Configuration settings are coming soon.</p>`
- **Solution**: Implement actual configuration UI with system settings and default accounts

**4. Missing Default Accounts UI:**
- **Root Cause**: Frontend UI was never implemented even though backend infrastructure exists
- **Evidence**: Backend has DefaultAccount model, service, and API endpoints, but no frontend component uses them
- **Solution**: Add Default Accounts section to SystemConfiguration component with account selectors

**5. Inconsistent Account Type Colors:**
- **Root Cause**: Multiple components define their own `ACCOUNT_TYPE_COLORS` constants with different color values
- **Evidence**: 
  - AccountTypeFilter: `LIABILITY: 'bg-red-100'`
  - AccountsTable: `LIABILITY: 'bg-amber-100'`
  - AccountTreeView: `LIABILITY: 'bg-amber-100'`
  - AccountDetailDialog: `LIABILITY: 'bg-red-100'`, `EQUITY: 'bg-indigo-100'`
- **Solution**: Create single source of truth for colors and import in all components

**6. Missing Parent Accounts:**
- **Root Cause**: Admin seed endpoint calls wrong script - `scripts/seed_data.py` (inventory) instead of `seed_chart_of_accounts.py` (accounts)
- **Evidence**: admin.py line 38: `script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "seed_data.py"`
- **Solution**: Change script path to point to `seed_chart_of_accounts.py` in project root

**7. Empty Journal Tab:**
- **Root Cause**: Tab was added prematurely before implementation, creating dead UI element
- **Evidence**: BooksPage.tsx shows placeholder: `<p className="text-muted-foreground">Coming soon - Phase 2</p>`
- **Solution**: Remove Journal Entries tab from navigation until Phase 2 implementation

## Correctness Properties

Property 1: Fault Condition - Report Download Works Without Authentication Redirect

_For any_ user action where the user clicks "Generate Report" or "Export PDF" button in the Reports tab, the fixed system SHALL download the report file directly using authenticated fetch with blob handling, without opening a new browser window or redirecting to the login page.

**Validates: Requirements 2.1, 2.2**

Property 2: Fault Condition - PDF Export Generates Valid PDF Files

_For any_ user action where the user clicks "Export PDF" button or selects PDF format from export options, the fixed system SHALL generate a properly formatted PDF file with report data and download it directly to the user's computer.

**Validates: Requirements 2.2**

Property 3: Fault Condition - Configuration Page Displays Settings

_For any_ user navigation to the Configuration tab in Books page, the fixed SystemConfiguration component SHALL display system settings, default accounts setup interface, and other configuration options instead of showing a placeholder message.

**Validates: Requirements 2.3, 2.4**

Property 4: Fault Condition - Default Accounts UI Visible and Functional

_For any_ user looking for default accounts setup in the Configuration page, the fixed system SHALL provide a visible interface with account selectors to set up and manage default accounts (default cash account, default expense account, etc.).

**Validates: Requirements 2.4**

Property 5: Fault Condition - Account Type Colors Uniform Across Components

_For any_ account type badge rendered in any component (AccountsTable, AccountManagement, AccountTreeView, AccountDetailDialog, Reports), the fixed system SHALL use uniform, consistent colors for each account type by importing from a single source of truth.

**Validates: Requirements 2.5**

Property 6: Fault Condition - Seed Script Creates Proper Hierarchy

_For any_ admin action to seed chart of accounts data via `/api/v1/admin/seed-data` endpoint, the fixed system SHALL call `seed_chart_of_accounts.py` script which creates accounts with proper parent-child hierarchy (e.g., "1100 - Current Assets" has parent "1000 - Assets").

**Validates: Requirements 2.6**

Property 7: Fault Condition - Journal Tab Removed or Implemented

_For any_ user viewing the Books page navigation, the fixed system SHALL either display a functional Journal Entries tab with journal entry UI controls OR remove the tab entirely from navigation if not required for MVP.

**Validates: Requirements 2.7**

Property 8: Preservation - Non-Development Mode Restrictions

_For any_ API call to admin seed endpoint when DEBUG=false (non-development mode), the fixed system SHALL produce exactly the same behavior as the original system, returning a 403 error preventing unauthorized data seeding.

**Validates: Requirements 3.1**

Property 9: Preservation - Other Export Formats Continue Working

_For any_ user action to export reports in CSV, Excel, or JSON format, the fixed system SHALL produce exactly the same behavior as the original system, successfully generating and downloading the report in the requested format.

**Validates: Requirements 3.7**

Property 10: Preservation - Account Table Interactions Unchanged

_For any_ user interaction with the accounts table (sorting, filtering, pagination, row selection), the fixed system SHALL produce exactly the same behavior as the original system, maintaining all existing functionality.

**Validates: Requirements 3.4**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

#### Bug 1 & 2: Report Download and PDF Export Authentication

**File**: `horizon-sync/apps/inventory/src/app/components/accounts/Reports.tsx`

**Function**: `handleExport`

**Specific Changes**:
1. **Replace window.open with authenticated fetch**: Change from `window.open(url, '_blank')` to authenticated fetch API call
   - Import API utility functions for authenticated requests
   - Use fetch with credentials and authorization header
   - Handle response as blob for file download
   - Create object URL and trigger download via temporary anchor element

2. **Add loading and error states**: Show loading indicator during export and handle errors gracefully
   - Add `exportLoading` state variable
   - Add `exportError` state variable
   - Display loading spinner when export in progress
   - Show error message if export fails

3. **Implement blob download helper**: Create utility function to handle blob downloads
   - Accept blob data and filename
   - Create object URL from blob
   - Create temporary anchor element
   - Trigger click to download
   - Clean up object URL

**File**: `horizon-sync/apps/inventory/src/app/hooks/useReports.ts`

**Specific Changes**:
1. **Add export function to hook**: Add `exportReport` function that handles authenticated API calls
   - Accept format parameter (csv, xlsx, json, pdf)
   - Accept filters parameter
   - Make authenticated fetch request to export endpoint
   - Return blob response
   - Handle errors and return error state

#### Bug 3 & 4: Configuration Page and Default Accounts UI

**File**: `horizon-sync/apps/inventory/src/app/components/accounts/SystemConfiguration.tsx`

**Function**: Complete component rewrite

**Specific Changes**:
1. **Add Default Accounts Section**: Create UI for configuring default accounts
   - Import AccountSelector component for account selection
   - Add form fields for each default account type (cash, expense, revenue, etc.)
   - Use AccountSelector with appropriate filters (e.g., only ASSET accounts for default cash)
   - Add Save and Cancel buttons

2. **Add API Integration**: Connect to backend default accounts API
   - Create `useDefaultAccounts` hook to fetch and update default accounts
   - Fetch current default accounts on component mount
   - Implement save handler to POST/PUT default accounts
   - Show success/error messages after save

3. **Add System Settings Section**: Add placeholder for future system settings
   - Create section for general system settings
   - Add fiscal year configuration
   - Add base currency setting
   - Add accounting method setting (cash vs accrual)

4. **Add Loading and Error States**: Handle async operations gracefully
   - Show skeleton loader while fetching data
   - Display error message if fetch fails
   - Disable form during save operation
   - Show success toast after successful save

**File**: `horizon-sync/apps/inventory/src/app/hooks/useDefaultAccounts.ts` (NEW FILE)

**Specific Changes**:
1. **Create custom hook**: Implement hook for default accounts management
   - Fetch default accounts from API
   - Provide save function to update default accounts
   - Manage loading and error states
   - Return accounts data and mutation functions

#### Bug 5: Inconsistent Account Type Colors

**File**: `horizon-sync/apps/inventory/src/app/utils/accountColors.ts` (NEW FILE)

**Specific Changes**:
1. **Create single source of truth**: Define standard color mapping for all account types
   - Export `ACCOUNT_TYPE_COLORS` constant with consistent colors
   - Include both light and dark mode variants
   - Use format: `{ ASSET: 'bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400', ... }`
   - Standard colors:
     - ASSET: blue (`bg-blue-100 text-blue-800 dark:bg-blue-900/20 dark:text-blue-400`)
     - LIABILITY: red (`bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400`)
     - EQUITY: purple (`bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400`)
     - REVENUE: green (`bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400`)
     - EXPENSE: orange (`bg-orange-100 text-orange-800 dark:bg-orange-900/20 dark:text-orange-400`)

2. **Export helper function**: Create `getAccountTypeColor(type: AccountType): string` function
   - Accept account type parameter
   - Return color string from ACCOUNT_TYPE_COLORS
   - Provide fallback for unknown types

**Files to Update**: 
- `horizon-sync/apps/inventory/src/app/components/accounts/AccountsTable.tsx`
- `horizon-sync/apps/inventory/src/app/components/accounts/AccountTreeView.tsx`
- `horizon-sync/apps/inventory/src/app/components/accounts/AccountDetailDialog.tsx`
- `horizon-sync/apps/inventory/src/app/components/accounts/AccountManagement.tsx`

**Specific Changes for Each File**:
1. **Remove local ACCOUNT_TYPE_COLORS constant**: Delete the local color definition
2. **Import from central location**: Add `import { ACCOUNT_TYPE_COLORS } from '../../utils/accountColors';`
3. **Update color references**: Ensure all badge/icon color references use imported constant
4. **Verify dark mode support**: Ensure dark mode color variants are applied correctly

**File**: `horizon-sync/apps/inventory/src/app/components/accounts/AccountTypeFilter.tsx`

**Specific Changes**:
1. **Update ACCOUNT_TYPES array**: Change color values to match standard colors
2. **Or import from central location**: Alternative approach - import ACCOUNT_TYPE_COLORS and derive ACCOUNT_TYPES from it
3. **Update getAccountTypeColor function**: Ensure it returns colors from standard mapping

#### Bug 6: Missing Parent Accounts (Wrong Seed Script)

**File**: `horizon-sync-erp-be/core-service/app/api/v1/endpoints/admin.py`

**Function**: `seed_sample_data`

**Specific Changes**:
1. **Change script path**: Update line 38 to point to correct seed script
   - FROM: `script_path = Path(__file__).parent.parent.parent.parent / "scripts" / "seed_data.py"`
   - TO: `script_path = Path(__file__).parent.parent.parent.parent / "seed_chart_of_accounts.py"`

2. **Update success message**: Change response message to reflect chart of accounts seeding
   - Update "accounts_created" field to show actual count from script output
   - Update "note" field to mention chart of accounts specifically

3. **Update docstring**: Clarify that this endpoint seeds chart of accounts, not inventory data
   - Change "Seed sample chart of accounts data" to be more specific
   - Add note about parent-child hierarchy creation

#### Bug 7: Empty Journal Tab

**File**: `horizon-sync/apps/inventory/src/app/pages/BooksPage.tsx`

**Specific Changes**:
1. **Remove Journal Entries from navigation**: Delete the NavItem for journal_entries
   - Remove: `<NavItem icon={FileText} label="Journal Entries" isActive={activeView === 'journal_entries'} onClick={() => setActiveView('journal_entries')} />`
   - Remove: `| 'journal_entries'` from ActiveView type definition

2. **Remove Journal Entries content section**: Delete the conditional render for journal_entries
   - Remove entire block: `{activeView === 'journal_entries' && ( ... )}`

3. **Update default view if needed**: Ensure default view is still valid after removal
   - Current default is 'coa' which is fine

4. **Remove Payments tab as well (optional)**: Since Payments also shows "Coming soon - Phase 3", consider removing it too
   - Remove Payments NavItem
   - Remove Payments content section
   - Remove `| 'payments'` from ActiveView type

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate each bug on unfixed code, then verify the fixes work correctly and preserve existing behavior. Each bug requires specific test cases to validate the fix and ensure no regressions.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate all seven bugs BEFORE implementing the fixes. Confirm or refute the root cause analysis for each bug. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that simulate each bug scenario and assert the expected failure. Run these tests on the UNFIXED code to observe failures and understand the root causes.

**Test Cases**:

1. **Report Download Authentication Test**: 
   - Simulate clicking "Generate Report" button
   - Assert that window.open is called (will pass on unfixed code, confirming bug)
   - Assert that new window redirects to login (will pass on unfixed code)
   - Expected failure: Report should download directly, not redirect

2. **PDF Export Test**: 
   - Simulate clicking "Export PDF" button
   - Assert that window.open is called with PDF URL (will pass on unfixed code)
   - Assert that authentication fails (will pass on unfixed code)
   - Expected failure: PDF should download with authentication

3. **Configuration Page Empty Test**: 
   - Navigate to Configuration tab
   - Assert that SystemConfiguration component renders
   - Assert that component contains only placeholder text (will pass on unfixed code)
   - Expected failure: Should show actual configuration options

4. **Default Accounts UI Missing Test**: 
   - Navigate to Configuration page
   - Search for default accounts UI elements (account selectors, save button)
   - Assert that no default accounts UI exists (will pass on unfixed code)
   - Expected failure: Should have default accounts configuration interface

5. **Color Inconsistency Test**: 
   - Render AccountsTable with LIABILITY account
   - Render AccountTypeFilter with LIABILITY account
   - Assert that colors are different (will pass on unfixed code)
   - Expected failure: Colors should be consistent across components

6. **Seed Script Test**: 
   - Call admin seed endpoint
   - Assert that scripts/seed_data.py is executed (will pass on unfixed code)
   - Query database for accounts with parent_account_id
   - Assert that most parent_account_id fields are NULL (will pass on unfixed code)
   - Expected failure: Should call seed_chart_of_accounts.py and create hierarchy

7. **Empty Journal Tab Test**: 
   - Navigate to Journal Entries tab
   - Assert that placeholder "Coming soon" message is displayed (will pass on unfixed code)
   - Assert that no functional controls exist (will pass on unfixed code)
   - Expected failure: Tab should either work or not exist

**Expected Counterexamples**:
- Report downloads open new windows without authentication tokens
- PDF export fails with 401 Unauthorized error
- Configuration page shows only placeholder text
- No UI elements for default accounts configuration
- LIABILITY accounts show amber in AccountsTable but red in AccountTypeFilter
- Seed endpoint creates accounts without parent_account_id values
- Journal tab shows non-functional placeholder

**Possible Root Causes Confirmed**:
- window.open doesn't include authentication credentials
- SystemConfiguration is a stub component
- Multiple ACCOUNT_TYPE_COLORS definitions with different values
- Admin endpoint points to wrong seed script
- Journal tab added prematurely without implementation

### Fix Checking

**Goal**: Verify that for all inputs where each bug condition holds, the fixed system produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedSystem(input)
  ASSERT expectedBehavior(result)
END FOR
```

**Test Cases by Bug**:

**Bug 1 & 2 - Report Download and PDF Export**:
```
FOR ALL reportType IN ['chart_of_accounts', 'hierarchical', 'trial_balance'] DO
  FOR ALL format IN ['csv', 'xlsx', 'json', 'pdf'] DO
    result := handleExport(format, filters)
    ASSERT result.usesAuthenticatedFetch == true
    ASSERT result.downloadsDirectly == true
    ASSERT result.noWindowOpen == true
    ASSERT result.fileReceived == true
  END FOR
END FOR
```

**Bug 3 & 4 - Configuration Page and Default Accounts**:
```
result := renderSystemConfiguration()
ASSERT result.hasDefaultAccountsSection == true
ASSERT result.hasAccountSelectors == true
ASSERT result.hasSaveButton == true
ASSERT result.canFetchDefaultAccounts == true
ASSERT result.canSaveDefaultAccounts == true
ASSERT result.noPlaceholderText == true
```

**Bug 5 - Color Consistency**:
```
FOR ALL accountType IN ['ASSET', 'LIABILITY', 'EQUITY', 'REVENUE', 'EXPENSE'] DO
  FOR ALL component IN [AccountsTable, AccountTreeView, AccountDetailDialog, AccountManagement] DO
    color := getColorFromComponent(component, accountType)
    standardColor := ACCOUNT_TYPE_COLORS[accountType]
    ASSERT color == standardColor
  END FOR
END FOR
```

**Bug 6 - Seed Script**:
```
result := callAdminSeedEndpoint()
ASSERT result.scriptCalled == "seed_chart_of_accounts.py"
ASSERT result.accountsCreated > 0

accounts := queryAccountsFromDatabase()
FOR ALL account IN accounts WHERE account.account_code LIKE '11%' DO
  ASSERT account.parent_account_id IS NOT NULL
  parentAccount := findAccountByCode('1000')
  ASSERT account.parent_account_id == parentAccount.id
END FOR
```

**Bug 7 - Journal Tab**:
```
result := renderBooksPage()
ASSERT result.hasJournalTab == false
OR
ASSERT result.journalTabHasFunctionalUI == true
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed system produces the same result as the original system.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalSystem(input) = fixedSystem(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for non-bug scenarios, then write property-based tests capturing that behavior.

**Test Cases**:

1. **Non-Development Mode Restriction Preservation**: 
   - Observe that admin seed endpoint returns 403 when DEBUG=false on unfixed code
   - Write test to verify this continues after fix
   - Test with various authentication states

2. **Other Export Formats Preservation**: 
   - Observe that CSV, Excel, JSON exports work on unfixed code
   - Write tests to verify these continue working after authentication fix
   - Test with various filter combinations

3. **Account Table Interactions Preservation**: 
   - Observe sorting, filtering, pagination behavior on unfixed code
   - Write property-based tests generating random sort/filter/page combinations
   - Verify behavior unchanged after color updates

4. **Inventory Seed Script Preservation**: 
   - Observe that direct calls to scripts/seed_data.py create inventory items
   - Write test to verify this continues working after admin endpoint fix
   - Test that inventory items (warehouses, item groups, items) are still created

5. **Other Books Tabs Preservation**: 
   - Observe that Chart of Accounts, Reports, Payments, Configuration tabs work on unfixed code
   - Write tests to verify these continue working after Journal tab removal
   - Test navigation between tabs

6. **Dark Mode Color Preservation**: 
   - Observe that account type badges render correctly in dark mode on unfixed code
   - Write tests to verify dark mode variants still work after color standardization
   - Test color contrast and visibility

7. **Default Account Validation Preservation**: 
   - Observe that backend validates default account selections on unfixed code
   - Write tests to verify validation continues after UI implementation
   - Test with invalid account IDs, wrong account types, non-existent accounts

### Unit Tests

- Test authenticated fetch implementation in Reports component
- Test blob download helper function with various file types
- Test SystemConfiguration component rendering with default accounts section
- Test useDefaultAccounts hook with mock API responses
- Test ACCOUNT_TYPE_COLORS import in each component
- Test getAccountTypeColor helper function with all account types
- Test admin endpoint script path change
- Test BooksPage navigation without Journal tab
- Test error handling for failed exports
- Test loading states during export operations

### Property-Based Tests

- Generate random report filters and verify all exports work with authentication
- Generate random account types and verify colors are consistent across all components
- Generate random organization IDs and verify seed script creates proper hierarchy
- Generate random navigation sequences and verify all tabs work correctly
- Generate random default account configurations and verify save/load works
- Generate random account data and verify table interactions (sort, filter, page) work
- Generate random authentication states and verify non-development mode restrictions

### Integration Tests

- Test full report generation and export flow with authentication
- Test full configuration page flow: load defaults, modify, save, reload
- Test full seed data flow: call endpoint, verify hierarchy, query accounts
- Test full Books page navigation flow across all tabs
- Test color consistency across full user journey (view table, open dialog, check stats)
- Test dark mode toggle with account type badges visible
- Test export in all formats (CSV, Excel, JSON, PDF) with various filters
- Test default accounts configuration with account selection and validation

