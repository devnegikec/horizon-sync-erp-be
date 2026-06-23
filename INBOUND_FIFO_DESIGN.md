# Inbound Receive-to-Bin & FIFO Picking — Design

> **Date**: 2026-06-22
> **Status**: Design Phase

---

## Part A: Two-Step Inbound (Receive → Assign Bin)

### Current Flow (3-step, put-away list based)

```
Worker scans items → Receiving Slip (PENDING)
  → Admin approves slip
  → System generates Put-Away List with bin assignments
  → Worker picks from put-away list → confirms bin
  → Stock added to bin
```

### Proposed Flow (2-step, receiving slip based)

```
Worker scans items → Receiving Slip (PENDING_PUTAWAY)
  → Worker scans bin QR → confirms quantity
  → ReceivingSlipItem updated: bin_location_id, status=put_away
  → Stock added to bin via BinStockService
  → When ALL items are put_away → Slip status → PUTAWAY_COMPLETE
```

### Why This is Better

| Current | Proposed |
|---------|----------|
| 3 steps (slip → approve → put-away list → bin) | 2 steps (slip → bin) |
| Requires admin approval before put-away | Worker can put-away immediately |
| Separate PutAwayList table | ReceivingSlipItem tracks bin directly |
| QR is unique per box → each scan is unique | Worker scans item QR → places in bin → confirms |

---

### DB Changes (ReceivingSlipItem)

Add columns to `receiving_slip_items`:

```sql
ALTER TABLE receiving_slip_items ADD COLUMN bin_location_id UUID REFERENCES warehouse_locations(id);
ALTER TABLE receiving_slip_items ADD COLUMN put_away_status VARCHAR(20) DEFAULT 'pending';
-- pending | completed
ALTER TABLE receiving_slip_items ADD COLUMN put_away_at TIMESTAMPTZ;
ALTER TABLE receiving_slip_items ADD COLUMN put_away_by UUID;
```

### Schema Changes

```python
# core-service/app/schemas/inbound.py

class AssignBinRequest(BaseModel):
    """Assign a bin to a receiving slip item (put-away step)"""
    slip_item_id: UUID          # ReceivingSlipItem ID
    bin_location_id: UUID       # Scanned bin QR location_id
    quantity: int               # Quantity to put in this bin (may be partial)
```

### New Endpoint

```
POST /api/v1/inbound/receiving-slips/{slip_id}/items/{item_id}/assign-bin
Authorization: Bearer <token>

Body:
{
  "bin_location_id": "<scanned-bin-uuid>",
  "quantity": 50
}

Response 200:
{
  "slip_item_id": "...",
  "sku": "SVACHH-SS-POP-2L",
  "bin_location_id": "...",
  "bin_full_path": "Z01-A01-B01-L01-BN001",
  "put_away_status": "completed",
  "put_away_at": "2026-06-22T10:00:00Z"
}
```

### Endpoint Logic

```python
async def assign_bin_to_slip_item(slip_id, item_id, body, current_user, db):
    # 1. Look up ReceivingSlipItem
    item = db.query(ReceivingSlipItem).filter(
        ReceivingSlipItem.id == item_id,
        ReceivingSlipItem.slip_id == slip_id,
    ).first()
    
    # 2. Validate bin exists, is active, type='bin'
    bin_location = validate_bin(body.bin_location_id)
    
    # 3. Add stock to bin via BinStockService
    bin_stock_service.add_stock(
        bin_id=body.bin_location_id,
        item_id=resolved_item_id,
        quantity=body.quantity,
        org_id=current_user.organization_id,
        batch_number=item.batch_number,
    )
    
    # 4. Update ReceivingSlipItem
    item.bin_location_id = body.bin_location_id
    item.put_away_status = "completed"
    item.put_away_at = datetime.now(UTC)
    item.put_away_by = current_user.id
    
    # 5. Check if ALL items on slip are completed
    pending = db.query(ReceivingSlipItem).filter(
        ReceivingSlipItem.slip_id == slip_id,
        ReceivingSlipItem.put_away_status == "pending",
        ReceivingSlipItem.flag == "ok",
    ).count()
    
    if pending == 0:
        slip.status = "putaway_complete"
    
    db.commit()
    return item
```

### Mobile App Flow

```
1. Worker starts scan session → POST /inbound/sessions
2. Worker scans item QR → POST /inbound/sessions/{id}/scan (each box)
3. Worker ends session → POST /inbound/sessions/{id}/end
   → Returns receiving slip with items
4. For each item in slip:
   a. Worker scans bin QR → decodes location_id
   b. Worker confirms quantity
   c. POST /inbound/receiving-slips/{slip_id}/items/{item_id}/assign-bin
   d. Item marked as put_away + stock added to bin
5. All items done → slip auto-completes
```

---

## Part B: FIFO-Based Picking (Outbound)

### What FIFO Means Here

When a pick list is created, items should be picked from bins in order of **oldest stock first** (First In, First Out). This is tracked by `created_at` on `BinStockLevel`.

### BinStockLevel Model (existing)

```
bin_stock_levels:
  id, bin_location_id, item_id, quantity_on_hand, batch_number, created_at

Warehouse Locations:
  id, full_path (e.g., Z01-A01-B01-L01-BN001)
```

### FIFO Picking Logic

```
For a pick list item with SKU=X, quantity=Q:

1. Query all bins containing SKU=X with quantity > 0
2. Sort by bin_stock_levels.created_at ASC (oldest first)
3. Allocate quantity Q across bins in FIFO order:
   Bin 1 (created Jan 1): 30 available → pick 30
   Bin 2 (created Jan 15): 20 available → pick 20 (total 50 = Q)
   Remaining in Bin 2: 0
```

### API Design

```
GET /api/v1/pick-lists/{pick_list_id}/suggest-bins
Authorization: Bearer <token>

Response 200:
{
  "pick_list_id": "...",
  "items": [
    {
      "pick_item_id": "...",
      "sku": "SVACHH-SS-POP-2L",
      "quantity_needed": 50,
      "suggested_bins": [
        {
          "bin_id": "...",
          "bin_path": "Z01-A01-B01-L01-BN001",
          "batch_number": "BATCH-2025-01",
          "available_qty": 30,
          "pick_qty": 30,
          "stock_age_days": 172
        },
        {
          "bin_id": "...",
          "bin_path": "Z01-A01-B01-L01-BN002",
          "batch_number": "BATCH-2025-02",
          "available_qty": 20,
          "pick_qty": 20,
          "stock_age_days": 158
        }
      ],
      "total_available": 50,
      "fully_covered": true
    }
  ]
}
```

### Service Method

```python
# core-service/app/services/pick_list_service.py

def suggest_bins_fifo(self, pick_list_id: UUID, org_id: UUID) -> list[dict]:
    """For each item in the pick list, suggest bins in FIFO order."""
    pick_list = self.get_by_id(pick_list_id, org_id)
    results = []
    
    for item in pick_list.items:
        needed = item.quantity
        allocations = []
        total_available = 0
        
        # Find bins with this item, ordered by stock age (oldest first)
        bins = (
            self.db.query(BinStockLevel, WarehouseLocation)
            .join(WarehouseLocation, BinStockLevel.bin_location_id == WarehouseLocation.id)
            .filter(
                BinStockLevel.item_id == item.item_id,
                BinStockLevel.organization_id == org_id,
                BinStockLevel.quantity_on_hand > 0,
                BinStockLevel.batch_number == item.batch_number,  # match batch if set
            )
            .order_by(BinStockLevel.created_at.asc())  # FIFO: oldest first
            .all()
        )
        
        for stock, location in bins:
            if needed <= 0:
                break
            available = int(stock.quantity_on_hand)
            pick_qty = min(available, needed)
            total_available += available
            age_days = (datetime.now(UTC) - stock.created_at).days
            
            allocations.append({
                "bin_id": str(stock.bin_location_id),
                "bin_path": location.full_path,
                "batch_number": stock.batch_number,
                "available_qty": available,
                "pick_qty": pick_qty,
                "stock_age_days": age_days,
            })
            needed -= pick_qty
        
        results.append({
            "pick_item_id": str(item.id),
            "sku": item.sku,
            "quantity_needed": int(item.quantity),
            "suggested_bins": allocations,
            "total_available": total_available,
            "fully_covered": needed <= 0,
            "shortfall": max(0, needed),
        })
    
    return results
```

### Mobile App Flow (Picking)

```
1. Worker views pick list → GET /pick-lists/{id}
2. Worker taps "Suggest Bins" → GET /pick-lists/{id}/suggest-bins
   → Returns bin-by-bin FIFO breakdown
3. Worker goes to first suggested bin:
   a. Scans bin QR → confirms location
   b. Picks quantity shown
   c. Confirms pick → POST /pick-lists/{id}/items/{item_id}/pick
4. Repeat for next bin until quantity filled
5. All items picked → pick list complete
```

---

## Implementation Order

| Phase | Feature | Effort |
|-------|---------|--------|
| **Phase 1** | Add columns to `receiving_slip_items` (bin_location_id, put_away_status) | 1 migration |
| **Phase 2** | `POST /receiving-slips/{slip_id}/items/{item_id}/assign-bin` endpoint | 1 endpoint + service |
| **Phase 3** | Update mobile app: after scan session, show slip items, scan bin, assign | Mobile app |
| **Phase 4** | FIFO suggest-bins endpoint | 1 endpoint + service method |
| **Phase 5** | Mobile app: FIFO pick flow with suggested bins | Mobile app |

---

## Summary

| Feature | What Changes |
|---------|-------------|
| **Two-step inbound** | `ReceivingSlipItem` gets `bin_location_id` + `put_away_status`. New `assign-bin` endpoint adds stock + updates item. No more put-away list needed for simple flow. |
| **FIFO picking** | New `/suggest-bins` endpoint returns bins sorted by `BinStockLevel.created_at` ASC. Worker picks oldest stock first. |
