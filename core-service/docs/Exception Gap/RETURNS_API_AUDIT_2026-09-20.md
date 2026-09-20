# Returns API Audit — Web App & Handheld

> **Date**: 2026-09-20
> **Environment**: local stack (`horizon_identity` :8000, `horizon_core` :8001, `horizon_postgres`)
> **User / tenant tested**: `ttkwmsmanager@prestige.com` → org `147f3b9d-77fd-432f-8d91-e5559af9d897` (Prestige), permissions `["*.*"]`
> **Warehouses**:
> - `8bc22a62-9e7a-4839-8f39-e58f6087d25e` — **Mother warehouse** (WH-2026-00002, parent)
> - `f0099ec7-0364-416c-9806-22fe38a4c56c` — **Ecity Warehouse** (WH-2026-00001, child)
>
> **Method**: compared every endpoint in `RETURNS_WEB_APP_INTEGRATION.md` and
> `RETURNS_HANDHELD_INTEGRATION.md` against the live `GET /openapi.json` (581 paths),
> plus row counts in Postgres. Read-only — no data was changed.

---

## 1. Verdict

| Area | Result |
| ---- | ------ |
| Login / tenant / warehouses | ✅ OK |
| **Returns module endpoints (web + handheld)** | ❌ **0 of 18 exist** |
| Endpoints the docs say are "already live" | ✅ 5 of 5 exist and respond |
| `return.*` permissions | ❌ none |
| `RETURN_*` exception reason codes | ❌ none seeded |
| Return tables (`return_registrations`, `return_receipt_notes`, `return_sessions`, …) | ❌ do not exist |
| Migrations past `123_notification_inbound_exception` | ❌ none |

**There is nothing to test for the returns flow yet.** Both integration guides carry the banner
*"SPECIFICATION — the returns module is not deployed yet"*, and the repo agrees: no code, no
models, no migration, no routes. The whole chain is backlog `R-01` → `R-10`, estimated
**3–4 weeks** (gap analysis §4.1 / §5 Phase 2).

---

## 2. Returns module endpoints — 0 / 18 present

### Web app — `RETURNS_WEB_APP_INTEGRATION.md`

| Task | Method | Path | Status |
| ---- | ------ | ---- | ------ |
| R-02 | `GET` | `/api/v1/returns/references` | ❌ 404 |
| R-01 | `POST` | `/api/v1/returns/registrations` | ❌ 404 |
| R-01 | `GET` | `/api/v1/returns/registrations` | ❌ 404 |
| R-01 | `GET` | `/api/v1/returns/registrations/{id}` | ❌ 404 |
| R-01 | `POST` | `/api/v1/returns/registrations/{id}/cancel` | ❌ 404 |
| R-05 | `GET` | `/api/v1/returns/receipt-notes` | ❌ 404 |
| R-05 | `GET` | `/api/v1/returns/receipt-notes/{id}` | ❌ 404 |
| R-06 | `POST` | `/api/v1/returns/receipt-notes/{id}/approve` | ❌ 404 |
| R-06 | `POST` | `/api/v1/returns/receipt-notes/{id}/reject` | ❌ 404 |
| R-06 | `POST` | `/api/v1/returns/receipt-notes/{id}/disposition` | ❌ 404 |
| R-07 | `POST` | `/api/v1/returns/receipt-notes/{id}/generate-put-away` | ❌ 404 |
| R-08 | `GET` | `/api/v1/returns/receipt-notes/{id}/slip` | ❌ 404 |

### Handheld — `RETURNS_HANDHELD_INTEGRATION.md`

| Task | Method | Path | Status |
| ---- | ------ | ---- | ------ |
| R-03 | `POST` | `/api/v1/returns/registrations/{id}/sessions` | ❌ 404 |
| R-03 | `GET` | `/api/v1/returns/sessions/{id}` | ❌ 404 |
| R-03 | `POST` | `/api/v1/returns/sessions/{id}/scans` | ❌ 404 |
| R-03 | `POST` | `/api/v1/returns/sessions/{id}/end` | ❌ 404 |
| R-04 | `POST` | `/api/v1/returns/sessions/{id}/classify` | ❌ 404 |
| R-04 | `POST` | `/api/v1/returns/sessions/{id}/classify/bulk` | ❌ 404 |

---

## 3. Reused "live today" endpoints — 5 / 5 working

| Method | Path | Result |
| ------ | ---- | ------ |
| `POST` | `/api/v1/inbound/exceptions/unreadable-qr` | ✅ route live (empty body → `400 VALIDATION_ERROR` naming `session_id`, `carton_reference`) |
| `GET` | `/api/v1/inbound/exception-reasons` | ✅ `200` |
| `GET` | `/api/v1/items` | ✅ `200` |
| `GET` | `/api/v1/put-away` | ✅ `200` |
| `POST` | `/api/v1/put-away/{list}/items/{item}/complete` | ✅ route registered |

These are the **only** parts of the returns story a client can call today.

---

## 4. Blocker found beyond the missing module: no sales reference data

`RETURNS_WEB_APP_INTEGRATION.md` §4 builds the registration form on
`GET /returns/references?invoice_no=…`, resolving an **invoice → party → warehouse → lines** triple
(R-02, "read-model over `invoices`, `customers`, `warehouses`").

The actual `invoices` table is **not** a sales invoice:

- `invoices` columns are `subscription_period_start`, `subscription_period_end`, `seat_count`,
  `billing_cycle`, `credit_usage` — it is the **tenant SaaS billing** document.
- It has **no `warehouse_id`** and **no customer/dealer reference**, so the documented
  `invoice.warehouse` / `invoice.party` block cannot be produced from it.
- `invoices` has **0 rows**; `invoice_items` has **0 rows**.

The real outbound/sales-side documents are `delivery_notes` / `delivery_note_items` /
`outbound_orders` / `dispatch_records` — and those are essentially empty too
(`delivery_notes` 0, `delivery_note_items` 0, `outbound_orders` 13, `dispatch_records` 2).

**Consequence:** R-02 must be re-pointed at a real sales document (delivery note / outbound order)
before it can be built, and there is currently no outbound history for a return to reference. This
is a design decision, not just a data-seeding gap. It is closest to open question **§6 Q2**
(*"is the reference always an existing WMS invoice, or may returns be registered against a
free-text dealer/warehouse reference?"*).

---

## 5. Data already present (for context)

| Table | Mother (`8bc22a62`) | Ecity (`f0099ec7`) |
| ----- | ------------------- | ------------------ |
| `asn_orders` | 32 | 95 |
| `receiving_slips` | 24 | 120 |
| `put_away_lists` | 24 | 98 |
| `inbound_exceptions` | 84 | 94 |

Org-wide: `customers` 837, `items` 28, `outbound_orders` 13, `invoices` 0, `delivery_notes` 0.

So the **inbound** side is already well populated in both warehouses — it does not need seeding.
The **outbound/sales** side (the thing returns must point at) is empty.

---

## 6. What "make the APIs work" would take

Phase 2 of the gap analysis, `R-01` → `R-07` + `R-10` (+ `X-05` for HC screens):

1. **R-01** `return_registrations` + `return_registration_items` tables, lifecycle, numbering `RR`.
2. **R-02** reference lookup — **needs the design decision in §4 first**.
3. **R-03** return receiving session (`return_sessions` / `return_session_items`, or
   `scan_sessions.session_type='return'`), scans with duplicate hard stop.
4. **R-04** condition classification, reusing `inbound_exception_reasons` (+ `return_*` categories).
5. **R-05** draft Return Receipt Note + numbering `RRN`.
6. **R-06** supervisor approve / reject / per-line disposition, `assert_manager()` gate + audit.
7. **R-07** put-away generation for `release_to_stock` lines, segregation for the rest.
8. **R-10** `return.register` / `return.receive` / `return.classify` / `return.approve` /
   `return.dispose`.

Note the local schema check constraint currently allows `scan_sessions.session_type` of only
`inbound` | `gate`, so `'return'` needs a migration either way.
