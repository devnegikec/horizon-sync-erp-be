# Bugfix Requirements Document

## Introduction

The "Create New Payment" dialog in the inventory app is missing the ability to select a bank account when creating payments with payment_mode="Bank_Transfer". The backend API expects a `bank_account_id` field (UUID) for Bank_Transfer payments and validates that the bank account exists, belongs to the organization, and is active. However, the frontend PaymentForm component does not include a bank account selector or send the `bank_account_id` field to the backend, preventing users from specifying which bank account should be used for the transfer.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN a user creates a payment with payment_mode="Bank_Transfer" THEN the system does not display a bank account selector field

1.2 WHEN a user submits a payment with payment_mode="Bank_Transfer" THEN the system does not include bank_account_id in the CreatePaymentPayload

1.3 WHEN the CreatePaymentPayload type is defined THEN the system does not include bank_account_id as a field

1.4 WHEN the PaymentForm formData state is initialized THEN the system does not include bank_account_id in the state

### Expected Behavior (Correct)

2.1 WHEN a user selects payment_mode="Bank_Transfer" THEN the system SHALL display a bank account selector dropdown

2.2 WHEN the bank account selector is displayed THEN the system SHALL fetch and display active bank accounts for the organization

2.3 WHEN a bank account is displayed in the selector THEN the system SHALL show the bank name and masked account number

2.4 WHEN a user submits a payment with payment_mode="Bank_Transfer" and a bank account selected THEN the system SHALL include the selected bank_account_id in the CreatePaymentPayload

2.5 WHEN the CreatePaymentPayload type is defined THEN the system SHALL include bank_account_id as an optional UUID field

2.6 WHEN the PaymentForm formData state is initialized THEN the system SHALL include bank_account_id in the state

2.7 WHEN a user submits a payment with payment_mode="Bank_Transfer" without selecting a bank account THEN the system SHALL display a validation error

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a user creates a payment with payment_mode="Cash" THEN the system SHALL CONTINUE TO not display or require a bank account selector

3.2 WHEN a user creates a payment with payment_mode="Check" THEN the system SHALL CONTINUE TO not display or require a bank account selector

3.3 WHEN a user creates a payment with payment_mode="Check" or "Bank_Transfer" THEN the system SHALL CONTINUE TO display and require the reference_no field

3.4 WHEN a user creates a payment with any payment_mode THEN the system SHALL CONTINUE TO validate all existing required fields (payment_type, party_id, amount, currency_code, payment_date, payment_mode)

3.5 WHEN a user creates a payment in edit mode THEN the system SHALL CONTINUE TO function correctly with the existing fields

3.6 WHEN a user creates a payment with invoice allocation THEN the system SHALL CONTINUE TO function correctly with the allocation section
