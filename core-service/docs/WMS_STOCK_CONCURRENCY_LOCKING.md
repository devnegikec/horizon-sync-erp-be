# WMS Stock Concurrency & Locking

> How the outbound (order → pick list → pick → dispatch) flow keeps warehouse
> stock safe under concurrent requests, and the invariants every change to the
> stock layer must respect.

---

## 1. Stock columns and the invariant

`stock_levels` tracks the warehouse-level aggregate per `(item, warehouse, org)`:

| Column | Meaning |
|---|---|
| `quantity_on_hand` | Physical units in the warehouse |
| `quantity_reserved` | Units promised to pick lists / orders |
| `quantity_available` | Units still free to promise |

**Invariant (must always hold):**

```
quantity_available = max(0, quantity_on_hand - quantity_reserved)
```

After any change to `quantity_on_hand` or `quantity_reserved`, `quantity_available`
is recomputed from this formula (never decremented independently in the outbound
reservation path).

> **Caveat:** the stock-reconciliation path computes
> `quantity_available = on_hand - reserved` **without** the `max(0, …)` clamp, so
> after a reconciliation it can be negative when reserved exceeds on-hand. The
> clamped invariant is enforced in the outbound reservation flow only.

---

## 2. Locking mechanism

All stock mutations **in the outbound flow described here** use **pessimistic
row-level locks** — PostgreSQL `SELECT … FOR UPDATE`, expressed in SQLAlchemy as
`.with_for_update()`. Other stock paths (e.g. receipt notes, reconciliation)
update `stock_levels` without row locks and are outside this document's scope.

- It is a **database row lock**, not an in-memory Python lock. FastAPI serves
  many requests concurrently (and possibly across multiple worker processes), so
  a `threading.Lock`/`asyncio.Lock` would not protect cross-process writes.
- A transaction that locks a row blocks other transactions that try to lock the
  same row until the first **commits or rolls back**, after which the waiting
  transaction re-reads the **latest committed** values.
- Locks are held until the transaction ends (typically the end of the request).

### Deadlock note

`FOR UPDATE` does not make lock ordering automatic. Two requests that lock
multiple rows in **different orders** can deadlock (Postgres aborts one). The
stock paths below lock rows in a **consistent order** (item order within a single
transaction) to keep the deadlock window minimal.

---

## 3. Lock sites

| Location | Locked row | Purpose |
|---|---|---|
| `OutboundOrderService.create_pick_lists_from_order` | `stock_levels` | Atomically reserve each line (race fix) |
| `BinStockService._sync_warehouse_stock` | `stock_levels` | Safe read-modify-write of the warehouse aggregate |
| `BinStockService.remove_stock` → `_get_bin_stock_record(for_update=True)` | `bin_stock_levels` | Prevent concurrent double-decrement of bin stock |
| `SalesOrderService._reserve_stock_and_split_items` | `stock_levels` | Reservation on sales-order confirm |
| `SmartPickingService.create_pick_list` / `create_bulk_delivery` | `stock_levels` | Reservation on smart-picking flow |
| `PackingSlipService.dispatch` | `stock_levels` | Single on-hand decrement at dispatch |
| `OutboundService._decrement_stock_levels` | `stock_levels` | Single on-hand decrement (legacy gate dispatch) |
| `BinReservationService.reserve` | `warehouse_locations` | One active worker per bin |

---

## 4. Single-decrement rule (no double decrement)

`quantity_on_hand` is decremented **exactly once** per shipped unit, and only at
**dispatch**:

- **Pick scan** (`PickListService.record_pick_scan`) calls
  `BinStockService.remove_stock(..., sync_warehouse=False)` — it only moves
  **bin-level** stock and marks it `picked`. Physical stock is still in the
  warehouse between pick and dispatch, so warehouse `quantity_on_hand` is **not**
  touched.
- **Dispatch** (`PackingSlipService.dispatch` or `OutboundService._decrement_stock_levels`)
  decrements `quantity_on_hand` and `quantity_reserved`, then recomputes
  `quantity_available`.
- **Cancel** (`PickListService.cancel_pick_list`) calls
  `BinStockService.add_stock(..., sync_warehouse=False)` so the bin add-back does
  **not** re-inflate `quantity_on_hand`, and releases the reservation.

`add_stock` / `remove_stock` both accept `sync_warehouse: bool = True` (keyword-only).
The default keeps inbound / bin-transfer behaviour unchanged; only the pick paths
pass `False`.

---

## 5. Reservation lifecycle (order-driven outbound)

```
Order (confirmed)
   │
   ▼
create_pick_lists_from_order ── lock stock_levels per line ──► reserved += qty
   │                                                           available -= qty
   ▼
pick scan ── remove_stock(sync_warehouse=False) ──► bin stock -= qty, status = picked
   │
   ├── cancel ──► add_stock(sync_warehouse=False) + release reserved
   │
   ▼
dispatch ──► on_hand -= qty, reserved -= qty, available = max(0, on_hand - reserved)
```

Worked example (qty 5, on_hand 10):

| Step | on_hand | reserved | available |
|---|---|---|---|
| Create pick list (reserve) | 10 | 5 | 5 |
| Pick scan | 10 | 5 | 5 |
| **Dispatch** | **5** | 0 | 5 |
| Cancel instead | 10 | 0 | 10 |

---

## 6. Partial-order semantics

- A line is **in stock** when `quantity_available >= qty` (fully fulfillable).
- `create_pick_lists_from_order` reserves only in-stock lines and skips
  out-of-stock lines (`exclude_out_of_stock=True`, the default).
- A pick list is created only when **at least one line** is in stock; if every
  line is out of stock, the service raises `ValidationError` and creates nothing.

---

## 7. Confirm guard & live availability display

`confirm_order` is a **soft check**, not a reservation:

- It rejects confirmation when **no** line is in stock
  (`ValidationError("Cannot confirm order: none of its line items are in stock")`),
  so a fully-unfulfillable order never reaches `confirmed` and the "Create Pick
  List" button never appears for it.
- Partial orders confirm normally; short lines are flagged `out_of_stock`.

Per-line `stock_status` is kept **live** on read so the UI never shows a stale
snapshot during the confirm → pick-list-creation window:

| Read | Refresh |
|---|---|
| `GET /outbound/orders/{id}` | `get_order` → `refresh_stock_status(order, commit=False)` (in-memory, no write) |
| `GET /outbound/orders` | `list_orders` → `selectinload(OutboundOrder.items)` + `refresh_stock_status_batch(orders, commit=False)`; the endpoint counts live in-stock/out-of-stock in Python |

The **authoritative** availability decision remains at `create_pick_lists_from_order`
under `FOR UPDATE` — a line that flips out-of-stock after confirm is still handled
there (partial order / all-out error).

---

## 8. Guardrails for future changes

1. Never write `quantity_on_hand -= qty` outside the dispatch paths.
2. Always lock (`with_for_update()`) before a read-modify-write on a stock row.
3. After touching `quantity_on_hand`/`quantity_reserved`, recompute
   `quantity_available = max(0, on_hand - reserved)`.
4. Keep lock acquisition order consistent within a transaction to avoid
   deadlocks.
5. Keep the bin-level and warehouse-level sync decision explicit via
   `sync_warehouse=`.
