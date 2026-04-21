# Bugfix Requirements Document: Invoice Journal Entries Fix

## Introduction

The AR/AP accounting workflow is incomplete and violates double-entry accounting principles. When invoices are confirmed/submitted (Stage A), the system fails to create journal entries to record accounts receivable/payable and revenue/expense. This causes:

- Inaccurate financial reports (missing AR/Revenue and AP/Expense entries)
- Incomplete audit trail for invoice confirmations
- Balance sheet doesn't reflect true receivables/payables
- Revenue/expense recognition not recorded at invoice confirmation

Additionally, payment journal entries (Stage B) use generic "bank" accounts instead of specific bank accounts (HDFC, ICICI, etc.), preventing accurate tracking of which bank account received or paid money.

The bug affects the complete invoice-to-payment lifecycle:
- **Stage A (Invoice Confirmation)**: Missing journal entries ❌
- **Stage B (Payment Confirmation)**: Works but uses wrong account ⚠️
- **Stage C (Payment Cancellation)**: Works but reverses wrong account ⚠️

## Bug Analysis

### Current Behavior (Defect)

**Stage A: Invoice Confirmation - Missing Journal Entries**

1.1 WHEN a sales invoice is confirmed/submitted THEN the system does not create any journal entry

1.2 WHEN a purchase invoice is confirmed/submitted THEN the system does not create any journal entry

1.3 WHEN an invoice status changes from "draft" to "submitted" THEN no accounts receivable or accounts payable entry is recorded

1.4 WHEN an invoice is confirmed THEN no revenue or expense recognition occurs in the general ledger

**Stage B: Payment Confirmation - Wrong Account Used**

1.5 WHEN a customer payment is confirmed with payment_mode "Bank_Transfer" THEN the system creates a journal entry debiting the generic "bank" default account instead of the specific bank account's GL account

1.6 WHEN a supplier payment is confirmed with payment_mode "Bank_Transfer" THEN the system creates a journal entry crediting the generic "bank" default account instead of the specific bank account's GL account

1.7 WHEN a payment is recorded THEN the PaymentEntry model has no bank_account_id field to link to a specific bank account

**Stage C: Payment Cancellation - Wrong Account Reversed**

1.8 WHEN a payment is cancelled THEN the system creates a reversing entry using the generic "bank" default account instead of the specific bank account's GL account

**Outstanding Amount Tracking**

1.9 WHEN an invoice is created THEN the outstanding_amount field is set to the grand_total value

1.10 WHEN payments are allocated to an invoice THEN the outstanding_amount field may not update automatically to reflect remaining balance

### Expected Behavior (Correct)

**Stage A: Invoice Confirmation - Create Journal Entries**

2.1 WHEN a sales invoice is confirmed/submitted THEN the system SHALL create a journal entry with:
   - Debit: Accounts Receivable (default account for "accounts_receivable")
   - Credit: Sales Revenue (default account for "sales_revenue")
   - Amount: Invoice grand_total in base currency
   - Reference: Invoice ID and invoice_no

2.2 WHEN a purchase invoice is confirmed/submitted THEN the system SHALL create a journal entry with:
   - Debit: Purchase Expense (default account for "purchase_expense")
   - Credit: Accounts Payable (default account for "accounts_payable")
   - Amount: Invoice grand_total in base currency
   - Reference: Invoice ID and invoice_no

2.3 WHEN an invoice status changes from "draft" to "submitted" THEN the system SHALL automatically trigger journal entry creation

2.4 WHEN an invoice is confirmed THEN the system SHALL set the invoice.submitted_at timestamp to the current datetime

**Stage B: Payment Confirmation - Use Specific Bank Account**

2.5 WHEN a customer payment is confirmed with payment_mode "Bank_Transfer" and a bank_account_id is provided THEN the system SHALL create a journal entry debiting the specific bank account's gl_account_id instead of the generic "bank" default account

2.6 WHEN a supplier payment is confirmed with payment_mode "Bank_Transfer" and a bank_account_id is provided THEN the system SHALL create a journal entry crediting the specific bank account's gl_account_id instead of the generic "bank" default account

2.7 WHEN a payment is recorded THEN the PaymentEntry model SHALL include a bank_account_id field (nullable, foreign key to bank_accounts.id) to link to a specific bank account

2.8 WHEN a payment is confirmed with payment_mode "Bank_Transfer" and no bank_account_id is provided THEN the system SHALL fall back to the generic "bank" default account for backward compatibility

**Stage C: Payment Cancellation - Reverse Specific Bank Account**

2.9 WHEN a payment with a bank_account_id is cancelled THEN the system SHALL create a reversing entry using the specific bank account's gl_account_id

2.10 WHEN a payment without a bank_account_id is cancelled THEN the system SHALL create a reversing entry using the generic "bank" default account

**Outstanding Amount Tracking**

2.11 WHEN an invoice is confirmed THEN the outstanding_amount field SHALL be set equal to grand_total

2.12 WHEN payments are allocated to an invoice THEN the InvoiceStatusService.update_invoice_status method SHALL recalculate outstanding_amount as (grand_total - total_allocated_payments)

2.13 WHEN a payment allocation is cancelled THEN the InvoiceStatusService.update_invoice_status method SHALL recalculate outstanding_amount to reflect the increased balance

### Unchanged Behavior (Regression Prevention)

**Existing Payment Flow**

3.1 WHEN a customer payment is confirmed with payment_mode "Cash" THEN the system SHALL CONTINUE TO create a journal entry debiting the "cash" default account and crediting accounts receivable

3.2 WHEN a customer payment is confirmed with payment_mode "Check" THEN the system SHALL CONTINUE TO create a journal entry debiting the "checks_received" default account and crediting accounts receivable

3.3 WHEN a supplier payment is confirmed with payment_mode "Cash" THEN the system SHALL CONTINUE TO create a journal entry debiting accounts payable and crediting the "cash" default account

3.4 WHEN a supplier payment is confirmed with payment_mode "Check" THEN the system SHALL CONTINUE TO create a journal entry debiting accounts payable and crediting the "checks_received" default account

**Existing Payment Cancellation**

3.5 WHEN a payment with payment_mode "Cash" or "Check" is cancelled THEN the system SHALL CONTINUE TO create reversing entries using the appropriate default accounts

**Invoice CRUD Operations**

3.6 WHEN an invoice in "draft" status is created THEN the system SHALL CONTINUE TO allow creation without creating journal entries

3.7 WHEN an invoice in "draft" status is updated THEN the system SHALL CONTINUE TO allow updates without creating journal entries

3.8 WHEN an invoice in "draft" status is deleted THEN the system SHALL CONTINUE TO allow deletion without affecting journal entries

**Invoice Status Transitions**

3.9 WHEN an invoice status changes from "submitted" to "paid" or "partial" due to payment allocations THEN the system SHALL CONTINUE TO update the status automatically via InvoiceStatusService

3.10 WHEN an invoice is already in "submitted" status and is updated (but not re-submitted) THEN the system SHALL CONTINUE TO allow updates without creating duplicate journal entries

**Default Account Configuration**

3.11 WHEN default accounts for "accounts_receivable", "accounts_payable", "sales_revenue", and "purchase_expense" are not configured THEN the system SHALL CONTINUE TO raise a ValidationError preventing invoice confirmation

3.12 WHEN journal entries are created THEN the system SHALL CONTINUE TO validate that total debits equal total credits

**Currency Conversion**

3.13 WHEN an invoice is in a foreign currency THEN the system SHALL CONTINUE TO convert amounts to the organization's base currency for journal entries using the CurrencyService

**Journal Entry Structure**

3.14 WHEN journal entries are created for payments THEN the system SHALL CONTINUE TO include reference_type, reference_id, against_account_id, and remarks fields in journal entry lines

3.15 WHEN journal entries are created THEN the system SHALL CONTINUE TO set status to "posted" and voucher_type appropriately
