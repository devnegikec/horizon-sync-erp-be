# Payment Flow – High-Level & Low-Level Design + Proposed Fixes

This document summarizes the intended payment flow from the specs, the current implementation, and **proposed fixes** for your confirmation before any code changes.

---

## 1. High-Level Design

### 1.1 Business flow (design intent)

```
┌──────────────────┐     ┌─────────────────────┐     ┌──────────────────┐
│ 1. Create        │     │ 2. Allocate          │     │ 3. Confirm        │
│    Draft Payment  │ ──► │    to Invoices      │ ──► │    Payment        │
│ (amount, party,   │     │ (link payment to     │     │ (journal post,    │
│  date, mode)     │     │  one or more         │     │  receipt number,  │
│                   │     │  invoices)           │     │  immutable)      │
└──────────────────┘     └─────────────────────┘     └──────────────────┘
        │                            │                            │
        │                            │                            │
        ▼                            ▼                            ▼
   Status: Draft               At least one                 Status: Confirmed
   Editable/Deletable           allocation required           Receipt generated
                               before confirm                Journal entry created
```

- **Create**: User creates a payment (Customer or Supplier) in **Draft**. No ledger impact.
- **Allocate**: User allocates (part or all of) the payment amount to one or more invoices (same party). Allocation can be partial (unallocated amount allowed).
- **Confirm**: Allowed only if **at least one allocation** exists. On confirm: receipt number generated, journal entry posted, payment becomes immutable. Cancel is allowed from Confirmed (reversal + remove allocations).

### 1.2 Main UI entry points (design)

| Entry point | Purpose |
|-------------|--------|
| **Payment list** | Filter, search, sort; view payments; row actions: View, Edit (draft), Confirm (draft), Cancel (confirmed). |
| **New Payment** | Open create dialog → PaymentForm → POST create → Draft created. |
| **View Details** | Open detail dialog → full payment + **Allocations** tab (existing allocations + **Add allocation** via InvoiceLinker). |
| **Edit** (draft) | Open create/edit dialog with selected payment → PaymentForm → PUT update. |
| **Confirm** (draft) | Confirm (with at least one allocation) → POST confirm. |
| **Cancel** (confirmed) | Cancel with reason → POST cancel. |

### 1.3 Data flow (design)

- **List**: `GET /api/v1/payments` with filters → `payment_entries` + `pagination`.
- **Single**: `GET /api/v1/payments/:id` → full payment + `payment_references` (allocations).
- **Create**: `POST /api/v1/payments` (body: payment_type, party_id, amount, currency_code, payment_date, payment_mode, reference_no).
- **Update**: `PUT /api/v1/payments/:id` (body: amount, payment_date, payment_mode, reference_no only; no currency_code).
- **Allocate**: `POST /api/v1/payments/:id/allocations` (body: invoice_id, allocated_amount).
- **Remove allocation**: `DELETE /api/v1/payments/allocations/:allocation_id`.
- **Confirm**: `POST /api/v1/payments/:id/confirm`.
- **Cancel**: `POST /api/v1/payments/:id/cancel` (body: cancellation_reason).

---

## 2. Low-Level Design (Relevant Parts)

### 2.1 Frontend components (from design)

- **PaymentManagement**: Container; owns list + filters state; opens Create/Edit dialog and View Details dialog; wires table actions.
- **PaymentTable**: Renders list; columns Receipt #, Date, Party, Amount, Mode, Status, Actions (View / Edit / Confirm / Cancel).
- **PaymentFilters**: Status, Mode, Type, search, “has unallocated”; calls parent `setFilters`.
- **PaymentDialog**: Wraps PaymentForm; create vs edit; onSubmit → createPayment / updatePayment.
- **PaymentForm**: Fields per design; validation (amount, date, reference when Check/Bank_Transfer, etc.); submit payload differs for create (full) vs update (amount, date, mode, reference only); `payment_date` sent as ISO datetime.
- **PaymentDetailDialog**: Tabs: Details, Allocations, Audit. Details: payment info + actions (Edit, Confirm, Cancel, View Receipt). Allocations: **AllocationList** (existing) + **InvoiceLinker** (add allocations for draft). Uses `useInvoiceAllocations(paymentId)` and outstanding-invoices for party.
- **InvoiceLinker**: Shows outstanding invoices for payment’s party; amount inputs; “Save Allocations” → create allocations (one-by-one or bulk per API).
- **AllocationList**: Shows current allocations; remove per allocation (draft only).

### 2.2 Hooks (from design)

- **usePayments(filters)**: Fetches list using **current filters**; returns payments, loading, error, totalCount, refetch. Design suggests React Query; current code uses useState + useEffect.
- **usePaymentActions()**: createPayment, updatePayment, confirmPayment, cancelPayment (and downloadReceipt); toasts; return success/failure.
- **useInvoiceAllocations(paymentId)**: Loads allocations for payment (e.g. from GET payment by id); createAllocation, removeAllocation; refetch after change.

### 2.3 Backend (already implemented per specs)

- Create/Update/Get/List/Confirm/Cancel, allocation create/delete, receipt, list response with `payment_entries` and `pagination`.
- Confirm requires at least one allocation; 409 and error message if not.
- Update schema: only amount, payment_date, payment_mode, reference_no.

---

## 3. Broken Flows and Gaps (Current vs Design)

### 3.1 **Filters not applied to list (critical)**

- **Issue**: `PaymentManagement` keeps `filters` in its own state and passes `filters` into `usePayments(filters)`. `usePayments` **also** keeps internal `filters` state, initialized only once from `initialFilters`. The hook’s `fetchPayments` uses the **hook’s** filters, so when the user changes filters in the UI (parent state updates), the hook still fetches with the **initial** filters. Result: **filter changes have no effect** on the list.
- **Proposed fix**: Make `usePayments` use the **passed-in** `filters` as the single source of truth for fetching. Remove the hook’s internal filter state; have `fetchPayments` depend on the `filters` argument and call `paymentApi.fetchPayments(filters)`. Stop returning `filters` / `setFilters` from the hook (parent already owns them). Signature: `usePayments(filters: Partial<PaymentFilters>)` → `{ payments, loading, error, totalCount, refetch }`.

### 3.2 **Payment list response shape**

- **Current**: API returns `payment_entries` and `pagination`; frontend uses `response.payment_entries` and `response.pagination.total`. This matches the backend and is correct. No change needed unless you want to align naming with design doc (e.g. “payments” vs “payment_entries”) in types only.

### 3.3 **preSelectedInvoice / pendingPaymentId not wired**

- **Issue**: `PaymentManagement` accepts `preSelectedInvoice`, `pendingPaymentId`, `onClearPendingPaymentId`, `onNavigateToInvoice` but they are not used. So “create payment from invoice” or “open a specific payment” from elsewhere in the app does not work.
- **Proposed fix (optional)**: If you need “Record Payment” from an invoice: when `pendingPaymentId` is set, auto-open View Details for that payment; when `preSelectedInvoice` is set and user clicks New Payment, prefill party and optionally open allocation for that invoice after create. If you don’t need this flow yet, we can leave as-is and only fix the filter bug.

### 3.4 **Confirm error message (already improved)**

- Confirm returns 409 when there are no allocations; the frontend now shows the backend message. No further change required unless you want a dedicated “Add allocations first” message in the UI.

### 3.5 **Allocation UI (recently added)**

- PaymentDetailDialog now has Allocations tab with AllocationList + InvoiceLinker for draft; outstanding invoices loaded by party + payment type; create allocation and onAllocationChange refetch. This matches the design. If something still fails (e.g. wrong party or no invoices), we can fix that in a follow-up.

### 3.6 **Design doc vs implementation (non-blocking)**

- Design suggests React Query for usePayments/usePaymentActions; current code uses useState + useEffect and manual async. Functionally the flow works; migrating to React Query would be a separate refactor for caching and consistency.

---

## 4. Proposed Fixes (For Your Confirmation)

I will only apply the following after you confirm.

### Fix 1: **usePayments – use passed-in filters for fetch (fix broken filtering)**

- **File**: `horizon-sync/apps/inventory/src/app/hooks/usePayments.ts`
- **Change**:
  - Make the hook accept **only** `filters: Partial<PaymentFilters>` (no internal filter state).
  - Use that `filters` in the fetch dependency array and in the API call: `paymentApi.fetchPayments(filters)`.
  - Return: `{ payments, loading, error, totalCount, refetch }` (remove `filters` and `setFilters` from the return value).
- **Call site**: In `PaymentManagement.tsx`, keep the existing `filters` and `setFilters` state; pass `filters` to `usePayments(filters)`; pass `filters` and `setFilters` to `PaymentFilters` (unchanged). No other component changes needed for this.

**Result**: Changing status, mode, type, search, or “has unallocated” will correctly refetch the list with the new filters.

---

### Fix 2 (optional): **preSelectedInvoice / pendingPaymentId**

- **Option A**: Do nothing; leave the props unused until you implement “Record Payment” from invoice or deep-link to a payment.
- **Option B**: Implement:
  - When `pendingPaymentId` is set and not null, auto-open the View Details dialog for that payment (fetch by id and set as `paymentForDetail`).
  - When `preSelectedInvoice` is set and user opens New Payment, prefill `party_id` (and optionally payment type) from the invoice; after creating the payment, optionally auto-open the detail dialog and focus Allocations so the user can allocate to that invoice.

Please confirm: **apply only Fix 1**, or **Fix 1 + Fix 2 (Option A or B)**.

---

## 5. Summary

| Item | Status | Action |
|------|--------|--------|
| High-level flow (Create → Allocate → Confirm) | Matches design | None |
| List API & response shape | Correct | None |
| Create/Update payloads & datetime | Fixed earlier | None |
| Confirm 409 + message | Fixed earlier | None |
| Allocation UI in detail dialog | Implemented | None |
| **List filters not applied** | **Broken** | **Fix 1 (usePayments)** |
| preSelectedInvoice / pendingPaymentId | Unused | Fix 2 optional (your choice) |

Once you confirm which fixes to apply (at least Fix 1), I’ll implement them in the codebase.
