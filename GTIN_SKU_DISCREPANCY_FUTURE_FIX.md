# GTIN vs SKU discrepancy — future fix

> Status: **Band-aids applied, root fix pending.**
> Do **not** treat GTIN as equal to SKU long-term. This document captures the
> underlying data-model issue and the recommended proper fix.

## Problem

The QR codes generated for products encode the **GTIN** (e.g. `9283975768`) in
the decoded payload's `sku` field. That raw value flows straight through the
inbound pipeline and is stored as the "sku":

- `scan_session_items.sku`
- `received` → `receiving_slip_items.sku`
- `scanned_item_tracking.sku` (falls back to `item.sku or item.item_code or payload.sku`)

Meanwhile the real identity lives on `items`:

| field | example (`ITM-2026-00015`) |
|---|---|
| `item_code` | `ITM-2026-00015` |
| `sku` | `PTK-COOK-I009` |
| `gtin` | `9283975768` |

So the slip stores `9283975768` where the resolver expects `PTK-COOK-I009` or
`ITM-2026-00015`. Every downstream resolver that matches on the slip's `sku`
column therefore has to "guess" by trying `item_code`, `sku`, **and** `gtin`.

## Symptoms already observed

1. `generate_from_slip` (put-away) → `Skipped N item(s) with unknown SKU (no matching Item found)` and an empty put-away list in the mobile app.
2. `_sync_asn_delivered_qty` → ASN never advanced from `confirmed` to `delivered`.
3. `_create_receiving_stock_entry` → line items unresolved, no `material_receipt` lines.

## Band-aids currently in place (equating GTIN with SKU)

| file | method | matching |
|---|---|---|
| `services/inbound_service.py` | `record_scan` | `Item.sku / Item.gtin / Item.item_code == payload.sku` |
| `services/inbound_service.py` | `_sync_asn_delivered_qty` | `item.sku, item.item_code, item.gtin` |
| `services/inbound_service.py` | `_create_receiving_stock_entry` | `Item.item_code | Item.sku | Item.gtin == slip_item.sku` |
| `services/put_away_service.py` | `generate_from_slip` | `Item.item_code | Item.sku | Item.gtin == slip_item.sku` |

These work but are fragile: they re-parse the same identifier at every hop and
break if a GTIN happens to collide with another item's SKU/code.

## Recommended proper fix (future)

Resolve the `Item` **once**, at scan time, and store the resolved reference on
the rows that flow downstream. Then match by `item_id` everywhere.

### 1. Persist the resolved item at scan time

`record_scan` already resolves `item` (for `scanned_item_tracking`). Also store:

- `scan_session_items.item_id` (nullable FK → `items.id`)
- `scan_session_items.sku` = **canonical** `item.sku or item.item_code` (not the raw GTIN)

### 2. Propagate to the receiving slip

`_generate_receiving_slip` groups scan items; store the resolved `item_id` (and
canonical `sku`) on `receiving_slip_items`.

### 3. Switch downstream resolvers to `item_id`

- `put_away_service.generate_from_slip` → resolve by `receiving_slip_items.item_id`
  (keep identifier fallback only as a last resort).
- `inbound_service._sync_asn_delivered_qty` → aggregate delivered qty by `item_id`.
- `inbound_service._create_receiving_stock_entry` → use `receiving_slip_items.item_id`.

### 4. Schema migration

```sql
ALTER TABLE scan_session_items ADD COLUMN item_id UUID REFERENCES items(id);
ALTER TABLE receiving_slip_items ADD COLUMN item_id UUID REFERENCES items(id);
-- backfill existing rows by matching sku against items.sku / items.gtin / items.item_code
```

### 5. Optional: fix the QR source

If product QRs can be regenerated to carry the canonical SKU (or a stable item
identifier) instead of the GTIN, the raw-value problem disappears at the source.
