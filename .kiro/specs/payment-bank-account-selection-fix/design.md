# Payment Bank Account Selection Fix - Bugfix Design

## Overview

This bugfix adds a bank account selector to the PaymentForm component in the inventory app. When users create a payment with payment_mode="Bank_Transfer", they need to select which bank account should be used for the transfer. The backend API already supports the bank_account_id field and validates it, but the frontend is missing the UI component and payload integration. The fix involves adding a conditional bank account selector that appears only for Bank_Transfer payments, fetching active bank accounts from the core API, and including the selected bank_account_id in the CreatePaymentPayload.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when payment_mode is "Bank_Transfer" but no bank account selector is displayed
- **Property (P)**: The desired behavior - a bank account selector should be displayed and the selected bank_account_id should be sent to the backend
- **Preservation**: Existing payment form behavior for Cash and Check payment modes must remain unchanged
- **PaymentForm**: The component in `horizon-sync/apps/inventory/src/app/components/payments/PaymentForm.tsx` that renders the payment creation form
- **CreatePaymentPayload**: The TypeScript interface in `horizon-sync/apps/inventory/src/app/types/payment.types.ts` that defines the payload structure for creating payments
- **payment_mode**: The field that determines the payment method (Cash, Check, or Bank_Transfer)
- **bank_account_id**: The UUID field that identifies which bank account is used for Bank_Transfer payments

## Bug Details

### Fault Condition

The bug manifests when a user selects payment_mode="Bank_Transfer" in the PaymentForm component. The form does not display a bank account selector field, does not include bank_account_id in the formData state, and does not send bank_account_id to the backend API when submitting the payment.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type PaymentFormState
  OUTPUT: boolean
  
  RETURN input.payment_mode == 'Bank_Transfer'
         AND bankAccountSelectorNotDisplayed()
         AND bank_account_id NOT IN input.formData
         AND bank_account_id NOT IN CreatePaymentPayload
END FUNCTION
```

### Examples

- User selects payment_mode="Bank_Transfer" → Expected: Bank account selector appears | Actual: No selector displayed
- User submits payment with payment_mode="Bank_Transfer" → Expected: bank_account_id included in payload | Actual: bank_account_id missing from payload
- User creates payment with payment_mode="Cash" → Expected: No bank account selector | Actual: No bank account selector (correct)
- User creates payment with payment_mode="Bank_Transfer" without selecting bank account → Expected: Validation error displayed | Actual: Field doesn't exist to validate

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Cash payment mode must continue to work without requiring or displaying a bank account selector
- Check payment mode must continue to work without requiring or displaying a bank account selector
- Reference number field must continue to be displayed and required for Check and Bank_Transfer modes
- All existing form fields (payment_type, party_id, amount, currency_code, payment_date, payment_mode) must continue to function correctly
- Edit mode functionality must continue to work with all existing fields
- Invoice allocation section must continue to function correctly

**Scope:**
All inputs that do NOT involve payment_mode="Bank_Transfer" should be completely unaffected by this fix. This includes:
- Cash payments (no bank account selector)
- Check payments (no bank account selector)
- All other form interactions (party selection, amount entry, date selection, etc.)
- Invoice allocation functionality

## Hypothesized Root Cause

Based on the bug description, the root causes are:

1. **Missing Type Definition**: The CreatePaymentPayload interface does not include bank_account_id as an optional field
   - Located in `horizon-sync/apps/inventory/src/app/types/payment.types.ts`
   - Needs to add: `bank_account_id?: string;`

2. **Missing Form State**: The PaymentForm component's formData state does not include bank_account_id
   - Located in `horizon-sync/apps/inventory/src/app/components/payments/PaymentForm.tsx`
   - The useState initialization and PaymentFormData type need to include bank_account_id

3. **Missing UI Component**: The PaymentForm component does not render a bank account selector when payment_mode="Bank_Transfer"
   - No conditional rendering logic exists for bank account selection
   - No API call to fetch active bank accounts

4. **Missing Payload Integration**: The handleSubmit function does not include bank_account_id when constructing the CreatePaymentPayload
   - The payload construction in handleSubmit needs to conditionally include bank_account_id

5. **Missing Validation**: The usePaymentValidation hook does not validate that bank_account_id is required when payment_mode="Bank_Transfer"
   - Validation logic needs to be added to ensure bank account is selected for Bank_Transfer payments

## Correctness Properties

Property 1: Fault Condition - Bank Account Selector for Bank Transfer

_For any_ payment form state where payment_mode is "Bank_Transfer", the PaymentForm component SHALL display a bank account selector dropdown that fetches and displays active bank accounts, and when submitted, SHALL include the selected bank_account_id in the CreatePaymentPayload sent to the backend API.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7**

Property 2: Preservation - Non-Bank-Transfer Payment Modes

_For any_ payment form state where payment_mode is NOT "Bank_Transfer" (i.e., "Cash" or "Check"), the PaymentForm component SHALL produce exactly the same behavior as the original component, preserving all existing functionality including form display, validation, and payload submission without requiring or displaying a bank account selector.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `horizon-sync/apps/inventory/src/app/types/payment.types.ts`

**Interface**: `CreatePaymentPayload`

**Specific Changes**:
1. **Add bank_account_id field**: Add optional bank_account_id field to CreatePaymentPayload interface
   - Add: `bank_account_id?: string;` after the `reference_no` field
   - This matches the backend schema which expects UUID | None

**File**: `horizon-sync/apps/inventory/src/app/components/payments/PaymentForm.tsx`

**Component**: `PaymentForm`

**Specific Changes**:
1. **Update formData state type**: Add bank_account_id to PaymentFormData type in usePaymentValidation hook
   - Modify the PaymentFormData interface to include: `bank_account_id?: string;`

2. **Initialize bank_account_id in state**: Add bank_account_id to the useState initialization
   - Add `bank_account_id: initialData?.bank_account_id,` to the formData state initialization

3. **Add bank account fetching logic**: Create a useQuery hook to fetch active bank accounts
   - Use the core API utility to call `/api/v1/bank-accounts?is_active=true`
   - Store the result in a `bankAccounts` variable

4. **Add bank account selector UI**: Render a Select component conditionally when payment_mode="Bank_Transfer"
   - Position it after the payment_mode field and before the reference_no field
   - Use the same styling as other Select components in the form
   - Display bank_name and masked account number in the dropdown options
   - Show validation error if bank account is not selected

5. **Add handleBankAccountChange handler**: Create a callback to update formData.bank_account_id
   - Use useCallback for performance: `const handleBankAccountChange = useCallback((value: string) => { setFormData(prev => ({ ...prev, bank_account_id: value })); }, []);`

6. **Update handleSubmit payload**: Include bank_account_id in the CreatePaymentPayload when mode is 'create'
   - Add `bank_account_id: formData.bank_account_id,` to the payload object

7. **Add validation logic**: Update usePaymentValidation hook to validate bank_account_id is required when payment_mode="Bank_Transfer"
   - Add validation rule: if payment_mode is "Bank_Transfer" and bank_account_id is empty, add error message

8. **Sync bank_account_id in useEffect**: Update the useEffect that syncs initialData to include bank_account_id
   - Add `bank_account_id: initialData.bank_account_id,` to the setFormData call in the useEffect

**File**: `horizon-sync/apps/inventory/src/app/hooks/usePaymentValidation.ts` (if it exists as a separate file)

**Hook**: `usePaymentValidation`

**Specific Changes**:
1. **Add bank_account_id validation**: Add validation logic for bank_account_id when payment_mode="Bank_Transfer"
   - Check if payment_mode is "Bank_Transfer" and bank_account_id is undefined/empty
   - Add error message: "Bank account is required for Bank Transfer payments"

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Write tests that simulate selecting payment_mode="Bank_Transfer" and verify that a bank account selector is displayed and the bank_account_id is included in the payload. Run these tests on the UNFIXED code to observe failures and understand the root cause.

**Test Cases**:
1. **Bank Account Selector Display Test**: Select payment_mode="Bank_Transfer" and verify selector appears (will fail on unfixed code)
2. **Bank Account Selector Not Display for Cash Test**: Select payment_mode="Cash" and verify selector does not appear (should pass on unfixed code)
3. **Bank Account ID in Payload Test**: Submit payment with payment_mode="Bank_Transfer" and verify bank_account_id is in payload (will fail on unfixed code)
4. **Validation Error Test**: Submit payment with payment_mode="Bank_Transfer" without selecting bank account and verify error is shown (will fail on unfixed code - field doesn't exist)

**Expected Counterexamples**:
- Bank account selector is not rendered when payment_mode="Bank_Transfer"
- bank_account_id is not included in CreatePaymentPayload type definition
- bank_account_id is not included in formData state
- Possible causes: missing type definition, missing state field, missing UI component, missing payload integration

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed function produces the expected behavior.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := PaymentForm_fixed(input)
  ASSERT bankAccountSelectorDisplayed(result)
  ASSERT bank_account_id IN result.formData
  ASSERT bank_account_id IN result.payload
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT PaymentForm_original(input) = PaymentForm_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Observe behavior on UNFIXED code first for Cash and Check payment modes, then write property-based tests capturing that behavior.

**Test Cases**:
1. **Cash Payment Preservation**: Observe that Cash payments work correctly on unfixed code (no bank account selector), then write test to verify this continues after fix
2. **Check Payment Preservation**: Observe that Check payments work correctly on unfixed code (no bank account selector, reference_no required), then write test to verify this continues after fix
3. **Reference Number Preservation**: Observe that reference_no field displays correctly for Check and Bank_Transfer on unfixed code, then write test to verify this continues after fix
4. **Invoice Allocation Preservation**: Observe that invoice allocation section works correctly on unfixed code, then write test to verify this continues after fix

### Unit Tests

- Test bank account selector displays when payment_mode="Bank_Transfer"
- Test bank account selector does not display when payment_mode="Cash"
- Test bank account selector does not display when payment_mode="Check"
- Test bank_account_id is included in payload when payment_mode="Bank_Transfer" and bank account is selected
- Test validation error displays when payment_mode="Bank_Transfer" and no bank account is selected
- Test bank accounts are fetched from API when component mounts
- Test bank account selector displays bank_name and masked account number

### Property-Based Tests

- Generate random payment form states with payment_mode="Bank_Transfer" and verify bank account selector is always displayed
- Generate random payment form states with payment_mode="Cash" or "Check" and verify bank account selector is never displayed
- Generate random bank account selections and verify bank_account_id is always included in payload for Bank_Transfer payments
- Test that all non-Bank_Transfer payment modes continue to work across many scenarios

### Integration Tests

- Test full payment creation flow with payment_mode="Bank_Transfer" and bank account selection
- Test switching between payment modes and verify bank account selector appears/disappears correctly
- Test that bank account selector fetches and displays active bank accounts from the API
- Test that validation errors display correctly when bank account is not selected for Bank_Transfer
- Test that Cash and Check payment modes continue to work end-to-end after the fix
