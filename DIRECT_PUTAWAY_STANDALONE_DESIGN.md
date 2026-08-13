# Direct Put-Away (Standalone) — Design

> Status: **Decided — ready for implementation**
> Complements: `DUAL_AXIS_RECEIVING_PUTAWAY_DESIGN.md`

## Goal

Make **Direct Put-Away** a fully standalone flow:

- ❌ No pending put-away list required
- ❌ No prior inbound scan / inbound session required
- ✅ Scanning during Direct Put-Away resolves item detail **exactly like inbound does**, and creates the `scanned_item_tracking` row **on the fly**

This is a repeatable, general flow — not a one-time fix or backfill.

---

## Background / Problem

Today the Direct Put-Away flow depends on a prior inbound scan:

```
Direct Put-Away scan
  → GET /put-away/lookup/{qr}
  → 404 (no tracking row) → item marked "not-found" → cannot assign
```

But the tracking row is currently only created during inbound `record_scan`.
That breaks the dual-axis promise: put-away should be able to stand alone.

---

## Proposed Flow (Direct Put-Away, standalone)

```
1. Scan QR (parent QSeal box → resolve children, or single item)
2. Decode QR            → decode_qr_payload()        (SAME as inbound)
3. Resolve Item         → ProductItem → Item          (SAME fixed resolution as inbound)
4. Upsert tracking row  → if exists for qr_identifier → reuse; else CREATE
5. Assign to bin        → POST /put-away/complete     (existing, unchanged)
```

Steps 2–3 reuse the exact item-detail resolution inbound uses:
`decode_qr_payload` → serial → `ProductItem` → `Item.qr_product_id`
(fallback: `Item.sku` / `Item.gtin` / `Item.item_code`).

---

## Proposed Backend Change

New endpoint that mirrors inbound's scan-side tracking creation, without a session:

```
POST /put-away/scan        (working name — TBD)
Body: { "qr": "<raw QR data or identifier>" }

1. decode_qr_payload(qr)
2. resolve Item (ProductItem → qr_product_id, SKU/GTIN/item_code fallback)
3. SELECT tracking WHERE qr_identifier = payload.id
   - exists   → return it
   - missing  → create tracking row → return it
Returns: TrackingItemResponse
```

Mobile app (`useDirectPutaway`) then treats a successful response as `pending`,
and `POST /put-away/complete` works exactly as it does today.

---

## Decisions (final)

### D1. Receiving-axis status for standalone rows
`receiving_status = 'scanned'` (dual-axis stays intact).
Stock still enters only when BOTH `receiving_status='approved'` AND
`putaway_status='completed'`. Direct put-away alone does not bypass admin approval.

> Note: standalone rows have `receiving_slip_id = NULL`, so they are not caught by
> the slip-level approve endpoint. Admin approval for these rows is handled
> separately (per-row approval) — out of scope for this change.

### D2. `scan_session_id` / `scan_session_item_id`
Make both columns **nullable** (Alembic migration).
- Inbound scans: still populate both (unchanged).
- Standalone put-away: both `NULL`.

### D3. QSeal parent scan
Parent QSeal → resolve children (`getLinkedUnits`) → each child gets its own
tracking row (child-level tracking, same as inbound). The parent serial itself is
not tracked.

### D4. Slip reconciliation
Standalone rows have `receiving_slip_id = NULL` and are excluded from
receiving-slip reconciliation (no slip by definition).

---

## Implementation Checklist

- [ ] Alembic migration: `scan_session_id`, `scan_session_item_id` → nullable
- [ ] `POST /put-away/scan` endpoint (decode → resolve Item → upsert tracking)
- [ ] Service method: `ensure_tracking_from_qr(...)` (reuses inbound's Item resolution)
- [ ] Mobile: `putawayService.scanItem(qr)` calls the new endpoint
- [ ] Mobile: `useDirectPutaway` — on lookup 404, call `scanItem` instead of marking `not-found`
- [ ] Tests: scan → tracking created; re-scan → same row returned; complete → works

---

## Non-Goals

- No backfill of previously scanned items.
- No change to `POST /put-away/complete` semantics.
- No change to the receiving (inbound) axis or admin approval flow.
