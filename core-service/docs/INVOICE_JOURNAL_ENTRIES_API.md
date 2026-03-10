# Invoice Journal Entries API Documentation

## Overview

This document describes the API changes related to the invoice journal entries fix, which addresses three critical bugs in the AR/AP accounting workflow:

1. **Invoice Confirmation**: Invoices now create journal entries when confirmed/submitted
2. **Bank Account Tracking**: Payments can now be linked to specific bank accounts
3. **Outstanding Amount Updates**: Invoice outstanding amounts update automatically with payment allocations

## Invoice Confirmation Endpoint

### POST /api/v1/invoices/{invoice_id}/confirm

Confirms/submits an invoice, changing its status from "draft" to "submitted" and creating the appropriate journal entries for accounts receivable/payable and revenue/expense recognition.

#### Request

**Path Parameters:**
- `invoice_id` (UUID, required): The ID of the invoice to confirm

**Headers:**
- `Authorization: Bearer <token>` (required): JWT authentication token

**Permissions Required:**
- `invoice.update`

#### Response

**Success Response (200 OK):**

Returns the updated invoice with the following key changes:
- `status`: Changed to "submitted"
- `submitted_at`: Timestamp when the invoice was confirmed
- `outstanding_amount`: Set to the invoice's `grand_total`

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "invoice_no": "INV-2024-001",
  "invoice_type": "Sales",
  "status": "submitted",
  "party_id": "660e8400-e29b-41d4-a716-446655440000",
  "party_name": "Acme Corporation",
  "posting_date": "2024-01-15",
  "due_date": "2024-02-15",
  "currency": "USD",
  "grand_total": 1000.00,
  "outstanding_amount": 1000.00,
  "submitted_at": "2024-01-15T10:30:00Z",
  "items": [...],
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

#### Error Responses

**400 Bad Request - Invoice Not in Draft Status:**
```json
{
  "detail": "Invoice must be in draft status to confirm. Current status: submitted"
}
```

**400 Bad Request - Missing Default Accounts:**
```json
{
  "detail": "Required default accounts not configured: accounts_receivable, sales_revenue. Please configure default accounts before confirming invoices."
}
```

**400 Bad Request - Invalid Grand Total:**
```json
{
  "detail": "Invoice grand_total must be greater than zero"
}
```

**404 Not Found - Invoice Does Not Exist:**
```json
{
  "detail": "Invoice 550e8400-e29b-41d4-a716-446655440000 not found"
}
```

**403 Forbidden - Insufficient Permissions:**
```json
{
  "detail": "User does not have permission to update invoices"
}
```

#### Journal Entry Creation

When an invoice is confirmed, the system automatically creates a journal entry:

**For Sales Invoices:**
- **Debit**: Accounts Receivable (default account for "accounts_receivable")
- **Credit**: Sales Revenue (default account for "sales_revenue")
- **Amount**: Invoice `grand_total` converted to base currency
- **Reference**: Links to the invoice via `reference_type="Invoice"` and `reference_id=invoice.id`

**For Purchase Invoices:**
- **Debit**: Purchase Expense (default account for "purchase_expense")
- **Credit**: Accounts Payable (default account for "accounts_payable")
- **Amount**: Invoice `grand_total` converted to base currency
- **Reference**: Links to the invoice via `reference_type="Invoice"` and `reference_id=invoice.id`

#### Validation Rules

1. **Invoice Status**: Invoice must be in "draft" status
2. **Invoice Type**: Must be either "Sales" or "Purchase"
3. **Grand Total**: Must be greater than zero
4. **Default Accounts**: Required default accounts must be configured:
   - Sales invoices: `accounts_receivable`, `sales_revenue`
   - Purchase invoices: `purchase_expense`, `accounts_payable`
5. **Currency**: If invoice is in foreign currency, conversion to base currency must succeed
6. **Organization**: Invoice must belong to the user's organization

#### Transaction Behavior

The invoice confirmation operation is atomic:
- If journal entry creation fails, the invoice status change is rolled back
- Both the invoice update and journal entry creation succeed together or fail together
- This ensures data consistency and prevents orphaned records

#### Example Usage

```bash
# Confirm a sales invoice
curl -X POST "https://api.example.com/api/v1/invoices/550e8400-e29b-41d4-a716-446655440000/confirm" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json"
```

---

## Payment Entry Bank Account Parameter

### Overview

Payment entries now support linking to specific bank accounts when using the "Bank_Transfer" payment mode. This enables accurate tracking of which bank account received or paid money, improving bank reconciliation and financial reporting.

### Affected Endpoints

#### POST /api/v1/payment-entries

Creates a new payment entry with optional bank account linkage.

**Request Body Changes:**

Added optional `bank_account_id` field:

```json
{
  "payment_type": "Customer_Payment",
  "party_id": "660e8400-e29b-41d4-a716-446655440000",
  "amount": 1000.00,
  "currency_code": "USD",
  "payment_date": "2024-01-15",
  "payment_mode": "Bank_Transfer",
  "reference_no": "TXN123456789",
  "bank_account_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

**Field Details:**

- `bank_account_id` (UUID, optional): The ID of the bank account used for the payment
  - **Only applicable** when `payment_mode` is "Bank_Transfer"
  - **Must be omitted** for "Cash" or "Check" payment modes
  - If provided, the bank account must:
    - Exist in the system
    - Belong to the user's organization
    - Be active (`is_active=True`)
    - Have a valid `gl_account_id` configured

**Response Changes:**

The response now includes bank account details when `bank_account_id` is provided:

```json
{
  "id": "880e8400-e29b-41d4-a716-446655440000",
  "payment_type": "Customer_Payment",
  "party_id": "660e8400-e29b-41d4-a716-446655440000",
  "amount": 1000.00,
  "currency_code": "USD",
  "payment_date": "2024-01-15",
  "payment_mode": "Bank_Transfer",
  "reference_no": "TXN123456789",
  "bank_account_id": "770e8400-e29b-41d4-a716-446655440000",
  "bank_account": {
    "id": "770e8400-e29b-41d4-a716-446655440000",
    "bank_name": "HDFC Bank",
    "masked_account_number": "****1234",
    "gl_account_id": "990e8400-e29b-41d4-a716-446655440000"
  },
  "status": "Draft",
  "unallocated_amount": 1000.00,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

#### PUT /api/v1/payment-entries/{payment_id}

Updates an existing payment entry. The `bank_account_id` field can be updated following the same validation rules as creation.

### Journal Entry Behavior

When a payment with `bank_account_id` is confirmed, the journal entry uses the specific bank account's GL account instead of the generic "bank" default account:

**Customer Payment with Bank Account:**
- **Debit**: Specific Bank Account's GL Account (from `bank_account.gl_account_id`)
- **Credit**: Accounts Receivable

**Supplier Payment with Bank Account:**
- **Debit**: Accounts Payable
- **Credit**: Specific Bank Account's GL Account (from `bank_account.gl_account_id`)

**Backward Compatibility:**

If `bank_account_id` is not provided for a "Bank_Transfer" payment, the system falls back to using the generic "bank" default account, maintaining backward compatibility with existing integrations.

### Validation Rules

1. **Payment Mode Consistency**: `bank_account_id` can only be provided when `payment_mode` is "Bank_Transfer"
2. **Bank Account Exists**: The bank account must exist in the database
3. **Organization Match**: The bank account must belong to the same organization as the payment
4. **Active Status**: The bank account must be active (`is_active=True`)
5. **GL Account Configured**: The bank account must have a valid `gl_account_id`

### Error Responses

**400 Bad Request - Invalid Payment Mode:**
```json
{
  "detail": "bank_account_id can only be provided for Bank_Transfer payment mode"
}
```

**404 Not Found - Bank Account Does Not Exist:**
```json
{
  "detail": "Bank account with ID 770e8400-e29b-41d4-a716-446655440000 not found"
}
```

**403 Forbidden - Organization Mismatch:**
```json
{
  "detail": "Bank account does not belong to your organization"
}
```

**400 Bad Request - Inactive Bank Account:**
```json
{
  "detail": "Bank account 'HDFC Bank' is not active"
}
```

### Payment Cancellation

When a payment with a `bank_account_id` is cancelled, the reversing journal entry automatically uses the same specific bank account's GL account, ensuring accurate reversal of the original transaction.

### Example Usage

```bash
# Create a customer payment with bank account
curl -X POST "https://api.example.com/api/v1/payment-entries" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": "Customer_Payment",
    "party_id": "660e8400-e29b-41d4-a716-446655440000",
    "amount": 1000.00,
    "currency_code": "USD",
    "payment_date": "2024-01-15",
    "payment_mode": "Bank_Transfer",
    "reference_no": "TXN123456789",
    "bank_account_id": "770e8400-e29b-41d4-a716-446655440000"
  }'

# Create a payment without bank account (backward compatible)
curl -X POST "https://api.example.com/api/v1/payment-entries" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "payment_type": "Customer_Payment",
    "party_id": "660e8400-e29b-41d4-a716-446655440000",
    "amount": 1000.00,
    "currency_code": "USD",
    "payment_date": "2024-01-15",
    "payment_mode": "Bank_Transfer",
    "reference_no": "TXN123456789"
  }'
```

---

## Outstanding Amount Tracking

### Overview

Invoice `outstanding_amount` now updates automatically when payments are allocated or cancelled. This field reflects the remaining balance on the invoice after accounting for all payment allocations.

### Automatic Updates

The `outstanding_amount` field is automatically recalculated in the following scenarios:

1. **Invoice Confirmation**: Set to `grand_total`
2. **Payment Allocation**: Decreased by the allocated amount
3. **Payment Cancellation**: Increased by the previously allocated amount
4. **Payment Allocation Removal**: Increased by the removed allocation amount

### Calculation Formula

```
outstanding_amount = grand_total - sum(all_allocated_payments)
```

### Invoice Status Updates

The invoice status is automatically updated based on the outstanding amount:

- **"submitted"**: `outstanding_amount == grand_total` (no payments allocated)
- **"partial"**: `0 < outstanding_amount < grand_total` (partially paid)
- **"paid"**: `outstanding_amount <= 0` (fully paid or overpaid)

### Example Workflow

1. **Invoice Created**: `grand_total = $1,000`, `outstanding_amount = $0` (draft status)
2. **Invoice Confirmed**: `outstanding_amount = $1,000`, `status = "submitted"`
3. **Payment Allocated ($300)**: `outstanding_amount = $700`, `status = "partial"`
4. **Payment Allocated ($400)**: `outstanding_amount = $300`, `status = "partial"`
5. **Payment Allocated ($300)**: `outstanding_amount = $0`, `status = "paid"`

### API Response

The `outstanding_amount` field is included in all invoice responses:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "invoice_no": "INV-2024-001",
  "status": "partial",
  "grand_total": 1000.00,
  "outstanding_amount": 700.00,
  ...
}
```

---

## Migration and Backward Compatibility

### Invoice Confirmation

- **New Behavior**: Invoices confirmed after this update will have journal entries created automatically
- **Historical Data**: Existing confirmed invoices without journal entries can be backfilled using the provided migration script (optional)
- **No Breaking Changes**: Existing invoice creation and update endpoints remain unchanged

### Bank Account Tracking

- **New Behavior**: Payments can now include `bank_account_id` for Bank_Transfer mode
- **Backward Compatibility**: Payments without `bank_account_id` continue to work using the generic "bank" default account
- **Historical Data**: Existing payments without `bank_account_id` remain unchanged and continue to use the generic "bank" account
- **No Breaking Changes**: The `bank_account_id` field is optional

### Outstanding Amount

- **New Behavior**: `outstanding_amount` updates automatically with payment allocations
- **Data Correction**: A migration script is available to recalculate `outstanding_amount` for all existing invoices
- **No Breaking Changes**: The field already existed; only the automatic update behavior is new

---

## Testing Recommendations

### Invoice Confirmation Testing

1. Confirm a sales invoice and verify journal entry created with correct accounts
2. Confirm a purchase invoice and verify journal entry created with correct accounts
3. Attempt to confirm an invoice without default accounts configured (should fail)
4. Attempt to confirm an already-submitted invoice (should fail)
5. Confirm an invoice in foreign currency and verify base currency conversion

### Bank Account Testing

1. Create a payment with `bank_account_id` and verify journal entry uses specific GL account
2. Create a payment without `bank_account_id` and verify journal entry uses generic "bank" account
3. Attempt to create a Cash payment with `bank_account_id` (should fail)
4. Attempt to create a payment with inactive bank account (should fail)
5. Cancel a payment with `bank_account_id` and verify reversing entry uses same GL account

### Outstanding Amount Testing

1. Confirm an invoice and verify `outstanding_amount` equals `grand_total`
2. Allocate a partial payment and verify `outstanding_amount` decreases
3. Allocate multiple payments and verify `outstanding_amount` reflects total allocations
4. Cancel a payment allocation and verify `outstanding_amount` increases
5. Fully pay an invoice and verify `outstanding_amount` is zero and status is "paid"

---

## Support and Troubleshooting

### Common Issues

**Issue**: Invoice confirmation fails with "Required default accounts not configured"
- **Solution**: Configure the required default accounts in the Chart of Accounts settings:
  - For sales invoices: `accounts_receivable`, `sales_revenue`
  - For purchase invoices: `purchase_expense`, `accounts_payable`

**Issue**: Payment creation fails with "bank_account_id can only be provided for Bank_Transfer payment mode"
- **Solution**: Only include `bank_account_id` when `payment_mode` is "Bank_Transfer". Remove it for Cash or Check payments.

**Issue**: Payment creation fails with "Bank account does not belong to your organization"
- **Solution**: Ensure you're using a bank account ID that belongs to your organization. Use the bank accounts list endpoint to find valid IDs.

**Issue**: Outstanding amount not updating after payment allocation
- **Solution**: This should happen automatically. If it doesn't, contact support. A migration script can recalculate outstanding amounts for all invoices.

### Contact

For additional support or questions about these API changes, please contact the development team or refer to the main API documentation.
