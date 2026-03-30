---
inclusion: always
---

# Backend — QR Block Creation & Excel Download

## Overview

This guide documents the **implemented** FastAPI endpoints in `core-service` for generating
QR code batches (Blocks), polling generation status, and downloading the resulting Excel file.

> All block endpoints live under `/api/v1/qr-products/` — not `/api/v1/blocks/`.

---

## Base URL

```
http://localhost:8001/api/v1/qr-products
```

## Authentication

All endpoints require a Bearer token:

```
Authorization: Bearer {token}
```

Permission required: `qr_product.read` (read) / `qr_product.create` (write)

---

## API Endpoints — Quick Reference

| Method | Path                                      | Permission          | Description                             |
| ------ | ----------------------------------------- | ------------------- | --------------------------------------- |
| POST   | `/qr-products/{product_id}/blocks`        | `qr_product.create` | Generate a new QR block for a product   |
| GET    | `/qr-products/blocks`                     | `qr_product.read`   | List all blocks for the org (paginated) |
| GET    | `/qr-products/{product_id}/blocks`        | `qr_product.read`   | List blocks for a specific product      |
| GET    | `/qr-products/blocks/{block_id}`          | `qr_product.read`   | Get single block detail + status        |
| GET    | `/qr-products/blocks/{block_id}/download` | `qr_product.read`   | Get signed download URL (60 min expiry) |
| GET    | `/qr-products/blocks/{block_id}/items`    | `qr_product.read`   | List ProductItems (serial numbers)      |

> **Route ordering note**: Literal `/blocks` and `/blocks/{block_id}` routes are registered
> before `/{product_id}` routes in the router to prevent FastAPI capturing `"blocks"` as a UUID.

---

## 1. Generate QR Block

**`POST /api/v1/qr-products/{product_id}/blocks`**

Creates a block and synchronously generates all QR codes. On success, `status` is `"completed"`.

### Request Body

```json
{
  "batch": "BATCH-2025-01",
  "quantity": 500,
  "qr_type": "D",
  "serial_prefix": "PROD",
  "sr_number_type": "S8DN",
  "qr_image": false,
  "manufacture_date": "2025-01-01",
  "expiry_date": "2026-01-01"
}
```

| Field              | Type    | Required | Notes                                                         |
| ------------------ | ------- | -------- | ------------------------------------------------------------- |
| `batch`            | string  | yes      | Max 50 chars                                                  |
| `quantity`         | integer | yes      | 1–10,000                                                      |
| `qr_type`          | string  | no       | `D` \| `S` \| `B` \| `O` \| `SC` (default: product's qr_type) |
| `serial_prefix`    | string  | no       | Max 20 chars — prepended to serial numbers                    |
| `sr_number_type`   | string  | no       | `R6DAN` \| `R4DAN` \| `S8DN` \| `S10DN`                       |
| `qr_image`         | boolean | no       | Include QR image column in Excel                              |
| `manufacture_date` | date    | no       | ISO date `YYYY-MM-DD`                                         |
| `expiry_date`      | date    | no       | ISO date `YYYY-MM-DD`                                         |

### Response `201 Created`

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "product_id": "uuid",
  "batch": "BATCH-2025-01",
  "quantity": 500,
  "serial_prefix": "PROD",
  "sr_number_type": "S8DN",
  "status": "completed",
  "task_status": "completed",
  "task_id": null,
  "qr_image": false,
  "manufacture_date": "2025-01-01",
  "expiry_date": "2026-01-01",
  "gcs_url": null,
  "download_url": "https://storage.googleapis.com/...",
  "completed_at": "2025-01-15T10:30:00Z",
  "created_at": "2025-01-15T10:29:55Z"
}
```

### Error Responses

| Code | Detail                                                                                |
| ---- | ------------------------------------------------------------------------------------- |
| 404  | `"QR product not found"`                                                              |
| 422  | `"No credit balance configured"` or `"Insufficient credits: available=X, required=Y"` |

---

## 2. List All Org Blocks

**`GET /api/v1/qr-products/blocks`**

Returns all blocks across all products for the authenticated user's organization.

### Query Parameters

| Param        | Type    | Default | Notes                                                 |
| ------------ | ------- | ------- | ----------------------------------------------------- |
| `page`       | integer | 1       | Min 1                                                 |
| `page_size`  | integer | 20      | 1–100                                                 |
| `status`     | string  | —       | `pending` \| `in_progress` \| `completed` \| `failed` |
| `product_id` | UUID    | —       | Filter to a specific product                          |

### Response `200 OK`

```json
{
  "blocks": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "product_id": "uuid",
      "product_name": "Widget A",
      "batch": "BATCH-2025-01",
      "quantity": 500,
      "serial_prefix": "PROD",
      "sr_number_type": "S8DN",
      "status": "completed",
      "task_status": "completed",
      "task_id": null,
      "qr_image": false,
      "manufacture_date": "2025-01-01",
      "expiry_date": "2026-01-01",
      "gcs_url": null,
      "download_url": "https://storage.googleapis.com/...",
      "completed_at": "2025-01-15T10:30:00Z",
      "created_at": "2025-01-15T10:29:55Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 42,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

> This response includes `product_name` (joined from `qr_products`). The per-product list below does not.

---

## 3. List Blocks for a Product

**`GET /api/v1/qr-products/{product_id}/blocks`**

### Query Parameters

| Param       | Type    | Default |
| ----------- | ------- | ------- |
| `page`      | integer | 1       |
| `page_size` | integer | 20      |

### Response `200 OK`

Same shape as above but without `product_name`, and `blocks` contains `QRBlockResponse` objects.

---

## 4. Get Block Detail (for status polling)

**`GET /api/v1/qr-products/blocks/{block_id}`**

Use this to poll generation status after creating a block.

### Response `200 OK`

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "product_id": "uuid",
  "batch": "BATCH-2025-01",
  "quantity": 500,
  "serial_prefix": "PROD",
  "sr_number_type": "S8DN",
  "status": "in_progress",
  "task_status": "in_progress",
  "task_id": null,
  "qr_image": false,
  "manufacture_date": "2025-01-01",
  "expiry_date": "2026-01-01",
  "gcs_url": null,
  "download_url": null,
  "completed_at": null,
  "created_at": "2025-01-15T10:29:55Z"
}
```

### Status lifecycle

```
pending → in_progress → completed   (download_url is set)
                      → failed      (no credits deducted)
```

### Error Responses

| Code | Detail                 |
| ---- | ---------------------- |
| 404  | `"QR block not found"` |

---

## 5. Get Signed Download URL

**`GET /api/v1/qr-products/blocks/{block_id}/download`**

Returns a V4 signed GCS URL valid for 60 minutes. Call this on every download click — never cache the URL.

### Response `200 OK`

```json
{
  "signed_url": "https://storage.googleapis.com/bucket/path/file.xlsx?X-Goog-Signature=...",
  "expires_at": "2025-01-15T11:30:00Z"
}
```

### Error Responses

| Code | Detail                                       |
| ---- | -------------------------------------------- |
| 404  | `"QR block not found"`                       |
| 404  | `"Download file not available"`              |
| 409  | `"Block is not ready (status: in_progress)"` |

---

## 6. List Block Items (Serial Numbers)

**`GET /api/v1/qr-products/blocks/{block_id}/items`**

### Query Parameters

| Param       | Type    | Default | Max |
| ----------- | ------- | ------- | --- |
| `page`      | integer | 1       | —   |
| `page_size` | integer | 50      | 200 |

### Response `200 OK`

```json
{
  "items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "product_id": "uuid",
      "block_id": "uuid",
      "serial_number": "PROD-00000001",
      "is_verify": false,
      "is_auth": false,
      "is_suspicious": false,
      "qr_deactive": true,
      "scans": 0,
      "scan_date": null,
      "destination_market": null,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "pagination": { ... }
}
```

---

## Block Generation — How It Works

Generation is **synchronous** in the current implementation (no Celery). The endpoint:

1. Validates the product exists and belongs to the org
2. Checks credit balance via `CreditService.check_balance()`
3. Creates the block with `status="pending"`
4. Sets `status="in_progress"`, generates all `ProductItem` rows
5. On success: sets `status="completed"`, `completed_at=now()`, deducts credits
6. On failure: sets `status="failed"` — no credits deducted

The `download_url` is set on the block once the Excel file is uploaded to GCS. If GCS is not configured, the field may be `null` or contain a direct URL.

---

## QR Type Reference

| Code | Name        | Behaviour                                              |
| ---- | ----------- | ------------------------------------------------------ |
| D    | Dynamic     | Unique signed URL per item — standard use case         |
| S    | Static      | All items share one serial; only timestamp varies      |
| B    | Dual        | Two QR codes per item (covert + overt URLs)            |
| O    | One-Time    | `qr_active` set to `false` after first successful scan |
| SC   | Secure Code | Each item gets a 12-char `secret_code`                 |

## Serial Number Type Reference

| Code  | Format        | Example           |
| ----- | ------------- | ----------------- |
| R6DAN | 6-char random | `A3K9F2`          |
| R4DAN | 4-char random | `X7B2`            |
| S8DN  | 8-digit seq   | `PROD-00000001`   |
| S10DN | 10-digit seq  | `PROD-0000000001` |

---

## Frontend Polling Pattern

Poll `GET /api/v1/qr-products/blocks/{block_id}` every 3 seconds until `status` is `completed` or `failed`. After 20 attempts without a terminal status, show a "check back later" message.

```
poll interval: 3000ms
max attempts:  20
terminal:      ["completed", "failed"]
```

---

## Storage Service

`core-service/app/services/storage_service.py`

- Uses `google-cloud-storage` (V4 signed URLs) when `GCS_BUCKET` is configured
- Falls back gracefully if `download_url` is already a full `https://` URL (dev/staging)
- Supports explicit credentials via `GCS_CREDENTIALS_PATH` or Application Default Credentials

---

## Environment Variables

```env
# QR & GCS
QR_DOMAIN=verify.example.com
GCS_BUCKET=your-bucket-name
GCS_CREDENTIALS_PATH=/path/to/service-account.json   # optional — uses ADC if omitted

# Brand key encryption (ECDSA private keys at rest)
BRAND_KEY_ENCRYPTION_SECRET=your-fernet-key
```

---

## Error Reference

| Code | Scenario                 | Detail                                            |
| ---- | ------------------------ | ------------------------------------------------- |
| 404  | Product not found        | `"QR product not found"`                          |
| 404  | Block not found          | `"QR block not found"`                            |
| 404  | Download file missing    | `"Download file not available"`                   |
| 409  | Block not yet completed  | `"Block is not ready (status: {status})"`         |
| 422  | No credit balance record | `"No credit balance configured"`                  |
| 422  | Insufficient credits     | `"Insufficient credits: available=X, required=Y"` |

---

## Do Not

- Do not call `/api/v1/blocks/...` — those paths do not exist; use `/api/v1/qr-products/blocks/...`
- Do not cache signed download URLs — always fetch fresh (they expire in 60 min)
- Do not expose `private_key_encrypted` anywhere in responses
- Do not return raw GCS paths to the frontend — always go through the `/download` endpoint
- Do not skip `organization_id` filtering — all queries are org-scoped via JWT
- Do not allow more than 10,000 QR codes per block request
