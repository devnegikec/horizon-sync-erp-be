# Migration Task List: Old Django QSeal → New FastAPI Services

## Status Legend

- 🟢 Done (already in new services)
- 🟡 Partial (needs work)
- 🔴 Not started (needs new module)
- ⏭️ Skip (not needed in new system)

---

## Phase 1: Foundation & Auth (identity-service)

### 1.1 Organizations & Users — identity_db

| #     | Task                                                               | Status | Notes                                                                  |
| ----- | ------------------------------------------------------------------ | ------ | ---------------------------------------------------------------------- |
| 1.1.1 | Export `dashboard_client` → `organizations`                        | 🟢     | `scripts/migration/phase1_export_from_old_db.sql`                      |
| 1.1.2 | Export `integration_brand` → merge into `organizations.extra_data` | 🟢     | Merged in same export SQL (short_code, public_key, etc.)               |
| 1.1.3 | Export `users_user` → `users`                                      | 🟢     | `scripts/migration/phase1_export_from_old_db.sql`                      |
| 1.1.4 | Create default roles (system_admin, org_admin, user)               | 🟢     | `scripts/migration/phase1_import_to_identity_db.sql` — Step 3          |
| 1.1.5 | Build `user_organization_roles` from old user-tenant FK            | 🟢     | `scripts/migration/phase1_import_to_identity_db.sql` — Step 4          |
| 1.1.6 | Password strategy: PBKDF2 → bcrypt                                 | 🟢     | Force reset — placeholder hash set, old hash preserved in `extra_data` |
| 1.1.7 | Verify row counts & no duplicate slugs                             | 🟢     | `scripts/migration/phase1_verify.sql`                                  |

### 1.2 Auth Endpoints — identity-service

| #     | Task              | Old Endpoint              | New Endpoint                              | Status |
| ----- | ----------------- | ------------------------- | ----------------------------------------- | ------ |
| 1.2.1 | Login             | `POST auth/login/`        | `POST /api/v1/auth/login`                 | 🟢     |
| 1.2.2 | Logout            | `POST auth/logout/`       | `POST /api/v1/auth/logout`                | 🟢     |
| 1.2.3 | Register          | `POST auth/web_register/` | `POST /api/v1/auth/register`              | 🟢     |
| 1.2.4 | Send email OTP    | `POST sent-otp/`          | `POST /api/v1/identity/otp/email/send`    | �      |
| 1.2.5 | Verify email OTP  | `POST otp/`               | `POST /api/v1/identity/otp/email/verify`  | �      |
| 1.2.6 | Send mobile OTP   | `POST send_mobileotp/`    | `POST /api/v1/identity/otp/mobile/send`   | �      |
| 1.2.7 | Verify mobile OTP | `POST verify_mobileotp/`  | `POST /api/v1/identity/otp/mobile/verify` | �      |
| 1.2.8 | Create tenant     | `POST create-tenant/`     | `POST /api/v1/organizations`              | 🟡     |

**Action for 1.2.4–1.2.7**: Add `otp_verifications` table (Alembic migration `004_add_otp_verifications.py`) and OTP endpoints to identity-service.

---

## Phase 2: QR Products & Blocks (core-service — new module)

> Old app was a QR platform. These have no equivalent in core-service yet.

| #    | Task                                                                  | Old Endpoint                    | Status |
| ---- | --------------------------------------------------------------------- | ------------------------------- | ------ |
| 2.1  | Alembic migration: `qr_products`, `qr_blocks`, `product_items`        | —                               | 🔴     |
| 2.2  | Alembic migration: `qr_activation_parameters`, `qr_activation_tracks` | —                               | 🔴     |
| 2.3  | Alembic migration: `qr_credit_usage`                                  | —                               | 🔴     |
| 2.4  | List/create products                                                  | `GET/POST products/`            | 🔴     |
| 2.5  | Generate QR block                                                     | `POST generate/product-block/`  | 🔴     |
| 2.6  | Activate QR code                                                      | `POST product/activate/`        | 🔴     |
| 2.7  | QR settings (get/set)                                                 | `GET/POST product/qr_settings/` | 🔴     |
| 2.8  | QR scan analytics                                                     | `GET product/qr_scans/`         | 🔴     |
| 2.9  | Product expiry tracking                                               | `GET product/expiry/`           | 🔴     |
| 2.10 | Validate/authenticate product                                         | `POST validate/product-block/`  | 🔴     |
| 2.11 | Migrate `integration_product` data → `qr_products`                    | —                               | 🔴     |
| 2.12 | Migrate `qr_blocks` / `product_items` data                            | —                               | 🔴     |

---

## Phase 3: Campaigns & Coupons (core-service — new module)

| #    | Task                                                                            | Old Endpoint                                    | Status |
| ---- | ------------------------------------------------------------------------------- | ----------------------------------------------- | ------ |
| 3.1  | Alembic migration: `campaigns`, `web_campaigns`, `play2win_prizes`              | —                                               | 🔴     |
| 3.2  | Alembic migration: `leads`, `coupons`, `external_coupons`, `coupon_unlock_logs` | —                                               | 🔴     |
| 3.3  | Alembic migration: `tags`, `lead_tags`, `coupon_durations`, `shopify_configs`   | —                                               | 🔴     |
| 3.4  | Coupon verification                                                             | `POST coupon-verification/`                     | 🔴     |
| 3.5  | Coupon redeem                                                                   | `POST coupon-redeem/`                           | 🔴     |
| 3.6  | Coupon unlock                                                                   | `POST coupon-unlock/`                           | 🔴     |
| 3.7  | Lead/CRM create & list                                                          | `GET/POST userinfo/`                            | 🔴     |
| 3.8  | Feedback submit                                                                 | `POST feedback/`                                | 🔴     |
| 3.9  | Survey submit/list                                                              | `GET/POST surveysubmitview/`, `surveylistview/` | 🔴     |
| 3.10 | Migrate `campaigns` data                                                        | —                                               | 🔴     |
| 3.11 | Migrate `leads` → `customers` (partial overlap)                                 | —                                               | 🟡     |
| 3.12 | Migrate `coupons` data                                                          | —                                               | 🔴     |

---

## Phase 4: Warranty Module (core-service — new module)

| #   | Task                                                | Old Endpoint           | Status |
| --- | --------------------------------------------------- | ---------------------- | ------ |
| 4.1 | Alembic migration: `warranty_periods`, `warranties` | —                      | 🔴     |
| 4.2 | Register warranty                                   | `POST warranty/`       | 🔴     |
| 4.3 | Create warranty record                              | `POST warrantycreate/` | 🔴     |
| 4.4 | Check warranty by serial                            | `GET warranty-check/`  | 🔴     |
| 4.5 | Search warranty records                             | `GET warranty-search/` | 🔴     |
| 4.6 | Migrate `warranties` data                           | —                      | 🔴     |

---

## Phase 5: Messaging Module (core-service — new module)

| #   | Task                                                                                                    | Old Endpoint              | Status |
| --- | ------------------------------------------------------------------------------------------------------- | ------------------------- | ------ |
| 5.1 | Alembic migration: `message_templates`, `bulk_message_jobs`, `scheduled_messages`                       | —                         | 🔴     |
| 5.2 | Alembic migration: `sms_reports`, `whatsapp_reports`, `rcs_templates`, `rcs_reports`, `message_credits` | —                         | 🔴     |
| 5.3 | Send WhatsApp message                                                                                   | `POST whatsapp_post/`     | 🔴     |
| 5.4 | WhatsApp delivery webhook                                                                               | `POST whatsapp_webhooks/` | 🔴     |
| 5.5 | SMS delivery webhook                                                                                    | `POST sms_webhooks/`      | 🔴     |
| 5.6 | Send RCS message                                                                                        | `POST rcs_post/`          | 🔴     |
| 5.7 | Migrate `message_templates` data                                                                        | —                         | 🔴     |
| 5.8 | Migrate `sms_reports` / `whatsapp_reports` data                                                         | —                         | 🔴     |

---

## Phase 6: Analytics Module (core-service — new module)

| #   | Task                                                  | Old Endpoint            | Status |
| --- | ----------------------------------------------------- | ----------------------- | ------ |
| 6.1 | Alembic migration: `qr_scan_events`, `meta_campaigns` | —                       | 🔴     |
| 6.2 | QR scan event ingestion (replaces Metamo)             | `GET product/qr_scans/` | 🔴     |
| 6.3 | Meta campaign analytics                               | —                       | 🔴     |
| 6.4 | Migrate historical scan data                          | —                       | 🔴     |

---

## Phase 7: Cascade / Hierarchical QR (core-service — new module)

| #   | Task                                                     | Old Endpoint                | Status |
| --- | -------------------------------------------------------- | --------------------------- | ------ |
| 7.1 | Alembic migration: `qr_activation_tracks` (parent-child) | —                           | 🔴     |
| 7.2 | Manage parent QR codes                                   | `GET/POST parentqr/`        | 🔴     |
| 7.3 | Create child QR codes                                    | `POST child_qrs/`           | 🔴     |
| 7.4 | Map parent-child relationships                           | `POST map_qrs/`             | 🔴     |
| 7.5 | Track cascade QR scan                                    | `POST scanqrs/`             | 🔴     |
| 7.6 | Download QR label batch                                  | `GET labels_download/`      | 🔴     |
| 7.7 | Cascade scan history                                     | `GET/POST cascade-history/` | 🔴     |

---

## Phase 8: URL Management (core-service — new module)

| #   | Task                 | Old Endpoint               | Status |
| --- | -------------------- | -------------------------- | ------ |
| 8.1 | Short URL generation | `POST generate/short-url/` | 🔴     |
| 8.2 | Short URL resolution | `GET shorturl/`            | 🔴     |

---

## Phase 9: Destinations / Markets (core-service — new module)

| #   | Task                          | Old Endpoint                | Status                                        |
| --- | ----------------------------- | --------------------------- | --------------------------------------------- |
| 9.1 | Destination market management | `GET/POST destinations/`    | 🔴                                            |
| 9.2 | Currency by destination       | `GET destination/currency/` | 🟡 (currencies exist, needs destination link) |

---

## Phase 10: Brand Trust Assessment (core-service — new module)

| #    | Task                     | Old Endpoint                  | Status                            |
| ---- | ------------------------ | ----------------------------- | --------------------------------- |
| 10.1 | Assessment questions     | `GET questions/`              | 🔴                                |
| 10.2 | Start assessment         | `POST start/`                 | 🔴                                |
| 10.3 | Submit assessment        | `POST submit/`                | 🔴                                |
| 10.4 | Assessment report        | `GET assessment-report/`      | 🔴                                |
| 10.5 | Brand trust PDF          | `GET brandtrust-pdf/`         | 🔴                                |
| 10.6 | Email brand trust report | `POST send-brandtrust-email/` | 🟡 (communications module exists) |
| 10.7 | List industries          | `GET brandindustry/`          | 🔴                                |

---

## Phase 11: Public / Marketing (identity-service or separate service)

| #    | Task                 | Old Endpoint          | Status |
| ---- | -------------------- | --------------------- | ------ |
| 11.1 | Contact form         | `POST contactus/`     | 🔴     |
| 11.2 | Career application   | `POST career_form/`   | 🔴     |
| 11.3 | Schedule demo        | `POST schedule_demo/` | 🔴     |
| 11.4 | Newsletter subscribe | `POST subscribe/`     | 🔴     |
| 11.5 | Request callback     | `POST request_call/`  | 🔴     |

> These are low-priority marketing endpoints. Can be simple email-forwarding handlers.

---

## Phase 12: ERP Modules Already in core-service (Verify & Test)

These are already implemented — just need frontend integration testing.

| #     | Module                         | Endpoint Prefix             | Status |
| ----- | ------------------------------ | --------------------------- | ------ |
| 12.1  | Items & Item Groups            | `/api/v1/items`             | 🟢     |
| 12.2  | Warehouses                     | `/api/v1/warehouses`        | 🟢     |
| 12.3  | Customers                      | `/api/v1/customers`         | 🟢     |
| 12.4  | Suppliers                      | `/api/v1/suppliers`         | 🟢     |
| 12.5  | Quotations                     | `/api/v1/quotations`        | 🟢     |
| 12.6  | Sales Orders                   | `/api/v1/sales-orders`      | 🟢     |
| 12.7  | Material Requests              | `/api/v1/material-requests` | 🟢     |
| 12.8  | RFQs                           | `/api/v1/rfqs`              | 🟢     |
| 12.9  | Purchase Orders                | `/api/v1/purchase-orders`   | 🟢     |
| 12.10 | Purchase Receipts              | `/api/v1/purchase-receipts` | 🟢     |
| 12.11 | Delivery Notes                 | `/api/v1/delivery-notes`    | 🟢     |
| 12.12 | Invoices                       | `/api/v1/invoices`          | 🟢     |
| 12.13 | Payments                       | `/api/v1/payments`          | 🟢     |
| 12.14 | Smart Picking / Pick Lists     | `/api/v1/smart-picking`     | 🟢     |
| 12.15 | Stock Levels & Movements       | `/api/v1/stock-levels`      | 🟢     |
| 12.16 | Journal Entries                | `/api/v1/journal-entries`   | 🟢     |
| 12.17 | Bank Accounts & Reconciliation | `/api/v1/bank-accounts`     | 🟢     |
| 12.18 | Communications (email)         | `/api/v1/communications`    | 🟢     |
| 12.19 | Chart of Accounts              | `/api/v1/accounts`          | 🟢     |
| 12.20 | Tax Templates                  | `/api/v1/tax-templates`     | 🟢     |
| 12.21 | UOMs                           | `/api/v1/uoms`              | 🟢     |
| 12.22 | Currencies & Exchange Rates    | `/api/v1/currencies`        | 🟢     |
| 12.23 | Bulk Import/Export             | `/api/v1/bulk-import`       | 🟢     |

---

## Recommended Execution Order

Work through phases in this order — each phase is independently testable:

```
Phase 1  → Auth & identity migration (BLOCKER for everything else)
Phase 12 → Verify existing ERP endpoints work with migrated users
Phase 2  → QR Products (core QSeal feature)
Phase 4  → Warranty (simple, standalone)
Phase 3  → Campaigns & Coupons (depends on products)
Phase 7  → Cascade QR (depends on products)
Phase 6  → Analytics (depends on QR scan events)
Phase 5  → Messaging (standalone, can run in parallel)
Phase 8  → URL Management (simple, standalone)
Phase 9  → Destinations (simple)
Phase 10 → Brand Trust Assessment
Phase 11 → Public/Marketing (lowest priority)
```

---

## Quick Reference: What's Blocking Frontend Right Now

If the frontend is already built against the new ERP APIs (Phase 12), the only
blockers are:

1. **Login/Auth** — identity-service auth is live, but OTP flows are missing (1.2.4–1.2.7)
2. **User data** — needs Phase 1 data migration to have real users
3. **QR features** — entire Phase 2 is missing from core-service
4. **Campaigns/Coupons** — entire Phase 3 is missing

Start with Phase 1 + Phase 12 verification to unblock frontend ERP testing immediately.
