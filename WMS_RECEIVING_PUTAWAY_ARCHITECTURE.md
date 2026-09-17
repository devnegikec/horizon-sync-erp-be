# WMS Architecture Analysis: Receiving → Put-Away → Picking

## Current Architecture (How it Works Today)

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SCAN QR    │────▶│  RECEIVING   │────▶│   PUT-AWAY   │────▶│ STOCK IN     │
│   (Mobile)   │     │  SLIP        │     │   LIST       │     │ BIN + SYNC   │
│              │     │  (pending)   │     │  (pending)   │     │ WAREHOUSE    │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                            │                     │                    │
                            ▼                     ▼                    ▼
                     status=pending_        status=pending      BinStockService
                     putaway                items→complete      .add_stock()
                                                                     │
                                                                     ▼
                                                            _sync_warehouse_stock()
                                                            stock_levels.quantity_
                                                            on_hand += qty ✅
```

**Key point**: Stock becomes visible at BOTH bin-level AND warehouse-level ONLY after put-away completion. Before that, the stock exists only as a `ReceivingSlipItem` — not in any `stock_levels` or `bin_stock_levels` table.

---

## Proposed Change: Stock Entry at Receiving, Bin Linking at Put-Away

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SCAN QR    │────▶│  RECEIVING   │────▶│   PUT-AWAY   │────▶│ BIN LINKED  │
│   (Mobile)   │     │  SLIP        │     │   LIST       │     │ (location    │
│              │     │  (pending)   │     │  (pending)   │     │  added to    │
└──────────────┘     └──────┬───────┘     └──────────────┘     │  stock)      │
                            │                                    └──────────────┘
                            ▼
                     STOCK ENTERED HERE
                     (warehouse-level only,
                      NO bin location)
                     stock_levels.on_hand += qty
```

---

## 🚨 Problem Analysis

### Problem 1: "Phantom Stock" — Visible but Not Locatable

Stock is at warehouse-level (`stock_levels.quantity_on_hand > 0`) but has **zero bin-level entries** (`bin_stock_levels.quantity_on_hand = 0`).

**Impact on Picking:**
```python
# pick_list_service.py — resolve_bin_locations()
BinStockLevel.query.filter(
    BinStockLevel.item_id == item_id,
    BinStockLevel.quantity_on_hand > 0  # ← STOCK NOT HERE YET
).order_by(expiry_date_asc, created_at_asc)
```
→ Returns **empty result set** for items received but not yet put away.

**Result**: Pick-list generation fails with "insufficient stock" even though `stock_levels` shows stock available. Workers see stock exists but can't pick it.

---

### Problem 2: FIFO/FEFO Breakdown

The FIFO rotation logic relies on `BinStockLevel` timestamps:

```python
# pick_list_service.py line 281-289
.order_by(
    BinStockLevel.expiry_date.asc().nulls_last(),  # FEFO
    BinStockLevel.created_at.asc()                  # FIFO
)
```

If stock sits in "receiving limbo" (warehouse-level only, no bin entry), then:
- The `created_at` timestamp for that stock doesn't exist in `bin_stock_levels`
- **Older stock in bins gets picked first** (correct FIFO)
- But stock that arrived **earlier and is still on the dock** gets bypassed entirely

| Scenario | Bin A (old stock) | Receiving Dock (new stock) | What Happens |
|----------|-------------------|---------------------------|--------------|
| Both in bins | Picked first (FIFO) | Picked second | ✅ Correct |
| New stock not binned | Picked first | **Not found** | ❌ FIFO violated for subsequent batches |

---

### Problem 3: Concurrent Picking During Put-Away — The "Race Condition"

```
Time ──────────────────────────────────────────────────▶

Worker-A (Put-Away):  [─── carrying stock to Bin-X ───][scan bin][confirm]
Worker-B (Pick-List):  [─── walks to Bin-X to pick ───][  FINDS EMPTY BIN  ]
```

**What happens:**
1. Warehouse-level stock shows 10 units available
2. Pick-list allocates 5 units from Bin-X (because `BinStockLevel` may not yet reflect the incoming put-away)
3. Worker-A arrives at Bin-X with new stock → places it
4. Worker-B arrives at Bin-X to pick → stock might exist or might not, depending on timing
5. If Worker-B arrives **before** Worker-A confirms, bin is empty → "stock not found" error

**Current protection (inadequate for this scenario):**
- `BinReservationService` prevents two workers from being assigned the **same bin** simultaneously
- But it doesn't prevent a picker from being sent to a bin that's about to receive stock but hasn't yet

---

### Problem 4: Inventory Accuracy — "Dock Stock" Pile-Up

Without bin location, there's no way to know WHERE the stock physically is:

| Data Point | Receiving Complete | Put-Away Complete |
|-----------|-------------------|-------------------|
| `stock_levels.quantity_on_hand` | +100 ✅ | +100 ✅ |
| `bin_stock_levels.quantity_on_hand` | 0 ❌ | +100 ✅ |
| Physical location known | No ❌ | Yes (Bin-X) ✅ |

If put-away is delayed (worker shift change, break, forgot), stock accumulates on the dock with no location trace. This creates:
- **Shrinkage risk** — stock exists on paper but can't be found
- **Re-order risk** — system shows stock available, procurement doesn't re-order, but stock is physically inaccessible
- **Audit nightmare** — cycle counting finds discrepancies with no way to reconcile

---

### Problem 5: Stock Reservation Double-Counting

In the smart picking flow (`SmartPickingService`), stock is reserved at warehouse level:

```python
# smart_picking_service.py — create_pick_list()
stock_level.quantity_reserved += qty
stock_level.quantity_available = quantity_on_hand - quantity_reserved
```

If warehouse-level stock includes "dock stock" (not yet binned), then:
- `quantity_available` includes stock that can't be physically picked
- A pick-list reserves 10 units → system says "5 available" → but those 5 are still on the dock
- Next pick-list sees "5 available" and tries to allocate → fails at bin resolution

---

## 🏭 How Real WMS Systems Handle This

### Tier 1: SAP EWM / Oracle WMS / Manhattan Associates

**Standard pattern: Storage Type with Availability Group**

```
┌──────────────────────────────────────────────────┐
│  Storage Types (Location Zones)                   │
│                                                   │
│  9010 - RECEIVING DOCK  (not available for pick)  │
│  9020 - QUALITY CHECK   (not available for pick)  │
│  0050 - BULK STORAGE    (available for pick)      │
│  0010 - PICK FACE       (available for pick)      │
└──────────────────────────────────────────────────┘
```

- Stock is **booked into receiving zone** (9010) immediately upon goods receipt
- Receiving zone stock is tracked but **NOT included in ATP (Available-to-Promise)** calculations
- Only after **put-away confirmation** (move from 9010 → 0050) does stock become "available for picking"
- This is done via **storage type availability groups** — a config flag that marks which zones contribute to ATP

### Tier 2: Fishbowl / Zoho Inventory / Odoo WMS

**Standard pattern: Staging Locations**

```
Location: "RECV-DOCK"     → type=receiving, pickable=false
Location: "QA-HOLD"        → type=quality,   pickable=false
Location: "BIN-A-01"       → type=storage,   pickable=true
Location: "BIN-B-02"       → type=storage,   pickable=true
```

- Receiving dock is a **special bin/location** with `is_pickable=False`
- Stock enters this bin on receipt, then transferred to storage bins during put-away
- Pick-list queries only `is_pickable=True` locations
- Simpler than SAP but same concept: receiving stock ≠ pickable stock

### Common Pattern Across All WMS

```
                       ┌──────────────────┐
GOODS RECEIPT ────────▶│ RECEIVING STAGE   │  stock = "on hand" but NOT "available"
                       │ (non-pickable)   │
                       └────────┬─────────┘
                                │ PUT-AWAY CONFIRMATION
                                ▼
                       ┌──────────────────┐
                       │ STORAGE BIN      │  stock = "on hand" AND "available"
                       │ (pickable)       │
                       └──────────────────┘
```

---

## ✅ Recommended Approach for This Project

### Option A: Add Receiving Stage Bin (Quick Fix)

Create a concept of "staging location" and mark it non-pickable:

1. Add field `is_pickable` (default=True) to `warehouse_locations`
2. Create a "RECEIVING-STAGE" bin per warehouse with `is_pickable=False`
3. On receiving completion: add stock to `RECEIVING-STAGE` bin → syncs to warehouse-level
4. On put-away completion: **transfer** stock from `RECEIVING-STAGE` → target bin
5. Pick-list query: filter `BinStockLevel WHERE bin.is_pickable = True`

```python
# Simplified flow
# Receiving complete:
BinStockService.add_stock(
    bin_location_id=receiving_stage_bin.id,  # staging bin
    item_id=item.id,
    quantity=received_qty,
    batch_number=batch,
)

# Put-away complete:
BinStockService.transfer_stock(
    from_bin=receiving_stage_bin.id,
    to_bin=target_bin.id,
    item_id=item.id,
    quantity=putaway_qty,
)
```

### Option B: Separate "On Hand" vs "Available" (More Robust)

1. Keep current flow (stock only after put-away) but add warehouse-level tracking in receiving
2. Add `quantity_in_receiving` to `stock_levels`
3. `quantity_available = quantity_on_hand - quantity_reserved - quantity_in_receiving`
4. Pick-list only considers `quantity_available > 0`
5. Put-away converts `quantity_in_receiving` → `quantity_on_hand` at bin level

---

## 📊 Comparison Summary

| Approach | Stock Visible After Receiving | Pickable Before Put-Away | Complexity | Risk |
|----------|------------------------------|--------------------------|------------|------|
| **Current** (stock only after put-away) | ❌ No | ❌ No | Low | Safe but slow — stock invisible until binned |
| **Proposed** (stock at receiving, bin at put-away) | ✅ Yes (warehouse only) | ⚠️ Attempted but fails | Medium | **HIGH** — phantom stock, FIFO violation, race conditions |
| **Option A** (staging bin + is_pickable flag) | ✅ Yes (staging bin) | ❌ No (staging bin excluded) | Medium | Low — industry standard approach |
| **Option B** (separate available vs in-receiving) | ✅ Yes (receiving column) | ❌ No (formula excludes) | High | Low — most flexible |

---

## 🎯 Recommendation

**Go with Option A** (staging bin + `is_pickable` flag). It's the industry standard, minimal code change, and prevents all the problems listed above while still giving visibility into received-but-not-binned stock.
