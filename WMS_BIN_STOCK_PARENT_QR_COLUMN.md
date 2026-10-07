# WMS Bin Stock — Parent QR Code Column

Feature: in the WMS bin-stock dialog (**Manage → Location Tree → Action → view**),
show a scannable **parent (master-pack) QR code** column for each batch.
The column is configurable via a feature flag and is **hidden by default**.

## Status

| Item | State |
|------|-------|
| Feature flag row (`bin_stock_show_parent_qr`) | ✅ Present in `core_db` (GLOBAL, `enabled=false`, `visible=true`) |
| Alembic migration | ✅ Applied — `core_alembic_version` contains `135_add_bin_stock_parent_qr_flag` |
| Default behavior | Column hidden (flag disabled) |

## Feature flag

- **Name:** `bin_stock_show_parent_qr`
- **Constant:** `BIN_STOCK_SHOW_PARENT_QR` in `core-service/app/core/constants.py`
- **Default:** disabled (hidden)
- **Scope resolution:** TENANT override first, then GLOBAL; `false` when missing.

Enable/disable:

```http
# Tenant override (Settings → Feature Flags also works)
PUT /api/v1/feature-flags/bin_stock_show_parent_qr
{ "enabled": true }

# Evaluate for the current user/org (used by the frontend)
GET /api/v1/feature-flags/evaluate/bin_stock_show_parent_qr
```

## Backend changes

| File | Change |
|------|--------|
| `core-service/app/core/constants.py` | Added `BIN_STOCK_SHOW_PARENT_QR` constant. |
| `core-service/app/schemas/bin_stock.py` | Added `parent_qr_code_url` to `BinStockLevelResponse` and `BinStockGroupItem`; added `qr_code_url` to `BinStockParentQSealInfo`. |
| `core-service/app/services/bin_stock_service.py` | Added `_show_parent_qr_column()`, `_build_parent_qr_url()`, `get_parent_qr_map()`; `get_parent_boxes()` now emits the QR fields when the flag is on. |
| `core-service/app/api/v1/endpoints/bin_stock.py` | `GET /bin-stock/{bin_id}` now populates `parent_qr_code_url` per stock level. |
| `core-service/alembic/versions/135_add_bin_stock_parent_qr_flag.py` | Seeds the GLOBAL flag (`enabled=false`), idempotent. |

QR URL format (matches the existing QSeal Excel export convention):

```
{QR_BASE_URL}/qseal/{parent_serial}
```

- Uses `settings.qr_base_url` when set, else `https://{settings.qr_domain}`.
- Example: `https://pollux.ciphercode.ai/qseal/QSLP1`.

## API contract

`GET /api/v1/bin-stock/{bin_id}/parents`

```jsonc
{
  "bin_id": "...",
  "total_parent_boxes": 1,
  "groups": [
    {
      "parent_qseal": {
        "id": "...",
        "serial_number": "QSLP1",
        "name": "Pallet",
        "qseal_type": "shipper",
        "capacity": 10,
        "qr_code_url": "https://pollux.ciphercode.ai/qseal/QSLP1"  // null when flag off
      },
      "product_name": "...",
      "items": [
        {
          "id": "...",
          "batch_number": "BATCH-A",
          "serial_number": "CHILD001",
          "parent_qr_code_url": "https://pollux.ciphercode.ai/qseal/QSLP1",  // null when flag off
          "...": "..."
        }
      ]
    }
  ]
}
```

`GET /api/v1/bin-stock/{bin_id}`

```jsonc
{
  "bin_stock_levels": [
    {
      "id": "...",
      "batch_number": "CHILD001",
      "parent_qr_code_url": "https://pollux.ciphercode.ai/qseal/QSLP1",  // null when flag off
      "...": "..."
    }
  ]
}
```

When the flag is off, all new QR fields are `null`.

## Frontend integration notes

1. Evaluate the flag when the bin-stock dialog opens:

   ```
   GET /api/v1/feature-flags/evaluate/bin_stock_show_parent_qr
   → { "feature_name": "bin_stock_show_parent_qr", "enabled": true|false, "visible": true }
   ```

2. If `enabled === true`, render a **Parent QR** column; otherwise hide it (default).
   The backend also returns `null` for the fields when disabled, so the column is
   empty/safe even without evaluating the flag.

3. Render the QR client-side from the URL value (already scannable, no encoding needed):

   ```tsx
   {row.parent_qr_code_url && <QRCode value={row.parent_qr_code_url} size={64} />}
   ```

## Validation

- `py_compile` on all changed files — passed.
- Import checks for the modified schema/service/endpoint/constants modules — passed.
- Standalone SQLite functional test:
  - flag off → QR fields `null`, `get_parent_qr_map()` returns `{}`;
  - flag on → correct QR URL on `parent_qseal`, batch items, and the stock-level map.
- Migration confirmed applied to `core_db` (flag row present + revision recorded).
