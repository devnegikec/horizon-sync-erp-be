# WMS Requirements vs. Codebase — Gap Analysis & Implementation Plan

> **Status:** Analysis / planning document. No code changes made yet.
> **Scope:** ASN (Advance Stock Notice) Management + User Roles, Responsibilities & Permission Management (RBAC), within Warehouse Management & Inventory Management.
> **Architecture:** Microservices — `identity-service` (auth/RBAC/users/orgs) and `core-service` (WMS, inventory, finance).

The codebase is already a mature WMS/ERP. A large portion of both requirement documents is already implemented. This document records what exists, what is missing, and how to sync each gap with the current design.

---

## Part 1 — ASN (Advance Stock Notice) Management

### Already implemented

- **ASN core**: `core-service/app/models/asn_order.py` (`AsnOrder` + `AsnOrderItem`), service `core-service/app/services/asn_order_service.py`, endpoints `core-service/app/api/v1/endpoints/asn_orders.py` (full CRUD + status transitions, RBAC-gated).
- **Unique ASN number**: auto-generated via `DocumentNumberingService` (`asn_order` prefix `ASN`).
- **Status lifecycle + validated transitions**: `AsnOrderStatus` enum (`core-service/app/models/base.py:284`) and `_validate_status_transition`.
- **Notifications on ASN events**: `_emit_asn_notification` routes to warehouse-assigned users with supervisor fallback (`Notification` model, `NotificationType` enum).
- **Scan-based inbound receiving**: `core-service/app/api/v1/endpoints/inbound.py` + `inbound_service.py` — scan sessions (`scan_session.py`), receiving slips (`receiving_slip.py`), SHORT/DAMAGED flagging, approve/reject, auto put-away list generation (`put_away_list.py`, `put_away_rule.py`, `location_allocation.py`, `worker_tasks.py`).
- **Audit history**: `AuditLog` field-level change tracking; `AsnOrder.__audited__ = True`.
- **Mobile scan workflow + dock field**: `ScanSession.dock_location`, QR scan endpoints.

### Gaps & how to sync

| # | Requirement | Status | How to implement (sync with existing) |
|---|-------------|--------|----------------------------------------|
| 1 | Status lifecycle: **Created, In Transit, Arrived, Partially Received, Fully Received, Closed** | Mismatch — current is Draft/Confirmed/Partially_Delivered/Delivered/Closed/Cancelled | Add `IN_TRANSIT`, `ARRIVED` (and align *received* semantics) to `AsnOrderStatus` in `core-service/app/models/base.py:284`; extend `_validate_status_transition`. Add an Alembic enum migration (follow pattern of `047_extend_pick_lists_and_create_put_away_lists.py`). Keep old values as aliases to avoid breaking data. |
| 2 | **Scan-based receiving _against ASN_** + validate received vs ASN qty | Missing link | `ScanSession` (`scan_session.py:21`) has no `asn_order_id`. Add nullable `asn_order_id` FK; on `end_session`/`approve_slip` in `inbound_service.py`, reconcile scanned qty → `AsnOrderItem.delivered_qty` and auto-advance ASN status (Partially/Fully Received). Wires the two existing subsystems together. |
| 3 | ASN sources: **Source warehouse, Vendor, Manufacturing plant** | Partial | Model only has `warehouse_id_from/to`. Add `source_type` (warehouse/vendor/plant) + `supplier_id` FK (reuse `suppliers`) on `AsnOrder`. `reference_type`/`reference_id` already exist for plant/PO refs. |
| 4 | ASN line fields: **batch number, serial numbers (optional)** | Missing columns | `AsnOrderItem` (`asn_order.py:84`) only has `extra_data`. Add `batch_no` + `serial_nos` (JSONB) — mirror `PurchaseReceiptItem` (`purchase_receipt.py:96`) which already has them. |
| 5 | **Vehicle details (shared across multiple ASNs)** | Missing | New `vehicle` entity (vehicle_no, driver, contact) + `vehicle_id` FK on `AsnOrder` (many ASNs → one vehicle). Reuse driver/vehicle schema shape from `GateVerificationSession`. |
| 6 | Import via **Inbox (email-like)** + EDI | Missing | Notification + manual creation exist. Add an "ASN inbox" ingestion endpoint (parse email/EDI/CSV → draft ASN). Reuse `bulk_import_job.py` infrastructure. |
| 7 | Receiving discrepancies: **Excess, Missing, Forwarding** | Partial | `ReceivingSlipItemFlag` (`warehouse_location.py:107`) only has OK/SHORT/DAMAGED. Add `EXCESS`, `MISSING`, `FORWARDING` to enum + handling in `inbound_service.flag_line_item`. |
| 8 | **Auto Goods Receipt confirmation** after receiving | Partial | `PurchaseReceipt` exists but isn't auto-created from ASN receiving. Add a hook in `approve_slip` to generate a Goods Receipt from the approved slip. |
| 9 | **Dock & labor allocation** planning | Partial | `dock_location` is free-text only; `worker_tasks` covers put-away/pick labor, not inbound. Add a dock allocation model + inbound labor task type if formal planning is required. |
| 10 | **Dashboard for expected inbound** | Missing | Add an analytics endpoint (extend `analytics.py`) aggregating ASNs by status/ETA/warehouse. |
| 11 | High-volume / real-time MM-IM integration | Partial | Event hooks exist (`app/events/`); confirm ASN events publish to stock/IM consumers. |

---

## Part 2 — User Roles, Responsibilities & Permission Management (RBAC)

### Already implemented

- **RBAC core** (`identity-service`): `Role`, `Permission`, `RolePermission`, `UserOrganizationRole` (`identity-service/app/models/role.py`). Multi-tenant (org-scoped), reusable roles, custom roles supported.
- **Permission model**: `resource.action` codes + wildcards (`*.*`, `resource.*`) enforced in `core-service/app/dependencies.py:186` (`has_permission`); catalog in `core-service/app/core/authorization.py`.
- **User lifecycle**: `UserStatus` = active/inactive/suspended/pending; activation/deactivation/suspension supported. Soft-delete (`deleted_at`) preserves history.
- **Auth**: password + device info capture on login (`token.py` device_id/name/type/os), remember-me, MFA fields, configurable token expiry (`config.py:34`).
- **Warehouse scoping primitive**: `core-service/app/models/warehouse_user.py` (`WarehouseUser`) links user→warehouse→role (supervisor/manager/operator/coordinator); used for list filtering + ASN notification routing.
- **Audit**: `SystemAdminAuditLog` (identity), field-level `AuditLog` (core), `entity_audit_log`.

### Gaps & how to sync

| # | Requirement | Status | How to implement (sync with existing) |
|---|-------------|--------|----------------------------------------|
| 1 | **Predefined WMS roles**: Warehouse_Admin, Inventory_Controller, Inbound_Operator, Picker, Packer, Dispatch_Supervisor, Gate_Security, Auditor, Viewer | Missing — only system_admin/org_admin/user/owner | Seed these 9 roles + permission bundles. No schema change — use existing `Role` + `RolePermission` and `authorization.py` codes. Add to identity `scripts/seed_data.py`. Highest-value, lowest-risk quick win. |
| 2 | Permission **actions**: Approve, Cancel, Reopen, Override | Missing | `ActionType` (`identity base.py:102`) only has create/read/update/delete/manage/execute/invite. Add `APPROVE`, `CANCEL`, `REOPEN`, `OVERRIDE`; add matching codes in `core-service/app/core/authorization.py`. |
| 3 | **Warehouse-scoped permission enforcement** | Partial / not enforced | `WarehouseUser` exists but `has_permission` is global — a user with `stock_entry.update` can act on any warehouse. Add a warehouse-scope dependency that cross-references `WarehouseUser`. Use `RolePermission.conditions` (JSON, already present) to carry scope. |
| 4 | Permission **levels**: Module / Screen / Transaction / **Device Operation** | Partial | Resource/transaction level exists. Use `module`/`category` columns (already on `Permission`) for screen grouping; add device-operation codes for scanner workflows. |
| 5 | **Approval / maker-checker** for stock adjustment, transfer, override, bin blocking, shipment closure | Missing | No approval engine. Add a lightweight approval workflow (request → pending → approve/reject) gated by new `*.approve` permissions. Bin blocking needs a `WarehouseLocation` block flag. |
| 6 | Assign users to **Zones / Storage Types / Operational Areas** | Partial | `WarehouseUser` is warehouse-level only. Add optional `zone_id`/`operational_area` (zones exist via `WarehouseLocation` type=`zone`). |
| 7 | User fields: **Employee ID, Login ID, Operational Area(s)** | Partial | `User` has email/phone but no `employee_id` / distinct `login_id`. Add columns to `identity-service/app/models/user.py`. |
| 8 | **Device-based login auth** + block unauthorized device txns + device session traceability | Partial | Device info is captured but not used for auth/whitelisting. Add device registration/whitelist + real-time device-permission check. |
| 9 | **Configurable session timeout policy** (per org/role) | Partial | Token expiry is a single global config. Make it org/role-configurable. |
| 10 | **Warehouse operational locks** (during count/audit) + **emergency override w/ audit** | Missing | Add warehouse/zone lock flag + override permission that writes to audit. |
| 11 | **Immutable + searchable audit** for login, user/permission changes, stock txns, approvals, device activity | Partial | Models exist but coverage is incomplete (esp. permission-change + device-activity); immutability not enforced. Extend coverage; enforce append-only at DB level. |
| 12 | **SSO / external identity providers** | Missing (future phase) | Token-based architecture supports it; add OAuth/SAML adapters later. |

---

## Recommended phased rollout

- **Phase 1 (quick wins, mostly seed/config, low risk):** Seed the 9 predefined WMS roles + permission bundles (Gap 2.1); add `APPROVE/CANCEL/REOPEN/OVERRIDE` action types and codes (2.2); align ASN status lifecycle (1.1).
- **Phase 2 (core flow wiring):** Link scan sessions → ASN and reconcile `delivered_qty` + auto status (1.2); add ASN line batch/serial + vendor/plant source + vehicle entity (1.3–1.5); extend receiving flags EXCESS/MISSING/FORWARDING (1.7); auto Goods Receipt (1.8).
- **Phase 3 (governance):** Warehouse-scoped permission enforcement (2.3), maker-checker approvals (2.5), zone/area assignment + user fields (2.6–2.7), audit hardening (2.11).
- **Phase 4 (enterprise):** Device-based auth + locks/override (2.8, 2.10), configurable session policy (2.9), ASN email/EDI inbox + dashboard (1.6, 1.10), SSO (2.12).

---

## Key file references

**ASN / Inbound (core-service):**
- `app/models/asn_order.py`, `app/services/asn_order_service.py`, `app/api/v1/endpoints/asn_orders.py`
- `app/models/scan_session.py`, `app/models/receiving_slip.py`, `app/models/put_away_list.py`, `app/models/put_away_rule.py`
- `app/api/v1/endpoints/inbound.py`, `app/services/inbound_service.py`
- `app/models/purchase_receipt.py`, `app/models/gate_verification.py`
- Enums: `app/models/base.py` (`AsnOrderStatus`, `NotificationType`), `app/models/warehouse_location.py` (`ReceivingSlipItemFlag`, scan/gate enums)

**RBAC (identity-service):**
- `app/models/role.py` (`Role`, `Permission`, `RolePermission`, `UserOrganizationRole`)
- `app/models/user.py`, `app/models/token.py`, `app/models/audit_log.py`, `app/models/base.py` (`ResourceType`, `ActionType`, `UserStatus`)
- `app/config.py` (session/token expiry), `scripts/seed_data.py`
- `ROLES.md`, `USER_PERMISSIONS_API.md`, `AUTHENTICATION_PLAN_ROLES_API.md`

**RBAC enforcement (core-service):**
- `app/dependencies.py` (`has_permission`, `require_permission`)
- `app/core/authorization.py` (permission code catalog)
- `app/models/warehouse_user.py` (warehouse scoping)

---

## Decision log

- 2026-06-01: Gap analysis produced and reviewed. User to confirm implementation start and chosen phase. **No code changes pending approval.**
