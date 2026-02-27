# Supplier / Customer, Journal, Chart of Accounts & Payment – Current Implementation

This document describes how **customers/suppliers**, **chart of accounts**, **journal entries**, and **payments** interact in the current codebase.

---

## 1. High-level flow

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│ Customer/       │     │ Payment Entry     │     │ Journal Entry        │
│ Supplier (Party)│────▶│ (party_id, type,  │────▶│ (posted on Confirm)  │
│                 │     │  amount, mode)    │     │                      │
└─────────────────┘     └────────┬─────────┘     └──────────┬──────────┘
                                 │                           │
                                 │  Default Accounts         │  Lines use
                                 ▼                           ▼
                        ┌──────────────────┐     ┌─────────────────────┐
                        │ DefaultAccount   │     │ Chart of Accounts    │
                        │ (transaction_    │────▶│ (Account: id, code,  │
                        │  type → account) │     │  type, hierarchy)    │
                        └──────────────────┘     └─────────────────────┘
```

- **Party** (customer or supplier) is stored on the payment via `party_id` + `payment_type`.
- **Payment** on confirm triggers **journal posting**, which uses **default accounts** to pick **chart of accounts** (by transaction type).
- **Journal entries** store header + lines; each line posts to one **account** (debit/credit).

---

## 2. Customer / Supplier (Party)

### Role

- **Customer** and **Supplier** are the “party” on a payment.
- A payment is either **Customer_Payment** or **Supplier_Payment** and has a single **party_id** (UUID) pointing to that customer or supplier.

### Where it appears

| Layer | What | How party is used |
|-------|------|-------------------|
| **Model** | `PaymentEntry` | `party_id` (UUID), `payment_type` (Customer_Payment / Supplier_Payment). No FK to customers/suppliers; resolved at read time. |
| **Service** | `PaymentEntryService` | Validates party exists and belongs to org. `_get_party_display_maps()` loads customer/supplier by ID to fill `party_name`, `party_code`, `party_email`, `party_phone` for list/detail. |
| **Journal** | `JournalPostingService` | Uses **payment_type** only to decide which default accounts are *required* (AR for customer, AP for supplier). **Current posting logic uses only customer path** (see below). |

### Important point

- **Party is not stored in the journal.** Journal lines use **accounts** (e.g. Accounts Receivable, Cash). Sub-ledgers (e.g. per-customer AR balance) would be a separate feature; currently the journal is account-level only.

---

## 3. Chart of Accounts

### Role

- Defines **accounts** (hierarchical: code, name, type, parent).
- **Journal entry lines** post **debits/credits** to these accounts.
- **Default accounts** map **transaction types** (e.g. `cash`, `accounts_receivable`) to a specific account so payment confirmation can pick the right accounts automatically.

### Main concepts

| Concept | Where | Purpose |
|--------|--------|--------|
| **Account** | `accounts` table (Chart of Accounts) | Each journal line has `account_id` → one account. Account has `account_type` (ASSET, LIABILITY, INCOME, EXPENSE, etc.). |
| **DefaultAccount** | `default_accounts` table | Maps `(organization_id, transaction_type, scenario)` → `account_id`. Used by payment journal posting to resolve “which account for cash?”, “which for AR?”, etc. |
| **DefaultAccountService** | `default_account_service.py` | `get_default_account(transaction_type, organization_id, scenario)` – used by `JournalPostingService`. Validates account type matches transaction type (e.g. AR must be ASSET). |


### Transaction types used for payments

- **Customer payment (confirm):**  
  - `cash` / `checks_received` / `bank` → account to **debit** (receipt side).  
  - `accounts_receivable` → account to **credit**.
- **Supplier payment (confirm):**  
  - `accounts_payable` → account to **debit**.  
  - `cash` / `checks_received` / `bank` → account to **credit**.

### Seeding

- **Chart of accounts:** e.g. `seed_chart_of_accounts.py` (creates accounts 1110 Cash, 1120 AR, etc.).
- **Default accounts for payments:** `seed_default_accounts_for_payments.py` sets `cash` → 1110, `accounts_receivable` → 1120 so that **customer** payment confirm can post.

---

## 4. Journal (Journal Entry)

### Role

- When a **payment** is **confirmed**, a **journal entry** is created (and optionally reversed on **cancel**).
- Each journal entry has **lines**; each line is one account, with **debit** and **credit** amounts.

### Model

| Table | Purpose |
|-------|--------|
| **journal_entries** | Header: `posting_date`, `voucher_type`, `reference_type` (e.g. `PaymentEntry`), `reference_id` (payment id), `total_debit`, `total_credit`, `status` (`posted`). |
| **journal_entry_lines** | Per account: `account_id` (FK to `accounts`), `debit`, `credit`, `against_account_id`, `reference_type`, `reference_id` (payment id). |

### Who creates it

- **JournalPostingService**
  - `post_payment_journal_entry(payment_entry, organization_id, user_id)` – called from **PaymentEntryService.confirm_payment()** after status is set to Confirmed.
  - `reverse_payment_journal_entry(...)` – called from **PaymentEntryService.cancel_payment()** to reverse the original entry (swap debits/credits).

### Flow (customer payment only, today)

1. **Validate** default accounts: for the payment’s `payment_type` and `payment_mode`, the required default accounts must exist (e.g. AR + cash/bank/checks).
2. **Resolve accounts:**  
   - Debit account = default for `payment_mode` → `cash` / `checks_received` / `bank`.  
   - Credit account = default for `accounts_receivable`.
3. **Convert amount** to base currency (if payment currency ≠ base).
4. **Create one journal entry** with two lines:  
   - Line 1: Debit payment account (Cash/Bank/Checks), Credit 0.  
   - Line 2: Debit 0, Credit AR.  
   - `reference_type` = `PaymentEntry`, `reference_id` = payment id.

So: **Chart of Accounts** supplies the accounts; **DefaultAccount** supplies which account is “Cash”, “AR”, etc.; **Journal** records the double-entry for that payment.

---

## 5. Payment

### Lifecycle and interaction with journal / chart of accounts

| Step | What happens | Interaction with CoA / Journal |
|------|------------------------------------------------|--------------------------------|
| **Create** | User creates payment (party_id, payment_type, amount, payment_mode, etc.). Status = Draft. Receipt number from Document Numbering (e.g. RCP-2026-00001). | No journal; no chart of accounts yet. |
| **Allocate** | User allocates payment to invoice(s) (PaymentReference records). Still Draft. | No journal. |
| **Confirm** | At least one allocation required. Default accounts validated (AR + cash/bank/checks for customer; AR + AP + cash/bank/checks for supplier). Then: status → Confirmed, then **JournalPostingService.post_payment_journal_entry()** creates one journal entry. | **Chart of Accounts**: lines use accounts from **DefaultAccount** (cash/bank/checks + AR). **Journal**: one posted entry, linked to payment via `reference_type`/`reference_id`. |
| **Cancel** | Only Confirmed payments. User gives reason. Status → Cancelled, then **JournalPostingService.reverse_payment_journal_entry()** creates a reversing entry (same accounts, debits/credits swapped). | **Journal**: second entry (reversal) linked to same payment. **Chart of Accounts**: same accounts, opposite effect. |


### Supplier payment logic (now implemented)

- **Validation** for confirm requires **accounts_payable** (and payment-mode account) when `payment_type == Supplier_Payment`.
- **Actual posting** in `post_payment_journal_entry()` now branches on payment type:
  - **Customer payments:** Debit Cash/Bank/Checks, Credit AR (unchanged).
  - **Supplier payments:** Debit Accounts Payable, Credit Cash/Bank/Checks (new logic).
  - Both use default accounts for mapping.

---

## 6. End-to-end interaction summary

| Entity | How it ties in |
|--------|----------------|
| **Customer / Supplier** | Identified on **Payment** via `party_id` + `payment_type`. Used for validation, display (party name/contact), and to require the right **default accounts** (AR vs AP). Not stored on journal lines. |
| **Chart of Accounts** | Defines **Account** records. **Journal entry lines** post to these accounts. **DefaultAccount** maps transaction types (cash, bank, AR, AP, etc.) to specific account IDs. |
| **Default accounts** | Bridge between “payment mode / payment type” and “which CoA account to use”. Required before confirming a payment. Configured via seed script or (in UI) System Configuration (e.g. accounts for cash, bank, checks_received, accounts_receivable, accounts_payable). |
| **Journal** | Created on **payment confirm** (one entry per payment); reversed on **payment cancel**. Lines reference **accounts** from the chart of accounts. Linked to payment via `reference_type` = `PaymentEntry`, `reference_id` = payment id. |
| **Payment** | Drives the flow: create (party, amount, mode) → allocate to invoices → confirm (validates default accounts, then posts journal) → optional cancel (reverses journal). |

In short: **Party** is on the payment; **Chart of Accounts** provides the accounts; **Default accounts** tell the system which account to use for cash, AR, AP, etc.; **Journal** records the double-entry when a payment is confirmed (and its reversal when cancelled). Currently only **customer** payment posting is implemented; **supplier** payment posting (Debit AP, Credit Bank/Cash) is not yet implemented in `JournalPostingService`.
