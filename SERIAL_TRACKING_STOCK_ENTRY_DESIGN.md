# Serial-Based Stock Entry: Single Entry, Double Protection

## Problem Recap

Can't create a staging bin. Need stock to enter at EITHER receiving OR put-away (not both). Need to prevent:
- Double-counting (same scanned item entered twice)
- Phantom stock (visible in `stock_levels` but not in any bin)

## Solution: `scanned_item_tracking` Table

Create a new table that tracks each scanned item's lifecycle from receiving through put-away. This serves as the **deduplication key** — stock can only be entered once per scanned item.

### Table Design

```sql
CREATE TABLE scanned_item_tracking (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id     UUID NOT NULL,
    warehouse_id        UUID NOT NULL REFERENCES warehouses_extended(id),

    -- Link to the scan session item that created this
    scan_session_item_id UUID NOT NULL REFERENCES scan_session_items(id),
    qr_identifier       VARCHAR(255) NOT NULL,   -- denormalized for fast lookup

    -- Item details
    item_id             UUID NOT NULL REFERENCES items(id),
    sku                 VARCHAR(100) NOT NULL,
    batch_number        VARCHAR(100),
    quantity            INTEGER NOT NULL,
    packaging_unit_id   UUID REFERENCES item_packaging_units(id),

    -- Receiving context
    receiving_slip_id       UUID REFERENCES receiving_slips(id),
    receiving_slip_item_id  UUID REFERENCES receiving_slip_items(id),

    -- Put-away context
    put_away_list_id    UUID REFERENCES put_away_lists(id),
    put_away_item_id    UUID REFERENCES put_away_list_items(id),
    bin_location_id     UUID REFERENCES warehouse_locations(id),

    -- Lifecycle tracking
    status              VARCHAR(30) NOT NULL DEFAULT 'scanned',
    -- 'scanned' → 'received' → 'binned' (or 'rejected')

    stock_entered       BOOLEAN NOT NULL DEFAULT FALSE,
    -- TRUE = stock has been added to stock_levels + bin_stock_levels
    -- Prevents double entry

    stock_entered_at    TIMESTAMPTZ,
    received_at         TIMESTAMPTZ,
    binned_at           TIMESTAMPTZ,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Prevent double stock entry per scanned item
    CONSTRAINT uq_scan_item UNIQUE (scan_session_item_id)
);

CREATE INDEX idx_sit_status ON scanned_item_tracking(status);
CREATE INDEX idx_sit_item_warehouse ON scanned_item_tracking(item_id, warehouse_id);
CREATE INDEX idx_sit_receiving_slip ON scanned_item_tracking(receiving_slip_id);
CREATE INDEX idx_sit_qr_identifier ON scanned_item_tracking(qr_identifier);
```

### Status Lifecycle

```
scanned ──▶ received ──▶ binned
                │
                ▼
            rejected
```

---

## Flow: How It Works

### Step 1: Scan (Existing — No Change)

```
Worker scans QR → ScanSessionItem created
  - qr_identifier = "RB7FJE"
  - sku = "ITEM-001"
  - raw_quantity = 50
  - batch_number = "BATCH-2025-01"
```

### Step 2: Session End → Receiving Slip Created (Existing)

```
receiving_slip created (status=pending_review)
receiving_slip_items created (aggregated by SKU+batch)
```

### Step 3: Slip Approved → Create Tracking Records (NEW)

```python
# inbound_service.py — _approve_slip() — NEW CODE

for scan_item in session.scan_session_items:
    tracking = ScannedItemTracking(
        scan_session_item_id=scan_item.id,
        qr_identifier=scan_item.qr_identifier,
        item_id=item.id,
        sku=scan_item.sku,
        batch_number=scan_item.batch_number,
        quantity=scan_item.raw_quantity,
        packaging_unit_id=scan_item.packaging_unit_id,
        receiving_slip_id=slip.id,
        receiving_slip_item_id=slip_item.id,
        status='received',
        stock_entered=False,  # ← NO stock entry yet
    )
    db.add(tracking)

# ⚠️ NO BinStockService.add_stock() here
# ⚠️ NO stock_levels update here
```

**What happens:**
- ✅ Tracking records created (audit trail)
- ✅ `status='received'` (items acknowledged)
- ❌ No stock in `stock_levels` yet
- ❌ No stock in `bin_stock_levels` yet
- ✅ Pick-list naturally ignores these (no bins to allocate from)

### Step 4: Put-Away Complete → Enter Stock (NEW)

```python
# put_away_service.py — _complete_item() — MODIFIED

# Find tracking records for this put-away item
trackings = db.query(ScannedItemTracking).filter(
    ScannedItemTracking.receiving_slip_item_id == putaway_item.source_item_id,
    ScannedItemTracking.status == 'received',
    ScannedItemTracking.stock_entered == False,
).all()

for tracking in trackings:
    if not tracking.stock_entered:  # Double-check dedup
        # ENTER STOCK ONCE
        BinStockService.add_stock(
            bin_location_id=putaway_item.bin_location_id,
            item_id=tracking.item_id,
            quantity=tracking.quantity,
            batch_number=tracking.batch_number,
            packaging_unit_id=tracking.packaging_unit_id,
        )
        # Mark as done
        tracking.stock_entered = True
        tracking.stock_entered_at = datetime.now(UTC)
        tracking.bin_location_id = putaway_item.bin_location_id
        tracking.status = 'binned'
        tracking.binned_at = datetime.now(UTC)
```

**What happens:**
- ✅ `BinStockService.add_stock()` → creates `BinStockLevel`
- ✅ `_sync_warehouse_stock()` → updates `stock_levels.quantity_on_hand`
- ✅ `tracking.stock_entered = True` → can never be entered again
- ✅ Pick-list can now find this stock in `BinStockLevel`

---

## Why Only One Stock Entry is Guaranteed

```python
# Protection 1: UNIQUE constraint on scan_session_item_id
# One scan → one tracking record. Can't create duplicates.

# Protection 2: stock_entered flag check
if tracking.stock_entered:
    return  # Already entered, skip

# Protection 3: status check
# Only 'received' items can transition to 'binned'
# 'binned' items are skipped
if tracking.status != 'received':
    return
```

---

## How Pick-List Stays Safe

```python
# pick_list_service.py — resolve_bin_locations()
# Queries BinStockLevel WHERE quantity_on_hand > 0

# Before put-away:
#   BinStockLevel: EMPTY for this item/batch
#   → resolve_bin_locations returns 0 bins
#   → pick-list says "insufficient stock" ✅ SAFE

# After put-away:
#   BinStockLevel: 50 units in Bin-A-01
#   → resolve_bin_locations returns Bin-A-01
#   → pick-list allocates normally ✅ CORRECT
```

The pick-list is **naturally protected** because it queries `BinStockLevel`, which only has entries after put-away. No flags, no filters, no special logic needed.

---

## SmartPickingService Protection

The `suggest_allocation()` method queries `stock_levels.quantity_available`. Since stock isn't in `stock_levels` until put-away, it also won't show up here.

---

## Comparison: Current vs Proposed

| | Current | Proposed (Serial Tracking) |
|---|---|---|
| Stock visible after receiving | ❌ No | ❌ No (same) |
| Stock visible after put-away | ✅ Yes | ✅ Yes |
| Double-entry protection | None (aggregation) | `stock_entered` flag + unique constraint |
| Individual scan traceability | ❌ Lost at slip creation | ✅ Full trace |
| Receiving → Put-away gap | Invisible | Tracked via `status='received'` |
| What's in `stock_levels` during gap | Nothing | Nothing |
| Pick-list safety | ✅ Safe (no BinStockLevel) | ✅ Safe (no BinStockLevel) |
| New table needed | — | `scanned_item_tracking` |

---

## What Happens If...

### ...a worker rejects items during receiving?

```
tracking.status = 'rejected'
tracking.stock_entered = False  # never entered
→ Excluded from put-away generation
→ Never makes it to stock_levels
```

### ...put-away is skipped for an item?

```
tracking.status stays 'received'
tracking.stock_entered stays False
→ Stock never entered
→ Admin can query: "items received but not binned"
SELECT * FROM scanned_item_tracking WHERE status='received';
```

### ...a QR code is scanned in TWO different sessions?

```
Session A: ScanSessionItem(qr_identifier="RB7FJE")
Session B: ScanSessionItem(qr_identifier="RB7FJE")
→ Both valid (unique per session)
→ Both get their own ScannedItemTracking records
→ Both get their own stock_entered=True on put-away
→ CORRECT: two physical items with same QR format
```

---

## Migration Plan

### 1. Create Table
```bash
cd core-service
python -m alembic revision --autogenerate -m "add scanned_item_tracking table"
python -m alembic upgrade head
```

### 2. Add Service Method
```python
# core-service/app/services/scanned_item_tracking_service.py
class ScannedItemTrackingService:
    def create_from_session(self, session, receiving_slip, slip_items_map): ...
    def mark_as_binned(self, putaway_item, bin_location_id): ...
    def get_unbinned_items(self, warehouse_id): ...
```

### 3. Wire Into Inbound Service
```python
# inbound_service.py — after slip approval
ScannedItemTrackingService.create_from_session(session, slip, slip_items_map)
```

### 4. Wire Into Put-Away Service
```python
# put_away_service.py — on item completion
ScannedItemTrackingService.mark_as_binned(putaway_item, bin_location_id)
```

---

## Summary

| Guarantee | How |
|-----------|-----|
| Stock entered only ONCE | `stock_entered` flag + `UNIQUE(scan_session_item_id)` |
| No phantom stock | Stock only enters `stock_levels` at put-away (same as current) |
| Pick-list safety | `BinStockLevel` naturally empty until put-away |
| Individual traceability | Each row links back to `scan_session_item_id` → QR code |
| Receiving dock visibility | `SELECT * WHERE status='received'` — know what's waiting |
