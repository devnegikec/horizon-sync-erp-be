# Chart of Account Bug Validation Tests

This document outlines the comprehensive test cases created to validate the fixes for the Chart of Account issues that were reported as still occurring.

## Issues Being Validated

### 1. Balance Not Populating in UI
**Problem**: Account balances are not showing up in the user interface.
**Tests**: `TestChartOfAccountBalancePopulation`

### 2. Correct Level Hierarchy Not Populating on UI
**Problem**: Account hierarchy levels are not being calculated or displayed correctly.
**Tests**: `TestChartOfAccountHierarchyLevels`

### 3. Correct Group Hierarchy Not Populating on UI
**Problem**: The `is_group` flag and group relationships are not working properly.
**Tests**: `TestChartOfAccountGroupHierarchy`

### 4. Pagination Not Working for Chart of Account Landing Page
**Problem**: Pagination controls and logic are not functioning on the main Chart of Accounts page.
**Tests**: `TestChartOfAccountPagination`

### 5. Edit Account Dialog Not Populating Parent Account Name
**Problem**: When editing an account, the parent account name is not showing in the dialog.
**Tests**: `TestEditAccountDialogParentName`

## Test Files

### Core Test File
- `tests/test_chart_of_accounts_bug_validation.py` - Main test cases for all issues
- `tests/test_chart_of_accounts_test_utils.py` - Test utilities and fixtures

## Running the Tests

### Prerequisites
Make sure your test environment is set up:
```bash
# Activate virtual environment
source .venv/Scripts/activate  # On Windows
# source .venv/bin/activate    # On Linux/Mac

# Install test dependencies
pip install pytest pytest-asyncio

# Set up test database
# (Make sure your test database is configured)
```

### Run All Bug Validation Tests
```bash
pytest tests/test_chart_of_accounts_bug_validation.py -v
```

### Run Tests by Issue Category

#### Issue 1: Balance Population 
```bash
pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountBalancePopulation -v
```

**Test Cases:**
- `test_list_accounts_includes_balance_in_response` - Verifies balance fields are in account list API
- `test_individual_account_get_includes_balance` - Verifies balance info in single account GET
- `test_balance_calculation_service_works` - Tests the underlying balance calculation service

#### Issue 2: Level Hierarchy
```bash
pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountHierarchyLevels -v
```

**Test Cases:**
- `test_account_levels_calculated_correctly` - Tests that parent/child/grandchild levels are 1/2/3
- `test_level_calculation_during_account_creation` - Tests automatic level calculation when creating accounts
- `test_level_appears_in_account_list_schema` - Verifies level field is in API response

#### Issue 3: Group Hierarchy
```bash
pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountGroupHierarchy -v
```

**Test Cases:**
- `test_is_group_flag_populated_correctly` - Tests `is_group` flag for parent vs leaf accounts
- `test_group_hierarchy_with_tree_structure` - Tests complex hierarchy relationships
- `test_is_group_automatically_set_when_creating_child` - Tests automatic group flagging

#### Issue 4: Pagination
```bash
pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountPagination -v
```

**Test Cases:**
- `test_pagination_metadata_returned` - Tests pagination metadata structure
- `test_pagination_page_navigation` - Tests navigation between different pages
- `test_pagination_with_filters` - Tests pagination with account type filters
- `test_pagination_edge_cases` - Tests edge cases like invalid page numbers

#### Issue 5: Parent Account Name in Edit Dialog
```bash
pytest tests/test_chart_of_accounts_bug_validation.py::TestEditAccountDialogParentName -v
```

**Test Cases:**
- `test_account_response_includes_parent_info` - Tests individual account GET includes parent data  
- `test_account_list_includes_parent_names` - Tests account list includes parent IDs
- `test_account_hierarchy_endpoint` - Tests hierarchy endpoints (if they exist)
- `test_update_account_preserves_parent_info` - Tests parent info is preserved during updates

## Expected Test Results

### When Tests Pass
If the fixes are working correctly, all tests should pass. This means:

1. **Balance fields** (`current_balance`, `opening_balance`) are present in API responses
2. **Level values** (1, 2, 3, etc.) are correctly calculated and returned
3. **Group flags** (`is_group` true/false) are properly set for parent accounts
4. **Pagination metadata** includes all required fields with correct values
5. **Parent information** is available in account responses for edit dialogs

### When Tests Fail
If any tests fail, it indicates the corresponding issue is not fully fixed:

1. **Balance test failures** → Balance calculation or API serialization problems
2. **Level test failures** → Hierarchy level calculation issues  
3. **Group test failures** → Group flagging logic problems
4. **Pagination test failures** → Pagination implementation issues
5. **Parent name test failures** → Parent data serialization problems

## Debugging Failed Tests

### Enable Debug Logging
```bash
pytest tests/test_chart_of_accounts_bug_validation.py -v -s --log-cli-level=DEBUG
```

### Run Single Test with Full Output  
```bash
pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountBalancePopulation::test_list_accounts_includes_balance_in_response -v -s
```

### Check Database State
The tests create sample data. You can inspect the database after running tests to see what data was created and whether the issue is in data creation or API serialization.

### Common Debugging Steps

1. **Check API Response Structure**: Look at the actual response JSON to see which fields are missing
2. **Verify Database Data**: Ensure test accounts are being created with correct values
3. **Check Service Layer**: Verify the ChartOfAccountService methods are returning expected data
4. **Review Model Serialization**: Check if Pydantic schemas are including all required fields

## Integration with CI/CD

These tests can be integrated into your continuous integration pipeline:

```yaml
# Example GitHub Actions or similar
- name: Run Chart of Account Bug Validation Tests
  run: |
    pytest tests/test_chart_of_accounts_bug_validation.py \
      --junitxml=test-results/chart-of-accounts-bugs.xml \
      --cov=app/services/chart_of_account_service \
      --cov=app/api/v1/endpoints/chart_of_accounts
```

## Test Data Cleanup

The tests use pytest fixtures that should automatically clean up test data. However, if you need to manually clean up:

```sql
-- Clean up test accounts (be careful in production!)
DELETE FROM account_balances WHERE account_id IN (
  SELECT id FROM accounts WHERE account_code LIKE 'T%' OR account_code LIKE 'P%'
);
DELETE FROM accounts WHERE account_code LIKE 'T%' OR account_code LIKE 'P%';
DELETE FROM organizations WHERE name = 'Test Organization';
```

## Extending the Tests

To add more test cases for new scenarios:

1. Add new test methods to the appropriate test class
2. Use the helper functions in `test_chart_of_accounts_test_utils.py`
3. Follow the existing naming convention: `test_{what_is_being_tested}`
4. Include both positive and negative test cases
5. Document the expected behavior in the test docstring

## Next Steps After Running Tests

1. **If all tests pass**: The reported issues should be resolved
2. **If tests fail**: Use the failure information to identify remaining problems
3. **Fix failing functionality** and re-run tests until they pass
4. **Add these tests to the regular test suite** to prevent regression
5. **Update API documentation** to reflect the correct response structures

This comprehensive test suite ensures that all the reported Chart of Account issues are properly validated and can be used to verify that fixes are working correctly.