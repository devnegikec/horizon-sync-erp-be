# Parallel Receiving & Put-Away: Dual-Axis Design (Final)

## Problem

Space-constrained warehouse. Workers must receive and put-away simultaneously. Worker A scans at the dock while Worker B bins items — working on **different items** from the same shipment. Stock enters only when **both** receiving approval AND put-away are complete.

---

## Core Concept

A single `scanned_item_tracking` row tracks two **independent axes**. Stock enters only when both axes converge.

```
                 RECEIVING AXIS                       PUT-AWAY AXIS
              ┌──────────────────┐              ┌──────────────────┐
              │  scanned         │              │  pending          │
              │       ↓          │              │       ↓           │
              │  approved        │              │  completed        │
              │  (admin action)  │              │  (worker action)  │
              └────────┬─────────┘              └────────┬──────────┘
                       │                                 │
                       └────────────┬────────────────────┘
                                    ▼
                          ┌─────────────────┐
                          │  STOCK ENTERS   │ ← ONLY when both done
                          │  Pickable       │
                          └─────────────────┘
```

---

## How We Know What Happened to Any Item

Every operation starts by reading the tracking row. The `qr_identifier` uniquely identifies the physical item:

```python
# ── Gate: Can I scan this QR? ──
def can_scan(qr, session_id):
    exists = db.query(Tracking).filter(
        qr_identifier=qr, scan_session_id=session_id
    ).first()
    return not exists  # Already scanned in this session → reject

# ── Gate: Can I put away this item? ──
def can_put_away(qr):
    tracking = db.query(Tracking).filter(qr_identifier=qr).first()
    if not tracking:
        return False, "Not scanned yet"
    if tracking.putaway_status == 'completed':
        return False, "Already put away"
    if tracking.receiving_status == 'rejected':
        return False, "Rejected by admin"
    return True, None

# ── Gate: Can admin approve this? ──
def can_approve(tracking):
    if tracking.receiving_status == 'approved':
        return False, "Already approved"
    if tracking.receiving_status == 'rejected':
        return False, "Already rejected"
    return True, None

# ── Gate: Is stock ready to be picked? ──
def is_pickable(tracking):
    return tracking.stock_entered == True
```

No separate tables. No cross-referencing. One row = one item's complete history.

---

## Database Design

```sql
CREATE TABLE scanned_item_tracking (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id       UUID NOT NULL,
    warehouse_id          UUID NOT NULL REFERENCES warehouses_extended(id),

    -- Scan context
    scan_session_id       UUID NOT NULL REFERENCES scan_sessions(id),
    scan_session_item_id  UUID NOT NULL REFERENCES scan_session_items(id),
    qr_identifier         VARCHAR(255) NOT NULL,       -- links receiving ↔ put-away

    -- Item data (extracted from QR once)
    item_id               UUID NOT NULL REFERENCES items(id),
    sku                   VARCHAR(100) NOT NULL,
    batch_number          VARCHAR(100),
    quantity              INTEGER NOT NULL DEFAULT 1,

    -- ═══ RECEIVING AXIS ═══
    receiving_status      VARCHAR(30) NOT NULL DEFAULT 'scanned',
    receiving_slip_id     UUID REFERENCES receiving_slips(id),
    received_at           TIMESTAMPTZ,
    received_by           UUID,
    rejection_reason      TEXT,

    -- ═══ PUT-AWAY AXIS ═══
    putaway_status        VARCHAR(30) NOT NULL DEFAULT 'pending',
    bin_location_id       UUID REFERENCES warehouse_locations(id),
    putaway_at            TIMESTAMPTZ,
    putaway_by            UUID,

    -- ═══ DERIVED ═══
    stock_entered         BOOLEAN NOT NULL DEFAULT FALSE,
    stock_entered_at      TIMESTAMPTZ,

    -- Metadata
    scanned_by            UUID,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_scan_item UNIQUE (scan_session_item_id)
);

CREATE INDEX idx_tracking_receiving ON scanned_item_tracking(receiving_status, warehouse_id);
CREATE INDEX idx_tracking_putaway   ON scanned_item_tracking(putaway_status, warehouse_id);
CREATE INDEX idx_tracking_stock     ON scanned_item_tracking(stock_entered, warehouse_id) WHERE stock_entered = TRUE;
CREATE INDEX idx_tracking_qr        ON scanned_item_tracking(qr_identifier);
CREATE INDEX idx_tracking_session   ON scanned_item_tracking(scan_session_id);
```

---

## All Possible States

```
receiving   putaway     stock_entered   Meaning
──────────  ─────────   ─────────────   ───────
scanned     pending     false           On dock, not binned, not approved
scanned     completed   false           In bin, awaiting admin approval
approved    pending     false           Approved, waiting for worker to bin
approved    completed   true  ✅        READY — stock entered, pickable
rejected    pending     false           Rejected at dock
rejected    completed   false           Rejected after binning (retrieval needed)
```

---

## Stock Entry: The Convergence Point

```python
def should_enter_stock(tracking) -> bool:
    return (
        tracking.receiving_status == 'approved'
        and tracking.putaway_status == 'completed'
        and not tracking.stock_entered
    )

def try_enter_stock(tracking, db):
    """Called after EVERY state change on either axis. Idempotent."""
    if should_enter_stock(tracking):
        BinStockService.add_stock(
            bin_location_id=tracking.bin_location_id,
            item_id=tracking.item_id,
            quantity=tracking.quantity,
            batch_number=tracking.batch_number,
        )
        tracking.stock_entered = True
        tracking.stock_entered_at = utcnow()
```

---

## API Endpoints

### Scan (creates tracking)

```
POST /api/v1/inbound/sessions/{session_id}/scan
```

```python
def process_scan(session, qr_data, user):
    qr = qr_data.qr  # "RB7FJE"

    # Gate: already scanned?
    if not can_scan(qr, session.id):
        raise ConflictError("QR already scanned in this session")

    tracking = ScannedItemTracking(
        scan_session_id=session.id,
        scan_session_item_id=scan_item.id,
        qr_identifier=qr,
        item_id=item.id,
        sku=item.sku,
        quantity=qr_data.quantity or 1,
        receiving_status='scanned',
        putaway_status='pending',
        stock_entered=False,
        scanned_by=user.id,
    )
    db.add(tracking)
```

### Admin Approves Receiving Slip

```
POST /api/v1/inbound/receiving-slips/{slip_id}/approve
```

```python
def approve_slip(slip_id, user, db):
    trackings = db.query(Tracking).filter(
        Tracking.receiving_slip_id == slip_id,
        Tracking.receiving_status == 'scanned',
    ).all()

    for t in trackings:
        if not can_approve(t):
            continue  # Already approved/rejected — skip
        t.receiving_status = 'approved'
        t.received_at = utcnow()
        t.received_by = user.id
    db.flush()

    # Enter stock for items already binned
    ready = db.query(Tracking).filter(
        Tracking.receiving_slip_id == slip_id,
        Tracking.receiving_status == 'approved',
        Tracking.putaway_status == 'completed',
        Tracking.stock_entered == False,
    ).all()
    for t in ready:
        try_enter_stock(t, db)
    db.commit()
```

### Admin Rejects Item

```
POST /api/v1/inbound/receiving-slips/{slip_id}/reject
```

```python
def reject_slip(slip_id, reason, user, db):
    trackings = db.query(Tracking).filter(
        Tracking.receiving_slip_id == slip_id,
        Tracking.receiving_status == 'scanned',
    ).with_for_update().all()

    for t in trackings:
        t.receiving_status = 'rejected'
        t.rejection_reason = reason

        if t.putaway_status == 'completed':
            # Physically in bin — create retrieval task
            create_retrieval_task(t.bin_location_id, t.qr_identifier, reason)
        # Stock was never entered — no rollback
    db.commit()
```

### Worker Completes Put-Away

```
POST /api/v1/put-away/complete
```

```python
def complete_putaway(qr, bin_id, user, db):
    # Gate: can I put away this?
    ok, err = can_put_away(qr)
    if not ok:
        raise ConflictError(err)

    tracking = db.query(Tracking).filter(
        Tracking.qr_identifier == qr,
    ).with_for_update().first()

    tracking.putaway_status = 'completed'
    tracking.bin_location_id = bin_id
    tracking.putaway_at = utcnow()
    tracking.putaway_by = user.id
    db.flush()

    try_enter_stock(tracking, db)
    db.commit()
```

### Items Available for Put-Away

```
GET /api/v1/put-away/available?warehouse_id={id}
```

```python
def list_available(wh_id, db):
    return db.query(Tracking).filter(
        Tracking.warehouse_id == wh_id,
        Tracking.putaway_status == 'pending',
        Tracking.receiving_status.in_(['scanned', 'approved']),
    ).all()
```

### Pick-List (stock_entered gate)

```python
def resolve_bins(item_id, wh_id, db):
    return db.query(BinStockLevel).join(
        Tracking,
        Tracking.bin_location_id == BinStockLevel.bin_location_id,
    ).filter(
        BinStockLevel.item_id == item_id,
        BinStockLevel.warehouse_id == wh_id,
        Tracking.stock_entered == True,        # ← ONLY gate
        BinStockLevel.quantity_on_hand > 0,
    ).all()
```

---

## Concurrency Model

Three-layer protection:

### Layer 1: Row-Level Locking

Every state-changing operation locks the row:

```python
tracking = db.query(Tracking).filter(qr_identifier=qr).with_for_update().first()
# PostgreSQL: only one transaction holds this lock at a time
# Other transactions wait or get serialization error
```

| Scenario | What Happens |
|---|---|
| Admin approves + Worker bins same item simultaneously | First request acquires lock → updates axis → `try_enter_stock()`. Second waits → sees `stock_entered=True` → skips |
| Two workers try to bin same item | First acquires lock → sets `putaway_status='completed'`. Second gets lock → sees `putaway_status='completed'` → conflict error |
| Admin rejects while worker bins | Whichever acquires lock first wins. Rejected → stock never enters. Binned → reject blocked (would need retrieval) |

### Layer 2: Gate Functions

Every operation validates state before acting:

```
can_scan()      → blocks duplicate QR in same session
can_put_away()  → blocks if not scanned, already binned, or rejected
can_approve()   → blocks if already approved or rejected
should_enter_stock() → blocks unless BOTH axes complete
```

### Layer 3: Database Constraints

```sql
UNIQUE(scan_session_item_id)  -- prevents duplicate tracking rows
```

---

## Independent Process Flows

### Flow A: Admin First, Put-Away Later
```
Scan Item#1 → receiving=scanned, putaway=pending
Approve     → receiving=approved, putaway=pending   [try: NO — putaway pending]
Bin         → receiving=approved, putaway=completed [try: YES ✅]
```

### Flow B: Put-Away First, Admin Later
```
Scan Item#2 → receiving=scanned, putaway=pending
Bin         → receiving=scanned, putaway=completed  [try: NO — not approved]
Approve     → receiving=approved, putaway=completed [try: YES ✅]
```

### Flow C: Separate Items (A scans, B bins different items)
```
A scans Item#1 → receiving=scanned, putaway=pending
B scans Item#2 → receiving=scanned, putaway=pending
B bins Item#2  → receiving=scanned, putaway=completed [try: NO]
...
Admin approves → Item#2: stock enters ✅, Item#1: still pending
B bins Item#1  → stock enters ✅
```

---

## Receiving Slip Reconciliation

```python
def get_slip_summary(slip_id, db):
    return db.query(
        Tracking.receiving_status,
        Tracking.putaway_status,
        Tracking.stock_entered,
        func.count(),
    ).filter(
        Tracking.receiving_slip_id == slip_id,
    ).group_by(
        Tracking.receiving_status,
        Tracking.putaway_status,
        Tracking.stock_entered,
    ).all()
```

**Example output:**

```
Receiving Slip #RS-2026-00123
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
On dock, not binned:            5   scanned + pending
In bin, awaiting approval:      3   scanned + completed
Approved, awaiting bin:         2   approved + pending
Fully complete (in stock):      7   approved + completed ✅
Rejected:                       1   rejected
```

---

## Complexity Summary

| # | Complexity | Severity | Mitigation |
|---|---|---|---|
| 1 | Reject after put-away | Medium | No stock entered → no rollback. Retrieval task |
| 2 | Concurrent completion | Low | `FOR UPDATE` + `stock_entered` guard |
| 3 | Bin change after stock entry | Medium | Stock movement transaction |
| 4 | Slip reconciliation | Medium | 3-axis GROUP BY query |
| 5 | Duplicate QR scan | Low | `UNIQUE` constraint + `can_scan()` gate |
| 6 | Put-away visibility | Low | Simple status filter query |
| 7 | Pick-list safety | Low | Single `stock_entered` boolean gate |
| 8 | Orphaned tracking records | Low | 24h cleanup job |

---

## Comparison

| | Current (Sequential) | Dual-Axis (This Design) |
|---|---|---|
| Put-away wait | Minutes to hours | Seconds (immediate) |
| Dock space | High pressure | Low pressure |
| Receiving → Put-away | Sequential | **Independent, parallel** |
| Stock entry gate | Put-away only | **Both axes complete** |
| Concurrency model | None | 3-layer (lock + gate + constraint) |
| Item state visibility | Lost at aggregation | **Per-item, real-time** |
| Rejection after binning | N/A | Retrieval task |
| Admin approval | Blocks everything | Independent axis |

---

## FAQ / Cross-Questions

### Q1: What's the difference between `scan_session_id`, `scan_session_item_id`, and `qr_identifier`?

Three different levels of identity — all needed:

| Field | What It Identifies | Example |
|---|---|---|
| `scan_session_id` | The scanning session ("shopping cart") | `S-001` |
| `scan_session_item_id` | One scan event within that session (DB row) | `SI-100` |
| `qr_identifier` | The physical QR code on the box | `RB7FJE` |

**Concrete example — Worker A opens a session and scans two items:**

```
Session S-001 created
  Scan #1: QR "RB7FJE" → scan_session_item SI-100
  Scan #2: QR "0OY5XY" → scan_session_item SI-101
  Scan #3: QR "RB7FJE" → REJECTED (already scanned via qr_identifier check)
```

**Why all three?**

| If we only had... | Problem |
|---|---|
| `qr_identifier` alone | Same QR in two sessions → which one? Same QR scanned twice in one session → can't detect duplicate |
| `scan_session_item_id` alone | Worker B during put-away scans QR "RB7FJE" → can't find tracking without knowing SI-100 |
| `scan_session_id` alone | Groups scans but can't identify individual items for put-away lookup |

**The critical bridge: `qr_identifier` is the common key both workers see.**

```
Worker A scans QR "RB7FJE" → tracking(scan_session_item=SI-100, qr="RB7FJE")
Worker B puts away → scans same QR "RB7FJE" → finds tracking WHERE qr='RB7FJE'
```

### Q2: How do you prevent the same QR from being scanned twice in one session?

Two layers:

1. **Application gate**: `can_scan()` checks `WHERE qr_identifier=? AND scan_session_id=?` before inserting
2. **Database constraint**: `UNIQUE(scan_session_item_id)` — each scan event creates exactly one tracking row

Same QR in a different session is allowed (different physical item with same QR format).

### Q3: How does put-away know which tracking record to update?

Worker B scans the same QR "RB7FJE" that Worker A scanned. Lookup:

```python
tracking = db.query(Tracking).filter(
    Tracking.qr_identifier == "RB7FJE",
    Tracking.putaway_status == 'pending',
).first()
```

No need to know the session or scan_item_id — the QR code on the box is the universal key.

### Q4: What if the QR code on the box is damaged or unscannable?

The tracking record has `sku`, `batch_number`, `item_id` extracted at scan time. Worker can look up by these fields:

```python
tracking = db.query(Tracking).filter(
    Tracking.sku == "ITEM-001",
    Tracking.batch_number == "BATCH-2025-01",
    Tracking.putaway_status == 'pending',
).first()
```

### Q5: Can two different sessions scan the same QR identifier?

Yes — that represents two different physical items with the same QR format. Each gets its own tracking row. They're distinguished by `scan_session_item_id`.

### Q6: What happens if a session is abandoned (worker crashes)?

Tracking records stay with `receiving_status='scanned'`, `putaway_status='pending'`. A background cleanup job marks records older than 24 hours without a slip as `abandoned`.

### Q7: How does the system know if an item was "received" vs "put away"?

Single query on the tracking table:

```sql
SELECT receiving_status, putaway_status, stock_entered
FROM scanned_item_tracking
WHERE qr_identifier = 'RB7FJE';

-- Returns one row with both answers:
-- receiving='scanned'  → not yet approved by admin
-- putaway='completed'  → already binned by worker
-- stock_entered=false  → stock NOT entered (receiving not approved yet)
```

### Q8: What if admin rejects an item that's already been put away?

Stock was never entered (both axes weren't complete), so no accounting rollback. The item is physically in the bin — a retrieval task is created:

```python
if tracking.putaway_status == 'completed' and tracking.receiving_status == 'rejected':
    create_retrieval_task(tracking.bin_location_id, tracking.qr_identifier, tracking.rejection_reason)
```

### Q9: Is there a scenario where stock_entered could be set to TRUE incorrectly?

No. `try_enter_stock()` is the ONLY function that sets `stock_entered = True`, and it requires both `receiving_status='approved'` AND `putaway_status='completed'`. Additionally, `FOR UPDATE` locking ensures no two transactions can enter stock for the same tracking row simultaneously.

### Q10: What's the difference between `damaged` and `rejected` flags on receiving slip items?

They serve different purposes in the warehouse workflow:

| | `damaged` | `rejected` |
|---|---|---|
| **Nature** | Observation — physical fact | Decision — explicit action |
| **Set by** | Dock worker via `POST .../flag` endpoint | Dock worker/supervisor via `reject_item()` |
| **When** | During receiving review — item arrived physically damaged (broken, crushed, wet, etc.) | Any time during receiving — wrong product, quality issue, expired, any reason |
| **Has reason?** | Optional `notes` field | `rejection_reason`, `rejected_by`, `rejected_at` — full audit trail |
| **Resolution** | Terminal state — handled outside system (insurance, supplier claim) | **Floating items workflow**: can be `accept`ed (back to `ok`), `return_to_sender`, or `dispose`d |
| **Put-away** | Excluded | Excluded |
| **ASN counting** | Counts as delivered (goods arrived, just damaged) | Counts as delivered (goods arrived, rejected by receiver) |

**Think of it as:** `damaged` = "the box is crushed, nothing we can do" — an observation. `rejected` = "I'm quarantining this item for reason X" — a decision that triggers the floating-items resolution flow.

**API endpoints involved:**

| Flag | Endpoint | Action |
|---|---|---|
| `damaged` | `POST /inbound/slips/{id}/items/{id}/flag` with `{"flag": "damaged"}` | Dock worker flags physical damage |
| `rejected` | `POST /inbound/slips/{id}/items/{id}/reject` with `{"reason": "..."}` | Worker/supervisor rejects with reason |
| Floating resolution | `POST /inbound/floating-items/{id}/resolve` with `{"action": "accept|return_to_sender|dispose"}` | Resolve rejected (floating) item |

### Q11: How are `damaged` and `rejected` items handled during put-away generation?

Both are excluded from put-away lists by `PutAwayService.generate_from_slip()`:

```python
# In put_away_service.py — generate_from_slip()
skipped_damaged: list[str] = []
skipped_rejected: list[str] = []   # separate tracking
skipped_unresolved: list[str] = []

for slip_item in slip.items:
    if slip_item.flag in ("damaged", "rejected"):
        skipped = (
            skipped_damaged if slip_item.flag == "damaged"
            else skipped_rejected
        )
        skipped.append(
            f"{slip_item.sku} (batch: {slip_item.batch_number}, qty: {slip_item.quantity})"
        )
        continue
```

Each category is tracked separately and written to `put_away_list.remarks` as JSON warnings:

```json
{
  "warnings": [
    "Skipped 2 damaged item(s): SKU123 (batch: B1, qty: 5); SKU456 (batch: B2, qty: 3)",
    "Skipped 1 rejected item(s): SKU789 (batch: B3, qty: 1)"
  ]
}
```

This gives full visibility into what was excluded and why — no items silently disappear.
