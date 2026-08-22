# B2B Billing & Subscription Flow — Complete Reference

## Overview

The billing system is built around a **Master Organization** (your company) that manages **Customer Organizations** (your clients) as subscription customers. System admins belonging to the master org handle all billing operations through the Admin Portal.

---

## 1. Organization Hierarchy

### Master Organization

- Seeded automatically in the identity DB during migration
- Only one can exist (unique constraint on `organization_type = 'master'`)
- Owned exclusively by `system_admin` users
- Cannot be billed — it's the billing entity, not a customer

### Customer Organizations

- Every organization that onboards automatically becomes a "customer" of the master org
- Linked via `parent_organization_id` in the organizations table
- Each gets billing fields: `billing_status`, `subscription_start_date`, `subscription_end_date`, `seat_limit`, `credit_limit`, `billing_cycle`, `next_billing_date`, `billing_contact_email`

### Billing Statuses

`ACTIVE` → `TRIAL` → `OVERDUE` → `SUSPENDED` → `CANCELLED` → `EXPIRED` → `DEACTIVATED`

---

## 2. Subscription Invoice Creation (Manual)

**Who:** System admin via Admin Portal → Billing → Create Invoice

**Steps:**

1. Admin selects the customer organization
2. Chooses billing cycle: `monthly`, `quarterly`, or `yearly`
3. Enters seat count and optional credit usage
4. `SubscriptionInvoiceService` calculates line items:
   - Base subscription fee = seats × price_per_seat × cycle multiplier
   - Credit usage charges = usage × credit_rate
5. Payment terms auto-set by cycle:
   - Monthly → Net 30 days
   - Quarterly → Net 45 days
   - Yearly → Net 60 days
6. Invoice created with:
   - `invoice_type: subscription`
   - `billing_cycle`, `subscription_period_start`, `subscription_period_end`
   - `seat_count`, `credit_usage`
   - Status: `draft`

**Backend flow:**

```
Frontend (BillingManagementPage)
  → BillingManagementService.createSubscriptionInvoice()
    → POST /api/v1/admin/billing/subscription-invoice
      → AdminInvoiceService.create_subscription_invoice()
        → SubscriptionInvoiceService.create_subscription_invoice()
          → Creates Invoice + InvoiceItems in core_db
```

**Key files:**

- Frontend: `apps/admin/src/app/pages/BillingManagementPage.tsx`
- Service: `apps/admin/src/app/services/billing-management.service.ts`
- Backend: `core-service/app/services/subscription_invoice_service.py`
- Backend: `core-service/app/services/admin_invoice_service.py`
- API: `core-service/app/api/v1/endpoints/admin/billing.py`

---

## 3. Invoice Lifecycle

```
draft → sent → pending → paid
                  ↓
               overdue → (reminders) → deactivation
```

| Status      | Meaning                             |
| ----------- | ----------------------------------- |
| `draft`     | Created but not sent to customer    |
| `sent`      | Emailed to customer org admin       |
| `pending`   | Awaiting payment                    |
| `paid`      | Fully paid (outstanding_amount = 0) |
| `overdue`   | Past due date, not paid             |
| `cancelled` | Voided by admin                     |

**Sending an invoice:**

- Admin clicks "Mark as Sent" on invoice detail
- Calls `POST /api/v1/admin/invoices/{id}/send`
- Status changes `draft → sent/pending`
- Email sent to org's billing contact

---

## 4. Payment Reminder Escalation

### Trigger

When invoices go past their due date, they appear as overdue in the Billing dashboard.

### Escalation Stages

| Stage             | Timing                                                     | Tone               |
| ----------------- | ---------------------------------------------------------- | ------------------ |
| `first_reminder`  | Grace period after due date (configurable, default 7 days) | Gentle             |
| `second_reminder` | After first reminder interval                              | Standard/Firm      |
| `final_notice`    | After second reminder interval                             | Final warning      |
| Deactivation      | After final notice period                                  | Account suspension |

### How Reminders Are Sent

1. **Manual:** Admin selects overdue invoice → clicks "Send Reminder" from actions dropdown
2. **Batch:** Admin goes to Payment Reminders page → selects multiple invoices → sends batch
3. **Semi-automatic:** System shows overdue invoices, admin clicks "Send Reminders"
4. **Automated:** (Not yet implemented) Cron job checks daily and sends based on config

### Reminder Configuration (per organization)

- `grace_period_days` — days after due date before first reminder
- `first_reminder_days`, `second_reminder_days`, `final_notice_days`
- `reminder_frequency_days` — interval between reminders
- `max_reminders_per_stage` — cap per escalation level
- `auto_deactivate_days` — days before auto-deactivation

### Reminder Logging

Every sent reminder is logged in `reminder_logs` with:

- Organization ID, invoice ID
- Reminder stage, recipient email
- Status (sent/pending/failed), timestamp

**Key files:**

- Frontend: `apps/admin/src/app/pages/PaymentRemindersPage.tsx`
- Service: `apps/admin/src/app/services/payment-reminder.service.ts`
- Backend: `core-service/app/api/v1/endpoints/admin/payment_reminders.py`
- Backend: `core-service/app/models/reminder_config.py`

---

## 5. Payment Capture

### Option A: Mark as Paid (manual confirmation)

- Admin opens invoice detail → clicks "Mark as Paid"
- Enters payment date, method, reference
- Calls `POST /api/v1/admin/invoices/{id}/mark-paid`
- Sets `outstanding_amount = 0`, `status = paid`

### Option B: Create Payment (creates PaymentEntry record)

- Admin opens invoice detail → clicks "Create Payment"
- Enters amount, method, date, notes
- Calls `POST /api/v1/admin/invoices/{id}/create-payment`
- Creates `PaymentEntry` + `PaymentReference` linking payment to invoice
- Reduces `outstanding_amount` by payment amount
- If fully paid → `status = paid`

### Option C: Payment Gateway (not yet implemented)

- Future integration with Stripe/PayPal
- Endpoint stub exists: `POST /api/v1/admin/invoices/{id}/capture-payment-intent`

**Key files:**

- Frontend: `apps/admin/src/app/components/billing/InvoiceDetailModal.tsx`
- Backend: `core-service/app/services/admin_invoice_service.py` (create_payment_from_invoice)
- Backend: `core-service/app/api/v1/endpoints/admin/invoices.py`

---

## 6. Organization Deactivation (Non-Payment)

### Automated Monitoring

`OrganizationDeactivationService` checks all organizations for:

- Expired trials (`trial_end_date` passed)
- Expired subscriptions (`subscription_end_date` passed)
- Overdue payments requiring escalation

### Escalation Timeline

| Days Overdue | Action                                      |
| ------------ | ------------------------------------------- |
| 0-29         | First reminder stage                        |
| 30-59        | Second reminder, billing status → `overdue` |
| 60-89        | Final notice                                |
| 90+          | Suspension — `billing_status → suspended`   |

### Deactivation Types

| Type                    | Trigger                        | Effect                          |
| ----------------------- | ------------------------------ | ------------------------------- |
| Trial Expiration        | `trial_end_date` passed        | Org deactivated, users blocked  |
| Subscription Expiration | `subscription_end_date` passed | Org deactivated                 |
| Non-Payment Suspension  | 90+ days overdue               | Org suspended, logins disabled  |
| Cancellation            | Admin or user-initiated        | Grace period, then deactivation |

### What Happens When Deactivated

- All user logins for that organization are disabled
- Users see "subscription expired" page
- Only org admin users receive deactivation notification
- Data is preserved (not deleted)

**API Endpoints:**

```
GET  /api/v1/organization-management/check-deactivations
GET  /api/v1/organization-management/deactivation-summary
POST /api/v1/organization-management/expire-trial/{org_id}
POST /api/v1/organization-management/expire-subscription/{org_id}
POST /api/v1/organization-management/suspend/{org_id}
POST /api/v1/organization-management/cancel/{org_id}
POST /api/v1/organization-management/reactivate/{org_id}
POST /api/v1/organization-management/bulk-suspension
GET  /api/v1/organization-management/organization-status/{org_id}
```

**Key files:**

- Backend: `identity-service/app/services/organization_deactivation_service.py`
- API: `identity-service/app/api/v1/endpoints/organization_deactivation.py`

---

## 7. Reactivation

- Requires manual review by system admin
- Admin calls `POST /api/v1/organization-management/reactivate/{org_id}`
- Must provide new `subscription_end_date`
- Billing status restored to `active`
- User access restored immediately
- Reactivation logged in audit trail

---

## 8. Admin Portal UI Pages

| Page                      | Route                        | Purpose                                               |
| ------------------------- | ---------------------------- | ----------------------------------------------------- |
| Billing                   | `/billing`                   | Dashboard with stats, invoices tab, organizations tab |
| Invoices                  | `/invoices`                  | Full invoice list with filters, create, view detail   |
| Payment Reminders         | `/payment-reminders`         | Overdue invoices, send reminders, config, logs        |
| Organizations             | `/organizations`             | Org management (billing status visible here too)      |
| Organization Deactivation | `/organization-deactivation` | Deactivation summary, actions                         |

---

## 9. Database Schema (Key Tables)

### Identity DB — `organizations` table (billing fields)

```
billing_status          — ACTIVE/TRIAL/OVERDUE/SUSPENDED/CANCELLED/EXPIRED
subscription_start_date — when subscription began
subscription_end_date   — when subscription expires
trial_end_date          — when trial expires
seat_limit              — max users allowed
credit_limit            — max credits allowed
billing_contact_email   — who receives invoices
billing_cycle           — monthly/quarterly/yearly
customer_since          — when they became a customer
last_billed_date        — last invoice date
next_billing_date       — next scheduled invoice
parent_organization_id  — links to master org
```

### Core DB — `invoices` table (subscription fields)

```
billing_cycle                — monthly/quarterly/yearly
subscription_period_start    — billing period start
subscription_period_end      — billing period end
seat_count                   — seats being billed
credit_usage                 — credit consumption
```

### Core DB — `reminder_configs` table

```
organization_id, grace_period_days, first_reminder_days,
second_reminder_days, final_notice_days, auto_deactivate_days,
reminder_frequency_days, max_reminders_per_stage, is_enabled
```

### Core DB — `reminder_logs` table

```
config_id, organization_id, invoice_id, recipient_email,
reminder_stage, status, sent_at, error_message
```

---

## 10. Implementation Status

| Feature                                 | Status  |
| --------------------------------------- | ------- |
| Master org schema & seeding             | Done    |
| Organization billing status tracking    | Done    |
| Subscription invoice creation (manual)  | Done    |
| Invoice line item calculation           | Done    |
| Payment capture (manual + PaymentEntry) | Done    |
| Payment reminder sending (manual/batch) | Done    |
| Reminder escalation stages              | Done    |
| Reminder configuration per org          | Done    |
| Organization deactivation service       | Done    |
| Deactivation API endpoints              | Done    |
| Reactivation with manual review         | Done    |
| System admin permissions (cross-org)    | Done    |
| Admin portal billing UI                 | Done    |
| Automated invoice generation (cron)     | Not yet |
| Automated reminder scheduling (cron)    | Not yet |
| Payment gateway integration (Stripe)    | Not yet |
| Customer self-service billing portal    | Not yet |
