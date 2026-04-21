# Invoice Journal Entries Fix - Technical Design

## Overview

This design addresses three critical bugs in the AR/AP accounting workflow that violate double-entry accounting principles:

1. **Bug 1 - Missing Invoice Journal Entries (Stage A)**: When invoices are confirmed/submitted, no journal entries are created to record AR/AP and Revenue/Expense, causing inaccurate financial reports and incomplete audit trails.

2. **Bug 2 - Generic Bank Account Usage (Stage B & C)**: Payment journal entries use a generic "bank" default account instead of specific bank accounts (HDFC, ICICI, etc.), preventing accurate tracking of which bank account received or paid money.

3. **Bug 3 - Outstanding Amount Updates**: Invoice outstanding_amount field may not update automatically when payments are allocated or cancelled, causing incorrect balance tracking.

The fix ensures proper double-entry accounting at all stages: invoice confirmation creates AR/AP entries, payments use specific bank accounts, and outstanding amounts update automatically.

## Glossary

- **Bug_Condition_1 (C1)**: Invoice status changes from "draft" to "submitted" without creating journal entries
- **Bug_Condition_2 (C2)**: Payment with payment_mode "Bank_Transfer" uses generic "bank" account instead of specific bank account's gl_account_id
- **Bug_Condition_3 (C3)**: Invoice outstanding_amount does not reflect current payment allocations
- **Property (P)**: The desired behavior - proper journal entries created, specific bank accounts used, outstanding amounts accurate
- **Preservation**: Existing payment flows (Cash, Check), invoice CRUD operations, and status transitions must remain unchanged
- **JournalPostingService**: Service in `app/services/journal_posting_service.py` that creates payment journal entries
- **InvoiceService**: Service in `app/services/invoice_service.py` that manages invoice CRUD operations
- **InvoiceStatusService**: Service in `app/services/invoice_status_service.py` that updates invoice status based on payment allocations
- **DefaultAccountService**: Service that retrieves default GL accounts for transaction types (accounts_receivable, accounts_payable, sales_revenue, purchase_expense, bank, cash, checks_received)
- **PaymentEntry**: Model representing actual money received or paid, currently lacks bank_account_id field
- **BankAccount**: Model linking GL accounts with banking information, has gl_account_id field
- **Stage A**: Invoice confirmation - when status changes from "draft" to "submitted"
- **Stage B**: Payment confirmation - when payment status changes to "confirmed"
- **Stage C**: Payment cancellation - when payment is cancelled and reversing entry created


## Bug Details

### Bug 1: Fault Condition - Missing Invoice Journal Entries

The bug manifests when an invoice status changes from "draft" to "submitted". The InvoiceService does not trigger journal entry creation, causing no AR/AP or Revenue/Expense entries to be recorded in the general ledger.

**Formal Specification:**
```
FUNCTION isBugCondition1(input)
  INPUT: input of type InvoiceStatusChange
  OUTPUT: boolean
  
  RETURN input.old_status == "draft"
         AND input.new_status == "submitted"
         AND input.invoice_type IN ["Sales", "Purchase"]
         AND NOT journalEntryCreated(input.invoice_id, "Invoice Confirmation")
END FUNCTION
```

### Bug 2: Fault Condition - Generic Bank Account Usage

The bug manifests when a payment with payment_mode "Bank_Transfer" is confirmed. The JournalPostingService uses the generic "bank" default account instead of the specific bank account's gl_account_id from the BankAccount model.

**Formal Specification:**
```
FUNCTION isBugCondition2(input)
  INPUT: input of type PaymentConfirmation
  OUTPUT: boolean
  
  RETURN input.payment_mode == "Bank_Transfer"
         AND input.bank_account_id IS NOT NULL
         AND journalEntryUsesAccount(input.payment_id, "bank_default_account")
         AND NOT journalEntryUsesAccount(input.payment_id, input.bank_account.gl_account_id)
END FUNCTION
```

### Bug 3: Fault Condition - Outstanding Amount Not Updated

The bug manifests when payments are allocated to or cancelled from an invoice. The Invoice.outstanding_amount field does not automatically recalculate to reflect the current balance.

**Formal Specification:**
```
FUNCTION isBugCondition3(input)
  INPUT: input of type PaymentAllocationChange
  OUTPUT: boolean
  
  RETURN (input.action == "payment_allocated" OR input.action == "payment_cancelled")
         AND invoice.outstanding_amount != (invoice.grand_total - total_allocated_payments)
END FUNCTION
```

### Examples

**Bug 1 Examples:**
- Sales invoice with grand_total $1,000 is confirmed → No journal entry created (Expected: Debit AR $1,000, Credit Revenue $1,000)
- Purchase invoice with grand_total $500 is confirmed → No journal entry created (Expected: Debit Expense $500, Credit AP $500)
- Invoice in foreign currency (EUR 800) is confirmed → No journal entry with base currency conversion
- Invoice confirmation fails if default accounts not configured → Expected behavior (validation should occur)

**Bug 2 Examples:**
- Customer payment $1,000 via Bank_Transfer to HDFC account → Journal entry debits generic "bank" account instead of HDFC's gl_account_id
- Supplier payment $500 via Bank_Transfer from ICICI account → Journal entry credits generic "bank" account instead of ICICI's gl_account_id
- Payment via Cash → Correctly uses "cash" default account (no bug)
- Payment via Bank_Transfer without bank_account_id → Should fall back to generic "bank" account for backward compatibility

**Bug 3 Examples:**
- Invoice with grand_total $1,000, payment allocated $300 → outstanding_amount should be $700 but may still show $1,000
- Invoice with outstanding_amount $700, payment cancelled → outstanding_amount should increase back to $1,000
- Invoice with multiple partial payments → outstanding_amount should reflect sum of all allocations


## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**

**Existing Payment Flow (Cash, Check):**
- Customer payments via Cash must continue to debit "cash" default account and credit AR
- Customer payments via Check must continue to debit "checks_received" default account and credit AR
- Supplier payments via Cash must continue to debit AP and credit "cash" default account
- Supplier payments via Check must continue to debit AP and credit "checks_received" default account
- Payment cancellations for Cash/Check must continue to create reversing entries using appropriate default accounts

**Invoice CRUD Operations:**
- Invoices in "draft" status must continue to allow creation without creating journal entries
- Invoices in "draft" status must continue to allow updates without creating journal entries
- Invoices in "draft" status must continue to allow deletion without affecting journal entries
- Invoices already in "submitted" status that are updated (but not re-submitted) must not create duplicate journal entries

**Invoice Status Transitions:**
- Invoice status changes from "submitted" to "paid" or "partial" due to payment allocations must continue to update automatically via InvoiceStatusService
- InvoiceStatusService.update_invoice_status must continue to recalculate status based on total_allocated vs grand_total

**Default Account Configuration:**
- System must continue to raise ValidationError if required default accounts are not configured before invoice confirmation or payment confirmation
- Journal entries must continue to validate that total debits equal total credits

**Currency Conversion:**
- Invoices and payments in foreign currency must continue to convert amounts to organization's base currency for journal entries using CurrencyService

**Journal Entry Structure:**
- Journal entries must continue to include reference_type, reference_id, against_account_id, and remarks fields in journal entry lines
- Journal entries must continue to set status to "posted" and voucher_type appropriately
- Journal entries must continue to maintain audit trail (no deletion, only reversing entries)

**Scope:**
All inputs that do NOT involve invoice confirmation (Bug 1), Bank_Transfer payments with bank_account_id (Bug 2), or payment allocations (Bug 3) should be completely unaffected by this fix. This includes:
- Draft invoice operations (create, update, delete)
- Cash and Check payment flows
- Manual invoice status updates
- Invoice queries and reporting


## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

### Bug 1: Missing Invoice Journal Entries

1. **No Journal Entry Creation Logic in InvoiceService**: The InvoiceService.create() and InvoiceService.update() methods do not call any journal posting service when invoice status changes to "submitted". There is no integration point between invoice confirmation and journal entry creation.

2. **Missing Invoice Confirmation Endpoint Logic**: The API endpoint that handles invoice confirmation (status change from "draft" to "submitted") does not trigger journal entry creation. The endpoint likely only updates the status field without accounting implications.

3. **No submitted_at Timestamp Update**: The Invoice model has a submitted_at field, but it's not being set when status changes to "submitted", indicating the confirmation logic is incomplete.

4. **Missing Default Account Validation**: Before creating invoice journal entries, the system should validate that required default accounts (accounts_receivable, accounts_payable, sales_revenue, purchase_expense) are configured, but this validation is not present in invoice confirmation flow.

### Bug 2: Generic Bank Account Usage

1. **PaymentEntry Model Missing bank_account_id Field**: The PaymentEntry model does not have a bank_account_id foreign key field to link to the BankAccount table. Without this field, the system cannot know which specific bank account was used for the payment.

2. **JournalPostingService Hardcoded to Use Default Account**: The _get_payment_account_by_mode() method in JournalPostingService maps "Bank_Transfer" to the "bank" transaction type, which retrieves the generic bank default account. There is no logic to check for a specific bank_account_id and use its gl_account_id instead.

3. **No Bank Account Selection in Payment Flow**: The payment creation and confirmation endpoints likely do not accept or store a bank_account_id parameter, so even if the model had the field, it wouldn't be populated.

4. **Reversing Entry Uses Same Logic**: The reverse_payment_journal_entry() method retrieves the original journal entry and reverses it, so if the original entry used the wrong account, the reversal will also use the wrong account.

### Bug 3: Outstanding Amount Not Updated

1. **InvoiceStatusService Doesn't Update outstanding_amount**: The InvoiceStatusService.update_invoice_status() method calculates outstanding_balance but only updates the invoice.status field. The calculated outstanding_balance is not assigned to invoice.outstanding_amount.

2. **No Automatic Trigger on Payment Allocation**: When payments are allocated to invoices (PaymentReference created), there may be no automatic trigger to call InvoiceStatusService.update_invoice_status() to recalculate the outstanding amount.

3. **Initial outstanding_amount Not Set on Confirmation**: When an invoice is confirmed, the outstanding_amount should be set equal to grand_total, but this initialization may not occur in the invoice confirmation logic.


## Correctness Properties

Property 1: Fault Condition - Invoice Journal Entries Created on Confirmation

_For any_ invoice where the status changes from "draft" to "submitted", the fixed system SHALL create a journal entry with appropriate debits and credits (AR/Revenue for sales invoices, Expense/AP for purchase invoices), set the submitted_at timestamp, and initialize outstanding_amount to grand_total.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.11**

Property 2: Fault Condition - Specific Bank Account Used in Payment Journal Entries

_For any_ payment with payment_mode "Bank_Transfer" and a bank_account_id provided, the fixed system SHALL create a journal entry using the specific bank account's gl_account_id instead of the generic "bank" default account, and SHALL fall back to the generic "bank" account if no bank_account_id is provided.

**Validates: Requirements 2.5, 2.6, 2.7, 2.8**

Property 3: Fault Condition - Specific Bank Account Used in Payment Reversals

_For any_ payment cancellation where the original payment had a bank_account_id, the fixed system SHALL create a reversing entry using the specific bank account's gl_account_id, and SHALL use the generic "bank" account if the original payment had no bank_account_id.

**Validates: Requirements 2.9, 2.10**

Property 4: Fault Condition - Outstanding Amount Updated on Payment Allocation

_For any_ payment allocation or cancellation, the fixed system SHALL automatically recalculate the invoice's outstanding_amount as (grand_total - total_allocated_payments) and update the invoice record.

**Validates: Requirements 2.12, 2.13**

Property 5: Preservation - Non-Bank_Transfer Payment Behavior

_For any_ payment with payment_mode "Cash" or "Check", the fixed system SHALL produce exactly the same journal entries as the original system, using the appropriate default accounts ("cash" or "checks_received").

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

Property 6: Preservation - Draft Invoice Operations

_For any_ invoice in "draft" status that is created, updated, or deleted, the fixed system SHALL produce exactly the same behavior as the original system, without creating journal entries.

**Validates: Requirements 3.6, 3.7, 3.8**

Property 7: Preservation - Invoice Status Transitions

_For any_ invoice status change from "submitted" to "paid" or "partial" due to payment allocations, the fixed system SHALL continue to update the status automatically via InvoiceStatusService, and SHALL not create duplicate journal entries when an already-submitted invoice is updated.

**Validates: Requirements 3.9, 3.10**

Property 8: Preservation - Default Account Validation and Journal Entry Structure

_For any_ invoice confirmation or payment confirmation, the fixed system SHALL continue to validate that required default accounts are configured, validate that debits equal credits, convert foreign currency amounts to base currency, and maintain proper journal entry structure with all required fields.

**Validates: Requirements 3.11, 3.12, 3.13, 3.14, 3.15**


## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct, the following changes are required:

### Change 1: Database Schema - Add bank_account_id to PaymentEntry

**File**: `horizon-sync-erp-be/core-service/app/models/payment_entry.py`

**Model**: `PaymentEntry`

**Specific Changes**:
1. **Add bank_account_id Field**: Add nullable foreign key field to link to bank_accounts table
   ```python
   bank_account_id = Column(
       UUID(as_uuid=True),
       ForeignKey("bank_accounts.id", ondelete="SET NULL"),
       nullable=True,
       index=True
   )
   ```

2. **Add Relationship**: Add relationship to BankAccount model
   ```python
   bank_account = relationship("BankAccount", foreign_keys=[bank_account_id])
   ```

3. **Update __repr__**: Include bank_account_id in string representation for debugging

**Migration Required**: Yes - Alembic migration to add bank_account_id column to payment_entries table

### Change 2: Service Layer - Create InvoiceJournalPostingService

**File**: `horizon-sync-erp-be/core-service/app/services/invoice_journal_posting_service.py` (NEW FILE)

**Purpose**: Separate service for creating invoice confirmation journal entries

**Specific Changes**:
1. **Create New Service Class**: InvoiceJournalPostingService with methods:
   - `post_invoice_journal_entry(invoice, organization_id, user_id)` - Creates journal entry for invoice confirmation
   - `_validate_invoice_default_accounts(invoice_type, organization_id)` - Validates required default accounts are configured
   - `_convert_to_base_currency(amount, from_currency, organization_id)` - Converts invoice amount to base currency

2. **Sales Invoice Journal Entry Logic**:
   - Debit: Accounts Receivable (from DefaultAccountService, transaction_type="accounts_receivable")
   - Credit: Sales Revenue (from DefaultAccountService, transaction_type="sales_revenue")
   - Amount: invoice.grand_total converted to base currency
   - Reference: reference_type="Invoice", reference_id=invoice.id

3. **Purchase Invoice Journal Entry Logic**:
   - Debit: Purchase Expense (from DefaultAccountService, transaction_type="purchase_expense")
   - Credit: Accounts Payable (from DefaultAccountService, transaction_type="accounts_payable")
   - Amount: invoice.grand_total converted to base currency
   - Reference: reference_type="Invoice", reference_id=invoice.id

4. **Validation**: Validate debits equal credits, validate default accounts configured before creating entries

5. **Error Handling**: Raise ValidationError if default accounts not configured or if validation fails

### Change 3: Service Layer - Update InvoiceService

**File**: `horizon-sync-erp-be/core-service/app/services/invoice_service.py`

**Method**: Add new method `confirm_invoice(invoice_id, organization_id, user_id)`

**Specific Changes**:
1. **Create confirm_invoice Method**: New method to handle invoice confirmation workflow
   - Validate invoice exists and is in "draft" status
   - Update status to "submitted"
   - Set submitted_at timestamp to current datetime
   - Set outstanding_amount to grand_total
   - Call InvoiceJournalPostingService.post_invoice_journal_entry()
   - Commit transaction
   - Return updated invoice

2. **Transaction Management**: Wrap all operations in a database transaction to ensure atomicity (if journal entry creation fails, invoice status should not change)

3. **Error Handling**: If journal entry creation fails, rollback invoice status change and re-raise exception

### Change 4: Service Layer - Update JournalPostingService

**File**: `horizon-sync-erp-be/core-service/app/services/journal_posting_service.py`

**Method**: `_get_payment_account_by_mode()` and `post_payment_journal_entry()`

**Specific Changes**:
1. **Modify _get_payment_account_by_mode Signature**: Add optional bank_account_id parameter
   ```python
   def _get_payment_account_by_mode(
       self,
       payment_mode: str,
       organization_id: UUID,
       bank_account_id: UUID | None = None,
   ) -> UUID:
   ```

2. **Add Bank Account Logic**: If payment_mode is "Bank_Transfer" and bank_account_id is provided:
   - Query BankAccount model to get bank_account record
   - Validate bank_account exists and belongs to organization
   - Return bank_account.gl_account_id
   - If bank_account_id is None, fall back to generic "bank" default account

3. **Update post_payment_journal_entry**: Pass payment_entry.bank_account_id to _get_payment_account_by_mode()

4. **Update reverse_payment_journal_entry**: No changes needed - it already retrieves and reverses the original journal entry, so it will automatically use the correct account

5. **Validation**: Add validation to ensure bank_account belongs to the same organization as the payment

### Change 5: Service Layer - Update InvoiceStatusService

**File**: `horizon-sync-erp-be/core-service/app/services/invoice_status_service.py`

**Method**: `update_invoice_status()`

**Specific Changes**:
1. **Update outstanding_amount Field**: After calculating outstanding_balance, assign it to invoice.outstanding_amount
   ```python
   invoice.status = new_status
   invoice.outstanding_amount = outstanding_balance  # ADD THIS LINE
   ```

2. **No Other Changes**: The method already calculates outstanding_balance correctly, it just wasn't being saved to the database

### Change 6: API Layer - Create Invoice Confirmation Endpoint

**File**: `horizon-sync-erp-be/core-service/app/api/v1/endpoints/invoices.py`

**Endpoint**: `POST /api/v1/invoices/{invoice_id}/confirm`

**Specific Changes**:
1. **Create New Endpoint**: POST endpoint to confirm/submit an invoice
   - Path parameter: invoice_id (UUID)
   - Call InvoiceService.confirm_invoice(invoice_id, organization_id, user_id)
   - Return updated invoice with 200 status
   - Handle ValidationError with 400 status (e.g., default accounts not configured)
   - Handle ResourceNotFoundException with 404 status

2. **Authorization**: Require appropriate permissions to confirm invoices

3. **Response Schema**: Return full invoice details including submitted_at timestamp and outstanding_amount

### Change 7: API Layer - Update Payment Entry Endpoints

**File**: `horizon-sync-erp-be/core-service/app/api/v1/endpoints/payment_entries.py`

**Endpoints**: Payment creation and update endpoints

**Specific Changes**:
1. **Update Request Schema**: Add optional bank_account_id field to payment creation/update request schemas
   ```python
   bank_account_id: Optional[UUID] = None
   ```

2. **Validation**: If bank_account_id is provided:
   - Validate that bank_account exists
   - Validate that bank_account belongs to the same organization
   - Validate that bank_account is active (is_active=True)

3. **Pass to Service**: Include bank_account_id in data passed to PaymentEntryService

4. **Response Schema**: Include bank_account_id in payment response schema

### Change 8: Schema Layer - Update Payment Entry Schemas

**File**: `horizon-sync-erp-be/core-service/app/schemas/payment_entry.py`

**Schemas**: PaymentEntryCreate, PaymentEntryUpdate, PaymentEntryResponse

**Specific Changes**:
1. **Add bank_account_id to PaymentEntryCreate**: Optional UUID field
2. **Add bank_account_id to PaymentEntryUpdate**: Optional UUID field
3. **Add bank_account_id to PaymentEntryResponse**: Optional UUID field
4. **Add bank_account to PaymentEntryResponse**: Optional nested BankAccount object with basic details (bank_name, masked account number, gl_account_id)


## Data Flow Diagrams

### Flow 1: Invoice Confirmation (Bug 1 Fix)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Invoice Confirmation Flow (Stage A)                                     │
└─────────────────────────────────────────────────────────────────────────┘

User Action: POST /api/v1/invoices/{invoice_id}/confirm
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API Endpoint: invoices.py                                               │
│ - Extract invoice_id, organization_id, user_id                          │
│ - Call InvoiceService.confirm_invoice()                                 │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ InvoiceService.confirm_invoice()                                        │
│ 1. Get invoice by ID (validate exists, status="draft")                  │
│ 2. Update invoice:                                                       │
│    - status = "submitted"                                                │
│    - submitted_at = current_datetime                                     │
│    - outstanding_amount = grand_total                                    │
│ 3. Call InvoiceJournalPostingService.post_invoice_journal_entry()       │
│ 4. Commit transaction                                                    │
│ 5. Return updated invoice                                                │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ InvoiceJournalPostingService.post_invoice_journal_entry()               │
│ 1. Validate default accounts configured:                                │
│    - Sales: accounts_receivable, sales_revenue                          │
│    - Purchase: purchase_expense, accounts_payable                       │
│ 2. Convert invoice.grand_total to base currency                         │
│ 3. Build journal entry data:                                            │
│    Sales Invoice:                                                        │
│      - Debit: Accounts Receivable                                       │
│      - Credit: Sales Revenue                                            │
│    Purchase Invoice:                                                     │
│      - Debit: Purchase Expense                                          │
│      - Credit: Accounts Payable                                         │
│ 4. Validate debits = credits                                            │
│ 5. Call JournalEntryService.create()                                    │
│ 6. Return journal entry                                                  │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ JournalEntryService.create()                                            │
│ - Create JournalEntry record                                            │
│ - Create JournalEntryLine records (2 lines: debit and credit)           │
│ - Set status="posted", voucher_type="Invoice Confirmation"              │
│ - Set reference_type="Invoice", reference_id=invoice.id                 │
│ - Return journal entry                                                   │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
Database: invoice.status="submitted", invoice.submitted_at=timestamp,
          invoice.outstanding_amount=grand_total, journal_entry created
```

### Flow 2: Payment Confirmation with Bank Account (Bug 2 Fix)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Payment Confirmation Flow (Stage B) - Bank Transfer                     │
└─────────────────────────────────────────────────────────────────────────┘

User Action: POST /api/v1/payment-entries (with bank_account_id)
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API Endpoint: payment_entries.py                                        │
│ - Extract payment data including bank_account_id                        │
│ - Validate bank_account exists and is active                            │
│ - Call PaymentEntryService.create()                                     │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PaymentEntryService.create()                                            │
│ - Create PaymentEntry record with bank_account_id                       │
│ - Set status="confirmed"                                                 │
│ - Call JournalPostingService.post_payment_journal_entry()               │
│ - Return payment entry                                                   │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ JournalPostingService.post_payment_journal_entry()                      │
│ 1. Validate default accounts configured                                 │
│ 2. Convert payment amount to base currency                              │
│ 3. Call _get_payment_account_by_mode(payment_mode, org_id,              │
│                                       bank_account_id)                   │
│ 4. Build journal entry data:                                            │
│    Customer Payment:                                                     │
│      - Debit: Specific Bank Account GL Account (or generic "bank")      │
│      - Credit: Accounts Receivable                                      │
│    Supplier Payment:                                                     │
│      - Debit: Accounts Payable                                          │
│      - Credit: Specific Bank Account GL Account (or generic "bank")     │
│ 5. Call JournalEntryService.create()                                    │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ JournalPostingService._get_payment_account_by_mode()                    │
│ IF payment_mode == "Bank_Transfer" AND bank_account_id IS NOT NULL:     │
│   - Query BankAccount by bank_account_id                                │
│   - Validate bank_account.organization_id == organization_id            │
│   - Return bank_account.gl_account_id                                   │
│ ELSE IF payment_mode == "Bank_Transfer":                                │
│   - Get default account for transaction_type="bank"                     │
│   - Return default_account.account_id                                   │
│ ELSE (Cash, Check):                                                      │
│   - Get default account for transaction_type="cash" or "checks_received"│
│   - Return default_account.account_id                                   │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
Database: payment_entry.bank_account_id=UUID, journal_entry uses specific
          bank account's gl_account_id
```

### Flow 3: Payment Allocation and Outstanding Amount Update (Bug 3 Fix)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Payment Allocation Flow - Outstanding Amount Update                     │
└─────────────────────────────────────────────────────────────────────────┘

User Action: POST /api/v1/payment-references (allocate payment to invoice)
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ API Endpoint: payment_references.py                                     │
│ - Extract payment_entry_id, invoice_id, allocated_amount                │
│ - Call PaymentReferenceService.create()                                 │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PaymentReferenceService.create()                                        │
│ 1. Validate payment_entry and invoice exist                             │
│ 2. Validate allocated_amount <= payment_entry.unallocated_amount        │
│ 3. Create PaymentReference record                                       │
│ 4. Call InvoiceStatusService.update_invoice_status(invoice_id)          │
│ 5. Return payment reference                                             │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ InvoiceStatusService.update_invoice_status()                            │
│ 1. Get invoice by ID                                                     │
│ 2. Calculate total_allocated = sum of all payment_references            │
│ 3. Calculate outstanding_balance = grand_total - total_allocated        │
│ 4. Determine new status:                                                 │
│    - "draft" if total_allocated == 0                                     │
│    - "partial" if 0 < total_allocated < grand_total                     │
│    - "paid" if total_allocated >= grand_total                           │
│ 5. Update invoice:                                                       │
│    - invoice.status = new_status                                         │
│    - invoice.outstanding_amount = outstanding_balance  ← FIX HERE       │
│ 6. Commit and return invoice                                             │
└─────────────────────────────────────────────────────────────────────────┘
     │
     ▼
Database: invoice.outstanding_amount updated to reflect current allocations
```


## Error Handling and Validation Logic

### Invoice Confirmation Validation

**Pre-Confirmation Checks:**
1. **Invoice Exists**: Validate invoice_id exists in database and belongs to organization
   - Error: 404 ResourceNotFoundException - "Invoice {invoice_id} not found"

2. **Invoice Status**: Validate invoice.status == "draft"
   - Error: 400 ValidationError - "Invoice must be in draft status to confirm. Current status: {status}"

3. **Invoice Type**: Validate invoice.invoice_type in ["Sales", "Purchase"]
   - Error: 400 ValidationError - "Invalid invoice type: {invoice_type}"

4. **Default Accounts Configured**: Validate required default accounts exist
   - Sales Invoice: accounts_receivable, sales_revenue
   - Purchase Invoice: purchase_expense, accounts_payable
   - Error: 400 ValidationError - "Required default accounts not configured: {missing_accounts}. Please configure default accounts before confirming invoices."

5. **Grand Total Valid**: Validate invoice.grand_total > 0
   - Error: 400 ValidationError - "Invoice grand_total must be greater than zero"

6. **Currency Valid**: Validate invoice.currency is a valid currency code
   - Error: 400 ValidationError - "Invalid currency code: {currency}"

**Journal Entry Creation Validation:**
1. **Debits Equal Credits**: Validate total_debit == total_credit
   - Error: 500 ValidationError - "Journal entry debits ({total_debit}) do not equal credits ({total_credit})"

2. **Currency Conversion**: If invoice currency != base currency, validate conversion succeeds
   - Error: 400 ValidationError - "Failed to convert {amount} {from_currency} to base currency {to_currency}: {error}"

**Transaction Rollback:**
- If journal entry creation fails, rollback invoice status change
- If any validation fails, rollback entire transaction
- Ensure atomicity: invoice status and journal entry are created together or not at all

### Payment Entry Validation (Bank Account)

**Bank Account Validation:**
1. **Bank Account Exists**: If bank_account_id provided, validate it exists
   - Error: 404 ResourceNotFoundException - "Bank account {bank_account_id} not found"

2. **Bank Account Organization**: Validate bank_account.organization_id == payment.organization_id
   - Error: 403 ValidationError - "Bank account does not belong to this organization"

3. **Bank Account Active**: Validate bank_account.is_active == True
   - Error: 400 ValidationError - "Bank account {bank_name} ({masked_account}) is not active"

4. **Payment Mode Consistency**: If bank_account_id provided, validate payment_mode == "Bank_Transfer"
   - Error: 400 ValidationError - "bank_account_id can only be provided for Bank_Transfer payment mode"

5. **GL Account Exists**: Validate bank_account.gl_account_id exists in accounts table
   - Error: 500 ValidationError - "Bank account GL account {gl_account_id} not found in chart of accounts"

**Backward Compatibility:**
- If payment_mode == "Bank_Transfer" and bank_account_id is None, fall back to generic "bank" default account
- No error thrown for missing bank_account_id (optional field)
- Existing payments without bank_account_id continue to work

### Outstanding Amount Update Validation

**Payment Allocation Validation:**
1. **Invoice Exists**: Validate invoice_id exists
   - Error: 404 ResourceNotFoundException - "Invoice {invoice_id} not found"

2. **Payment Entry Exists**: Validate payment_entry_id exists
   - Error: 404 ResourceNotFoundException - "Payment entry {payment_entry_id} not found"

3. **Allocated Amount Valid**: Validate allocated_amount <= payment_entry.unallocated_amount
   - Error: 400 ValidationError - "Allocated amount {allocated_amount} exceeds unallocated payment amount {unallocated_amount}"

4. **Outstanding Amount Calculation**: Validate outstanding_amount = grand_total - total_allocated >= 0
   - Note: Overpayment is allowed (outstanding_amount can be negative), but should be flagged in UI

**Automatic Recalculation:**
- InvoiceStatusService.update_invoice_status() is called automatically after:
  - Payment allocation created (PaymentReference created)
  - Payment allocation cancelled (PaymentReference deleted)
  - Payment cancelled (all PaymentReferences for that payment deleted)
- No manual intervention required

### Error Response Format

All validation errors return consistent format:
```json
{
  "error": "ValidationError",
  "message": "Detailed error message",
  "details": {
    "field": "field_name",
    "value": "invalid_value",
    "constraint": "constraint_violated"
  }
}
```

### Logging and Audit Trail

**Journal Entry Audit:**
- All journal entries include reference_type and reference_id linking back to source document
- Journal entries are never deleted, only reversed
- Reversing entries include remarks explaining reason for reversal

**Invoice Confirmation Audit:**
- submitted_at timestamp records when invoice was confirmed
- created_by and updated_by fields track user who confirmed invoice
- Journal entry remarks include invoice_no for traceability

**Payment Audit:**
- PaymentAuditLog records all payment status changes
- Journal entry remarks include payment reference_no for traceability
- Bank account changes tracked in BankAccountHistory table


## Migration Strategy for Existing Data

### Challenge: Existing Invoices Without Journal Entries

**Problem**: Invoices that were confirmed before this fix was deployed do not have corresponding journal entries. This creates:
- Incomplete financial history
- Inaccurate balance sheet (missing AR/AP)
- Inaccurate income statement (missing Revenue/Expense)
- Broken audit trail

**Solution Options:**

#### Option 1: Backfill Journal Entries (Recommended)

Create a data migration script that:
1. Identifies all invoices with status="submitted" or "paid" or "partial" that do not have corresponding journal entries
2. For each invoice, creates the appropriate journal entry with:
   - posting_date = invoice.submitted_at (or invoice.posting_date if submitted_at is null)
   - Same logic as InvoiceJournalPostingService.post_invoice_journal_entry()
   - remarks = "Backfilled journal entry for historical invoice"
3. Validates that all backfilled entries have debits = credits
4. Runs in a transaction with rollback on any error

**Pros:**
- Complete financial history
- Accurate financial reports from day one
- Proper audit trail

**Cons:**
- May create large number of journal entries
- Requires careful testing to avoid data corruption
- May affect historical financial reports (if they were generated before backfill)

**Implementation:**
```python
# Migration script: backfill_invoice_journal_entries.py
def backfill_invoice_journal_entries():
    # Get all submitted invoices without journal entries
    invoices = db.query(Invoice).filter(
        Invoice.status.in_(["submitted", "paid", "partial"]),
        ~exists(
            select(JournalEntry).where(
                JournalEntry.reference_type == "Invoice",
                JournalEntry.reference_id == Invoice.id
            )
        )
    ).all()
    
    for invoice in invoices:
        # Create journal entry using same logic as InvoiceJournalPostingService
        # Use invoice.submitted_at or invoice.posting_date as posting_date
        # Add remark: "Backfilled journal entry for historical invoice"
        pass
```

#### Option 2: Mark Historical Invoices (Alternative)

Add a flag to indicate invoices that were confirmed before the fix:
1. Add `legacy_invoice` boolean field to Invoice model
2. Set `legacy_invoice=True` for all existing submitted invoices without journal entries
3. Display warning in UI for legacy invoices
4. Optionally allow manual journal entry creation for legacy invoices

**Pros:**
- No risk of data corruption
- Simpler implementation
- Users can decide which invoices to backfill

**Cons:**
- Incomplete financial history
- Inaccurate financial reports (unless manually corrected)
- Requires user intervention

### Challenge: Existing Payments Without bank_account_id

**Problem**: Payments that were created before this fix do not have bank_account_id populated. This means:
- Cannot determine which bank account was used for historical payments
- Journal entries use generic "bank" account
- Bank reconciliation is difficult for historical data

**Solution Options:**

#### Option 1: Leave Historical Payments As-Is (Recommended)

- Do not backfill bank_account_id for existing payments
- Historical payments continue to use generic "bank" account in journal entries
- New payments from this point forward use specific bank accounts
- Document cutover date in release notes

**Pros:**
- No risk of incorrect data
- Simple implementation
- Clear cutover point

**Cons:**
- Incomplete bank account tracking for historical data
- Bank reconciliation requires manual work for historical periods

#### Option 2: Manual Backfill with User Input

Create an admin tool that:
1. Lists all payments with payment_mode="Bank_Transfer" and bank_account_id=NULL
2. Allows admin to manually select which bank account was used
3. Updates payment_entry.bank_account_id
4. Does NOT update journal entries (they remain with generic "bank" account)

**Pros:**
- More accurate historical data
- Helps with bank reconciliation

**Cons:**
- Requires manual work
- Risk of incorrect data entry
- Journal entries still use generic "bank" account (cannot be changed without reversing and recreating)

### Challenge: Existing Invoices with Incorrect outstanding_amount

**Problem**: Invoices that have payments allocated may have incorrect outstanding_amount values.

**Solution: Recalculate All Outstanding Amounts (Recommended)**

Create a data migration script that:
1. Iterates through all invoices with status="submitted", "paid", or "partial"
2. For each invoice, calls InvoiceStatusService.update_invoice_status()
3. This recalculates outstanding_amount and status based on current payment allocations
4. Runs in a transaction with rollback on any error

**Implementation:**
```python
# Migration script: recalculate_outstanding_amounts.py
def recalculate_outstanding_amounts():
    invoices = db.query(Invoice).filter(
        Invoice.status.in_(["submitted", "paid", "partial"])
    ).all()
    
    for invoice in invoices:
        InvoiceStatusService(db).update_invoice_status(
            invoice_id=invoice.id,
            organization_id=invoice.organization_id
        )
```

**Pros:**
- Corrects all outstanding amounts
- Simple and safe (uses existing service logic)
- No risk of data corruption

**Cons:**
- May change invoice status if it was incorrect before
- May affect reports if they were based on incorrect data

### Migration Execution Plan

**Phase 1: Schema Changes**
1. Run Alembic migration to add bank_account_id column to payment_entries table
2. Verify column added successfully in all environments

**Phase 2: Code Deployment**
1. Deploy new code with all service and API changes
2. Verify new invoice confirmations create journal entries
3. Verify new payments with bank_account_id use specific GL accounts

**Phase 3: Data Backfill (Optional)**
1. Run backfill_invoice_journal_entries.py script in staging environment
2. Verify journal entries created correctly
3. Run in production during maintenance window
4. Run recalculate_outstanding_amounts.py script
5. Verify outstanding amounts corrected

**Phase 4: Validation**
1. Generate financial reports and compare with pre-migration reports
2. Verify AR/AP balances are correct
3. Verify Revenue/Expense totals are correct
4. Document any discrepancies and explain to users

**Rollback Plan:**
- If issues discovered, code can be rolled back (new invoices will not create journal entries)
- Database schema change (bank_account_id column) can remain (nullable field, no impact)
- Backfilled journal entries can be deleted by reference_type="Invoice" and remarks containing "Backfilled"


## Testing Strategy

### Validation Approach

The testing strategy follows a three-phase approach:
1. **Exploratory Testing**: Surface counterexamples that demonstrate the bugs on unfixed code
2. **Fix Verification**: Verify the fix works correctly for all bug conditions
3. **Preservation Testing**: Verify existing behavior is unchanged for non-buggy inputs

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bugs BEFORE implementing the fix. Confirm or refute the root cause analysis.

#### Bug 1: Missing Invoice Journal Entries

**Test Plan**: Create and confirm invoices on UNFIXED code, then query journal_entries table to verify no entries exist.

**Test Cases**:
1. **Sales Invoice Confirmation Test**: Create sales invoice with grand_total $1,000, confirm it, verify no journal entry created (will fail on unfixed code)
2. **Purchase Invoice Confirmation Test**: Create purchase invoice with grand_total $500, confirm it, verify no journal entry created (will fail on unfixed code)
3. **Foreign Currency Invoice Test**: Create invoice in EUR, confirm it, verify no journal entry with currency conversion (will fail on unfixed code)
4. **Missing Default Accounts Test**: Remove default accounts, attempt to confirm invoice, verify appropriate error (may pass or fail depending on current validation)

**Expected Counterexamples**:
- No journal entries exist for confirmed invoices
- submitted_at timestamp is not set
- outstanding_amount is not initialized to grand_total
- Possible cause: No integration between InvoiceService and JournalPostingService

#### Bug 2: Generic Bank Account Usage

**Test Plan**: Create payments with payment_mode="Bank_Transfer" on UNFIXED code, then query journal_entry_lines to verify which account_id is used.

**Test Cases**:
1. **Customer Payment with Bank Account Test**: Create customer payment with bank_account_id (HDFC), verify journal entry uses generic "bank" account instead of HDFC's gl_account_id (will fail on unfixed code)
2. **Supplier Payment with Bank Account Test**: Create supplier payment with bank_account_id (ICICI), verify journal entry uses generic "bank" account instead of ICICI's gl_account_id (will fail on unfixed code)
3. **Payment Without Bank Account Test**: Create payment without bank_account_id, verify journal entry uses generic "bank" account (should pass - this is expected behavior)
4. **Cash Payment Test**: Create payment with payment_mode="Cash", verify journal entry uses "cash" account (should pass - preservation test)

**Expected Counterexamples**:
- Journal entries use generic "bank" account even when bank_account_id is provided
- PaymentEntry model does not have bank_account_id field
- Possible cause: Missing field in model, no logic to use specific bank account

#### Bug 3: Outstanding Amount Not Updated

**Test Plan**: Create invoices and allocate payments on UNFIXED code, then query invoice.outstanding_amount to verify it reflects allocations.

**Test Cases**:
1. **Payment Allocation Test**: Create invoice with grand_total $1,000, allocate payment $300, verify outstanding_amount is $700 (will fail on unfixed code if not updated)
2. **Payment Cancellation Test**: Create invoice with outstanding_amount $700, cancel payment allocation, verify outstanding_amount increases back to $1,000 (will fail on unfixed code)
3. **Multiple Allocations Test**: Create invoice with grand_total $1,000, allocate three payments ($200, $300, $400), verify outstanding_amount is $100 (will fail on unfixed code)
4. **Full Payment Test**: Create invoice with grand_total $1,000, allocate payment $1,000, verify outstanding_amount is $0 and status is "paid" (may pass or fail depending on current logic)

**Expected Counterexamples**:
- outstanding_amount does not change after payment allocation
- outstanding_amount is not recalculated after payment cancellation
- Possible cause: InvoiceStatusService calculates outstanding_balance but doesn't save it to invoice.outstanding_amount

### Fix Checking

**Goal**: Verify that for all inputs where the bug conditions hold, the fixed system produces the expected behavior.

#### Bug 1 Fix Verification

**Pseudocode:**
```
FOR ALL invoice WHERE isBugCondition1(invoice) DO
  result := InvoiceService.confirm_invoice(invoice.id)
  ASSERT journalEntryExists(invoice.id, "Invoice")
  ASSERT invoice.submitted_at IS NOT NULL
  ASSERT invoice.outstanding_amount == invoice.grand_total
  ASSERT invoice.status == "submitted"
  
  IF invoice.invoice_type == "Sales" THEN
    ASSERT journalEntryHasDebit("accounts_receivable", invoice.grand_total)
    ASSERT journalEntryHasCredit("sales_revenue", invoice.grand_total)
  ELSE IF invoice.invoice_type == "Purchase" THEN
    ASSERT journalEntryHasDebit("purchase_expense", invoice.grand_total)
    ASSERT journalEntryHasCredit("accounts_payable", invoice.grand_total)
  END IF
END FOR
```

**Test Cases**:
1. Confirm sales invoice → Verify journal entry with Debit AR, Credit Revenue
2. Confirm purchase invoice → Verify journal entry with Debit Expense, Credit AP
3. Confirm invoice in foreign currency → Verify journal entry uses base currency amount
4. Confirm invoice without default accounts → Verify ValidationError raised
5. Confirm invoice with grand_total = 0 → Verify ValidationError raised

#### Bug 2 Fix Verification

**Pseudocode:**
```
FOR ALL payment WHERE isBugCondition2(payment) DO
  result := PaymentEntryService.create(payment_data_with_bank_account_id)
  ASSERT payment.bank_account_id IS NOT NULL
  ASSERT journalEntryUsesAccount(payment.id, payment.bank_account.gl_account_id)
  ASSERT NOT journalEntryUsesAccount(payment.id, "bank_default_account")
END FOR
```

**Test Cases**:
1. Create customer payment with bank_account_id → Verify journal entry debits specific bank account's gl_account_id
2. Create supplier payment with bank_account_id → Verify journal entry credits specific bank account's gl_account_id
3. Create payment with bank_account_id for inactive bank account → Verify ValidationError raised
4. Create payment with bank_account_id from different organization → Verify ValidationError raised
5. Create payment without bank_account_id → Verify journal entry uses generic "bank" account (backward compatibility)

#### Bug 3 Fix Verification

**Pseudocode:**
```
FOR ALL payment_allocation WHERE isBugCondition3(payment_allocation) DO
  result := PaymentReferenceService.create(payment_allocation)
  invoice := InvoiceRepository.get_by_id(payment_allocation.invoice_id)
  total_allocated := sum(payment_references.allocated_amount)
  ASSERT invoice.outstanding_amount == (invoice.grand_total - total_allocated)
END FOR
```

**Test Cases**:
1. Allocate payment to invoice → Verify outstanding_amount decreases
2. Cancel payment allocation → Verify outstanding_amount increases
3. Allocate multiple payments → Verify outstanding_amount reflects sum of all allocations
4. Fully pay invoice → Verify outstanding_amount = 0 and status = "paid"
5. Overpay invoice → Verify outstanding_amount is negative

### Preservation Checking

**Goal**: Verify that for all inputs where the bug conditions do NOT hold, the fixed system produces the same result as the original system.

**Pseudocode:**
```
FOR ALL input WHERE NOT (isBugCondition1(input) OR isBugCondition2(input) OR isBugCondition3(input)) DO
  ASSERT fixed_system(input) == original_system(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

#### Preservation Test Cases

**Draft Invoice Operations:**
1. Create draft invoice → Verify no journal entry created
2. Update draft invoice → Verify no journal entry created
3. Delete draft invoice → Verify no journal entries affected
4. Query draft invoices → Verify same results as before

**Cash and Check Payments:**
1. Create customer payment with payment_mode="Cash" → Verify journal entry debits "cash" account
2. Create customer payment with payment_mode="Check" → Verify journal entry debits "checks_received" account
3. Create supplier payment with payment_mode="Cash" → Verify journal entry credits "cash" account
4. Create supplier payment with payment_mode="Check" → Verify journal entry credits "checks_received" account
5. Cancel Cash/Check payment → Verify reversing entry uses same accounts

**Invoice Status Transitions:**
1. Invoice status changes from "submitted" to "partial" after payment allocation → Verify automatic status update
2. Invoice status changes from "partial" to "paid" after full payment → Verify automatic status update
3. Update already-submitted invoice (change remarks) → Verify no duplicate journal entries created

**Default Account Validation:**
1. Attempt to confirm invoice without default accounts configured → Verify ValidationError raised
2. Attempt to create payment without default accounts configured → Verify ValidationError raised

**Currency Conversion:**
1. Create invoice in foreign currency → Verify journal entry uses base currency amount
2. Create payment in foreign currency → Verify journal entry uses base currency amount

**Journal Entry Structure:**
1. Verify all journal entries have reference_type and reference_id
2. Verify all journal entries have against_account_id in lines
3. Verify all journal entries have status="posted"
4. Verify all journal entries have debits = credits

### Unit Tests

**InvoiceJournalPostingService Tests:**
- Test post_invoice_journal_entry() for sales invoices
- Test post_invoice_journal_entry() for purchase invoices
- Test _validate_invoice_default_accounts() with missing accounts
- Test _convert_to_base_currency() with foreign currency
- Test error handling for invalid invoice types

**InvoiceService Tests:**
- Test confirm_invoice() success path
- Test confirm_invoice() with draft invoice
- Test confirm_invoice() with already-submitted invoice (should fail)
- Test confirm_invoice() with missing default accounts (should fail)
- Test confirm_invoice() transaction rollback on journal entry failure

**JournalPostingService Tests:**
- Test _get_payment_account_by_mode() with bank_account_id
- Test _get_payment_account_by_mode() without bank_account_id (fallback)
- Test _get_payment_account_by_mode() with inactive bank account (should fail)
- Test _get_payment_account_by_mode() with bank account from different org (should fail)
- Test post_payment_journal_entry() with bank_account_id
- Test reverse_payment_journal_entry() with bank_account_id

**InvoiceStatusService Tests:**
- Test update_invoice_status() updates outstanding_amount
- Test update_invoice_status() with no allocations
- Test update_invoice_status() with partial allocations
- Test update_invoice_status() with full payment
- Test update_invoice_status() with overpayment

### Property-Based Tests

**Invoice Confirmation Properties:**
- For any valid invoice in draft status, confirming it creates exactly one journal entry
- For any confirmed invoice, the journal entry debits equal credits
- For any confirmed invoice, the outstanding_amount equals grand_total
- For any confirmed invoice in foreign currency, the journal entry amount is in base currency

**Payment with Bank Account Properties:**
- For any payment with bank_account_id, the journal entry uses the bank account's gl_account_id
- For any payment without bank_account_id, the journal entry uses the generic "bank" account
- For any payment with payment_mode != "Bank_Transfer", the bank_account_id is ignored

**Outstanding Amount Properties:**
- For any invoice, outstanding_amount = grand_total - sum(allocated_payments)
- For any payment allocation, invoice.outstanding_amount decreases by allocated_amount
- For any payment cancellation, invoice.outstanding_amount increases by allocated_amount

**Preservation Properties:**
- For any draft invoice operation, no journal entries are created
- For any Cash/Check payment, the journal entry uses the appropriate default account
- For any invoice status transition, the status is updated correctly based on allocations

### Integration Tests

**End-to-End Invoice Flow:**
1. Create draft sales invoice
2. Confirm invoice → Verify journal entry created (Debit AR, Credit Revenue)
3. Create customer payment with bank_account_id → Verify journal entry created (Debit Bank GL Account, Credit AR)
4. Allocate payment to invoice → Verify outstanding_amount updated, status changed to "paid"
5. Cancel payment → Verify reversing entry created, outstanding_amount restored, status changed back to "submitted"

**End-to-End Purchase Flow:**
1. Create draft purchase invoice
2. Confirm invoice → Verify journal entry created (Debit Expense, Credit AP)
3. Create supplier payment with bank_account_id → Verify journal entry created (Debit AP, Credit Bank GL Account)
4. Allocate payment to invoice → Verify outstanding_amount updated, status changed to "paid"

**Multi-Currency Flow:**
1. Create sales invoice in EUR with grand_total €800
2. Confirm invoice → Verify journal entry uses base currency (USD) amount
3. Create payment in EUR → Verify journal entry uses base currency amount
4. Allocate payment → Verify outstanding_amount calculated correctly

**Error Handling Flow:**
1. Attempt to confirm invoice without default accounts → Verify ValidationError with helpful message
2. Attempt to create payment with inactive bank account → Verify ValidationError
3. Attempt to allocate payment exceeding unallocated amount → Verify ValidationError
4. Simulate journal entry creation failure → Verify invoice status not changed (transaction rollback)

