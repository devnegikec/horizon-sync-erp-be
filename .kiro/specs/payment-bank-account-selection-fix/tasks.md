# Implementation Plan

- [x] 1. Write bug condition exploration test
  - **Property 1: Fault Condition** - Bank Account Selector for Bank Transfer
  - **CRITICAL**: This test MUST FAIL on unfixed code - failure confirms the bug exists
  - **DO NOT attempt to fix the test or the code when it fails**
  - **NOTE**: This test encodes the expected behavior - it will validate the fix when it passes after implementation
  - **GOAL**: Surface counterexamples that demonstrate the bug exists
  - **Scoped PBT Approach**: Scope the property to payment_mode="Bank_Transfer" with various form states
  - Test that when payment_mode is "Bank_Transfer", the PaymentForm component displays a bank account selector dropdown
  - Test that bank_account_id is included in formData state when payment_mode="Bank_Transfer"
  - Test that bank_account_id is included in CreatePaymentPayload when submitting with payment_mode="Bank_Transfer"
  - Test that validation error appears when payment_mode="Bank_Transfer" and no bank account is selected
  - Run test on UNFIXED code
  - **EXPECTED OUTCOME**: Test FAILS (this is correct - it proves the bug exists)
  - Document counterexamples found:
    - Bank account selector is not rendered when payment_mode="Bank_Transfer"
    - bank_account_id is not in formData state
    - bank_account_id is not in CreatePaymentPayload type definition
    - Validation does not check for bank_account_id requirement
  - Mark task complete when test is written, run, and failure is documented
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Non-Bank-Transfer Payment Modes
  - **IMPORTANT**: Follow observation-first methodology
  - Observe behavior on UNFIXED code for non-buggy inputs (payment_mode="Cash" or "Check")
  - Observe: Cash payments work without bank account selector on unfixed code
  - Observe: Check payments work without bank account selector on unfixed code
  - Observe: Reference number field displays correctly for Check and Bank_Transfer on unfixed code
  - Observe: Invoice allocation section works correctly on unfixed code
  - Write property-based tests capturing observed behavior patterns:
    - For all payment form states where payment_mode is NOT "Bank_Transfer", verify no bank account selector is displayed
    - For all Cash payment submissions, verify payload structure matches original behavior
    - For all Check payment submissions, verify payload structure matches original behavior including reference_no
    - For all payment modes, verify invoice allocation functionality remains unchanged
  - Property-based testing generates many test cases for stronger guarantees
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (this confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 3. Fix for Payment Bank Account Selection

  - [x] 3.1 Update CreatePaymentPayload type definition
    - Add optional bank_account_id field to CreatePaymentPayload interface in `horizon-sync/apps/inventory/src/app/types/payment.types.ts`
    - Add: `bank_account_id?: string;` after the `reference_no` field
    - This matches the backend schema which expects UUID | None
    - _Bug_Condition: isBugCondition(input) where input.payment_mode == 'Bank_Transfer' AND bank_account_id NOT IN CreatePaymentPayload_
    - _Expected_Behavior: bank_account_id field exists in CreatePaymentPayload type definition_
    - _Preservation: Cash and Check payment payloads remain unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.2 Update PaymentForm component state and types
    - Update PaymentFormData type to include: `bank_account_id?: string;`
    - Add bank_account_id to formData state initialization: `bank_account_id: initialData?.bank_account_id,`
    - Update useEffect that syncs initialData to include: `bank_account_id: initialData.bank_account_id,`
    - _Bug_Condition: isBugCondition(input) where input.payment_mode == 'Bank_Transfer' AND bank_account_id NOT IN formData_
    - _Expected_Behavior: bank_account_id field exists in formData state_
    - _Preservation: Existing form state fields remain unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.3 Add bank account fetching logic
    - Create useQuery hook to fetch active bank accounts from `/api/v1/bank-accounts?is_active=true`
    - Use the core API utility to make the API call
    - Store the result in a `bankAccounts` variable
    - Handle loading and error states appropriately
    - _Bug_Condition: isBugCondition(input) where input.payment_mode == 'Bank_Transfer' AND bankAccountSelectorNotDisplayed()_
    - _Expected_Behavior: Active bank accounts are fetched from API when component mounts_
    - _Preservation: No impact on existing API calls or data fetching_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 3.4 Add bank account selector UI component
    - Render Select component conditionally when payment_mode="Bank_Transfer"
    - Position it after the payment_mode field and before the reference_no field
    - Use the same styling as other Select components in the form
    - Display bank_name and masked account number in dropdown options
    - Show validation error if bank account is not selected
    - Create handleBankAccountChange callback: `const handleBankAccountChange = useCallback((value: string) => { setFormData(prev => ({ ...prev, bank_account_id: value })); }, []);`
    - _Bug_Condition: isBugCondition(input) where input.payment_mode == 'Bank_Transfer' AND bankAccountSelectorNotDisplayed()_
    - _Expected_Behavior: Bank account selector is displayed when payment_mode="Bank_Transfer"_
    - _Preservation: No bank account selector displayed for Cash or Check payment modes_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.5 Update handleSubmit to include bank_account_id in payload
    - Add `bank_account_id: formData.bank_account_id,` to the CreatePaymentPayload object in handleSubmit
    - Ensure this is included when mode is 'create'
    - _Bug_Condition: isBugCondition(input) where input.payment_mode == 'Bank_Transfer' AND bank_account_id NOT IN CreatePaymentPayload_
    - _Expected_Behavior: bank_account_id is included in payload when payment_mode="Bank_Transfer"_
    - _Preservation: Cash and Check payment payloads remain unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.6 Add validation logic for bank_account_id
    - Update usePaymentValidation hook to validate bank_account_id is required when payment_mode="Bank_Transfer"
    - Add validation rule: if payment_mode is "Bank_Transfer" and bank_account_id is empty, add error message "Bank account is required for Bank Transfer payments"
    - _Bug_Condition: isBugCondition(input) where input.payment_mode == 'Bank_Transfer' AND bank_account_id is empty_
    - _Expected_Behavior: Validation error displays when bank account is not selected for Bank_Transfer_
    - _Preservation: Existing validation for Cash and Check modes remains unchanged_
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.7 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Bank Account Selector for Bank Transfer
    - **IMPORTANT**: Re-run the SAME test from task 1 - do NOT write a new test
    - The test from task 1 encodes the expected behavior
    - When this test passes, it confirms the expected behavior is satisfied
    - Run bug condition exploration test from step 1
    - **EXPECTED OUTCOME**: Test PASSES (confirms bug is fixed)
    - Verify bank account selector displays when payment_mode="Bank_Transfer"
    - Verify bank_account_id is in formData state
    - Verify bank_account_id is in CreatePaymentPayload
    - Verify validation error appears when no bank account is selected
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

  - [x] 3.8 Verify preservation tests still pass
    - **Property 2: Preservation** - Non-Bank-Transfer Payment Modes
    - **IMPORTANT**: Re-run the SAME tests from task 2 - do NOT write new tests
    - Run preservation property tests from step 2
    - **EXPECTED OUTCOME**: Tests PASS (confirms no regressions)
    - Verify Cash payments work without bank account selector
    - Verify Check payments work without bank account selector
    - Verify reference number field displays correctly
    - Verify invoice allocation section works correctly
    - Confirm all tests still pass after fix (no regressions)
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise
  - Verify bank account selector works correctly for Bank_Transfer payments
  - Verify Cash and Check payment modes continue to work without changes
  - Verify all form fields and validation work as expected
