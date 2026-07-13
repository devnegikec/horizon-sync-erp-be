# Bin Bulk Add — Mobile App API Guide

> **Endpoint**: `POST /api/v1/bin-stock/bulk-add` > **Auth**: Bearer token (JWT) — requires `STOCK_ENTRY_CREATE` permission

---

## Purpose

Add **multiple items** to a **single bin** in one API call. Instead of calling `POST /bin-stock/add` once per item, you send a single request with an array of items.

---

## Request

### URL

```
POST {{base_url}}/api/v1/bin-stock/bulk-add
```

### Headers

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

### Body

```json
{
  "bin_id": "a1b2c3d4-...",
  "items": [
    {
      "item_id": "e5f6a7b8-...",
      "quantity": 10,
      "batch_number": "BATCH-001"
    },
    {
      "item_id": "c9d0e1f2-...",
      "quantity": 5
    }
  ]
}
```

| Field                  | Type    | Required | Description                                |
| ---------------------- | ------- | -------- | ------------------------------------------ |
| `bin_id`               | UUID    | ✅       | The bin location UUID (must be type `bin`) |
| `items`                | Array   | ✅       | 1–50 item entries                          |
| `items[].item_id`      | UUID    | ✅       | Item UUID to add                           |
| `items[].quantity`     | Decimal | ✅       | Positive quantity                          |
| `items[].batch_number` | String  | ❌       | Optional batch/lot number (max 100 chars)  |

---

## Response

### Success (201 Created)

Each item is processed independently. The response tells you per-item status.

```json
{
  "bin_id": "a1b2c3d4-...",
  "added": 2,
  "errors": 0,
  "items": [
    {
      "item_id": "e5f6a7b8-...",
      "quantity": 10,
      "batch_number": "BATCH-001",
      "status": "added",
      "error": null,
      "bin_stock_level": {
        "id": "11111111-...",
        "organization_id": "22222222-...",
        "bin_location_id": "a1b2c3d4-...",
        "item_id": "e5f6a7b8-...",
        "quantity_on_hand": 10,
        "batch_number": "BATCH-001",
        "created_at": "2026-06-24T10:30:00Z",
        "updated_at": "2026-06-24T10:30:00Z"
      }
    },
    {
      "item_id": "c9d0e1f2-...",
      "quantity": 5,
      "batch_number": null,
      "status": "added",
      "error": null,
      "bin_stock_level": {
        "id": "33333333-...",
        "organization_id": "22222222-...",
        "bin_location_id": "a1b2c3d4-...",
        "item_id": "c9d0e1f2-...",
        "quantity_on_hand": 5,
        "batch_number": null,
        "created_at": "2026-06-24T10:30:00Z",
        "updated_at": "2026-06-24T10:30:00Z"
      }
    }
  ]
}
```

### Partial Failure (201 Created)

If some items fail (e.g., capacity exceeded), the other items still succeed:

```json
{
  "bin_id": "a1b2c3d4-...",
  "added": 1,
  "errors": 1,
  "items": [
    {
      "item_id": "e5f6a7b8-...",
      "quantity": 10,
      "batch_number": null,
      "status": "added",
      "error": null,
      "bin_stock_level": { ... }
    },
    {
      "item_id": "c9d0e1f2-...",
      "quantity": 99999,
      "batch_number": null,
      "status": "error",
      "error": "Cannot add 99999. Available capacity: 50 (total: 100, current: 10)",
      "bin_stock_level": null
    }
  ]
}
```

### Error (4xx / 5xx)

| Status | When                                              |
| ------ | ------------------------------------------------- |
| `400`  | Invalid quantity (≤0), or items array empty / >50 |
| `401`  | Missing or expired token                          |
| `403`  | User lacks `STOCK_ENTRY_CREATE` permission        |
| `404`  | Bin not found                                     |
| `422`  | Validation error (malformed body)                 |

---

## Validation Rules

1. **Bin must be**: active, of type `bin`, and belong to your organization.
2. **Capacity**: Each item's quantity is checked against the bin's **cumulative available capacity** (including items added earlier in the same batch). If the bin has `capacity = 0`, it's treated as unlimited.
3. **Batch uniqueness**: Same `(bin_id, item_id, batch_number)` combination merges quantities — it does NOT create duplicate records.
4. **Maximum 50 items** per request.

---

## Mobile App Usage Example (TypeScript)

```typescript
// api/bin-stock.ts
import apiClient from "./api-client";

interface BulkAddItem {
  item_id: string; // UUID
  quantity: number;
  batch_number?: string;
}

interface BulkAddRequest {
  bin_id: string; // UUID
  items: BulkAddItem[];
}

interface BulkAddItemResult {
  item_id: string;
  quantity: number;
  batch_number: string | null;
  status: "added" | "error";
  error: string | null;
  bin_stock_level: BinStockLevel | null;
}

interface BulkAddResponse {
  bin_id: string;
  added: number;
  errors: number;
  items: BulkAddItemResult[];
}

export async function bulkAddStockToBin(
  binId: string,
  items: BulkAddItem[],
): Promise<BulkAddResponse> {
  const { data } = await apiClient.post<BulkAddResponse>(
    "/bin-stock/bulk-add",
    { bin_id: binId, items },
  );
  return data;
}
```

### Screen Integration (React Native / Flutter)

```typescript
// Example: After scanning a bin QR, the user selects items to put away
async function handlePutAway(binId: string, selectedItems: ScannedItem[]) {
  const items = selectedItems.map((item) => ({
    item_id: item.id,
    quantity: item.qty,
    batch_number: item.batch || undefined,
  }));

  const result = await bulkAddStockToBin(binId, items);

  // Show summary to user
  if (result.errors > 0) {
    const failedItems = result.items.filter((i) => i.status === "error");
    showAlert(
      "Partial Success",
      `${result.added} items added. ${result.errors} failed:\n` +
        failedItems.map((i) => `• ${i.error}`).join("\n"),
    );
  } else {
    showToast(`✅ ${result.added} items added to bin successfully`);
  }
}
```

---

## Related Endpoints (for reference)

| Endpoint                                              | Method | Use Case                                             |
| ----------------------------------------------------- | ------ | ---------------------------------------------------- |
| `/bin-stock/add`                                      | POST   | Add a single item to a bin                           |
| `/bin-stock/remove`                                   | POST   | Remove a single item from a bin                      |
| `/bin-stock/{bin_id}`                                 | GET    | List all stock in a bin                              |
| `/bin-stock/item/{item_id}`                           | GET    | Find which bins contain an item                      |
| `/warehouse-locations/{id}/summary`                   | GET    | Get bin capacity & occupancy info                    |
| `/warehouse-locations/{id}/qr-image`                  | GET    | Get bin QR code image                                |
| `/inbound/receiving-slips/{id}/items/{id}/assign-bin` | POST   | Assign a receiving slip item to a bin (inbound flow) |

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────┐
│  POST /api/v1/bin-stock/bulk-add                    │
│                                                     │
│  Body:                                              │
│  {                                                  │
│    "bin_id": "<UUID>",                              │
│    "items": [                                       │
│      { "item_id": "<UUID>", "quantity": N },        │
│      ... (up to 50)                                 │
│    ]                                                │
│  }                                                  │
│                                                     │
│  Response 201:                                      │
│  {                                                  │
│    "added": N,     // success count                 │
│    "errors": N,    // failure count                 │
│    "items": [...]  // per-item status + error       │
│  }                                                  │
└─────────────────────────────────────────────────────┘
```
