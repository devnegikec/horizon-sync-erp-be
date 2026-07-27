# Frontend Integration Guide — QR Verification & Landing Pages

> **Backend Base URL (production):** `https://core-service-production-66e9.up.railway.app` > **Last updated:** 2026-07-27

---

## Table of Contents

1. [Overview](#overview)
2. [1. QR Code URL Format](#1-qr-code-url-format)
3. [2. Landing Page Config API (Admin Dashboard)](#2-landing-page-config-api-admin-dashboard)
4. [3. Landing Page Config API (Consumer QR Page)](#3-landing-page-config-api-consumer-qr-page)
5. [4. Scan Analytics Ingestion](#4-scan-analytics-ingestion)
6. [5. Image Upload](#5-image-upload)
7. [6. Complete Consumer QR Page Flow](#6-complete-consumer-qr-page-flow)
8. [7. Permissions](#7-permissions)

---

## Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                    QR Verification System                           │
├────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Admin Dashboard (Auth Required)                                    │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  /api/v1/products/{id}/landing-page          CRUD        │       │
│  │  /api/v1/products/{id}/landing-page/upload-image  Upload │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
│  Consumer QR Page (Public — No Auth)                                │
│  ┌─────────────────────────────────────────────────────────┐       │
│  │  GET /api/v1/public/products/{id}/landing-page  Fetch    │       │
│  │  POST /api/v1/analytics/scans/ingest             Record  │       │
│  └─────────────────────────────────────────────────────────┘       │
│                                                                     │
└────────────────────────────────────────────────────────────────────┘
```

---

## 1. QR Code URL Format

Each product QR code resolves to a URL in this format:

```
{QR_BASE_URL}/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}
```

**Current production value:** `QR_BASE_URL = https://v0-horizon-sync.vercel.app`

**Example:**

```
https://v0-horizon-sync.vercel.app/g/28943028344/s/4A8HON/1784792205404?c=MEYCIQCE5i...
```

### Extracting Data from the URL

The consumer QR page must parse the URL path to extract:

| Segment         | Location                 | Example Value   |
| --------------- | ------------------------ | --------------- |
| `gtin`          | `/g/{gtin}/`             | `28943028344`   |
| `serial_number` | `/s/{serial}/`           | `4A8HON`        |
| `timestamp`     | After serial, before `?` | `1784792205404` |
| `signature`     | Query param `c`          | `MEYCIQCE5i...` |

```javascript
// JavaScript parser
function parseQrUrl() {
  const path = window.location.pathname; // /g/28943028344/s/4A8HON/1784792205404
  const params = new URLSearchParams(window.location.search);

  const match = path.match(/\/g\/([^/]+)\/s\/([^/]+)\/([^?]+)/);
  if (!match) return null;

  return {
    gtin: match[1],
    serial_number: match[2],
    timestamp: match[3],
    signature: params.get("c") || "",
  };
}
```

---

## 2. Landing Page Config API (Admin Dashboard)

All admin endpoints require a **Bearer token** in the `Authorization` header.

### 2.1 Fetch Config

```
GET /api/v1/products/{productId}/landing-page
Authorization: Bearer {token}
```

**Response `200`:**

```json
{
  "config": {
    "id": "uuid",
    "product_id": "uuid",
    "organization_id": "uuid",
    "logo_url": "https://cdn.example.com/logo.png",
    "banner_image_url": null,
    "primary_color": "#1a56db",
    "accent_color": "#f59e0b",
    "product_details": {
      "show_gtin": true,
      "show_batch": true,
      "show_mfg_date": true,
      "show_expiry_date": true,
      "show_serial_number": false,
      "custom_fields": []
    },
    "social_links": [],
    "feedback": {
      "enabled": false,
      "type": "none",
      "title": "",
      "description": ""
    },
    "warranty": {
      "enabled": false,
      "title": "",
      "description": "",
      "cta_text": "",
      "cta_url": ""
    },
    "custom_cta": {
      "enabled": false,
      "button_text": "",
      "button_url": "",
      "button_style": "primary"
    },
    "footer": {
      "text": "",
      "show_powered_by": true,
      "custom_links": []
    },
    "created_at": "2026-07-26T10:00:00Z",
    "updated_at": "2026-07-26T10:00:00Z"
  }
}
```

**Error:** `404` — No config exists yet (not created). `403` — Product doesn't belong to your org.

### 2.2 Create Config

```
POST /api/v1/products/{productId}/landing-page
Authorization: Bearer {token}
Content-Type: application/json
```

**Minimal request body** (all other fields get defaults):

```json
{
  "logo_url": "https://cdn.example.com/logo.png",
  "primary_color": "#1a56db"
}
```

**Full request body** — see the [API Contract](./LANDING_PAGE_API_CONTRACT.md) for all nested fields.

**Response:** `201 Created` — same shape as GET.

**Error:** `409` — Config already exists (use PATCH instead).

### 2.3 Update Config (Partial)

```
PATCH /api/v1/products/{productId}/landing-page
Authorization: Bearer {token}
Content-Type: application/json
```

Send **only the fields you want to change**. Nested objects are deep-merged.

```json
{
  "primary_color": "#059669",
  "feedback": {
    "enabled": true,
    "type": "feedback",
    "title": "We'd Love Your Input"
  }
}
```

**Array fields** (`social_links`, `custom_fields`, `footer.custom_links`) are **replaced entirely** — send the full array to modify.

### 2.4 Delete Config

```
DELETE /api/v1/products/{productId}/landing-page
Authorization: Bearer {token}
```

**Response:** `200` — `{ "success": true }`

---

## 3. Landing Page Config API (Consumer QR Page)

Public endpoint — **no authentication required**.

```
GET /api/v1/public/products/{productId}/landing-page?organization_id={orgId}
```

Your consumer QR page needs to know the `product_id` and `organization_id`. Ways to get them:

- **Option A:** Include `product_id` and `organization_id` as query params in the QR URL itself (e.g., `?pid=uuid&oid=uuid`)
- **Option B:** Store a lookup table on the frontend mapping serial numbers to product/org IDs
- **Option C:** Look up by serial number via a separate backend call

Same response shape as the authenticated GET.

**Error:** `404` — No config exists.

---

## 4. Scan Analytics Ingestion

Every time a consumer scans a QR code and lands on your verification page, send a scan event.

```
POST /api/v1/analytics/scans/ingest?organization_id={orgId}
Content-Type: application/json
```

**No auth required.**

### Request Body

```json
{
  "serial_number": "4A8HON",
  "product_item_id": null,
  "device_type": "mobile",
  "os": "iOS",
  "browser": "Safari",
  "ip_address": null,
  "latitude": null,
  "longitude": null,
  "city": null,
  "state": null,
  "country": null,
  "extra_data": {}
}
```

### JavaScript Implementation

```javascript
async function sendScanEvent(serialNumber) {
  // Detect device / OS / browser
  const ua = navigator.userAgent;
  const deviceType = /Mobi|Android/i.test(ua)
    ? "mobile"
    : /iPad|Tablet/i.test(ua)
      ? "tablet"
      : "desktop";

  let os = "Unknown";
  if (/Windows/i.test(ua)) os = "Windows";
  else if (/Mac/i.test(ua)) os = "macOS";
  else if (/Android/i.test(ua)) os = "Android";
  else if (/iPhone|iPad|iPod/i.test(ua)) os = "iOS";

  let browser = "Unknown";
  if (/Edg\//i.test(ua)) browser = "Edge";
  else if (/Chrome/i.test(ua)) browser = "Chrome";
  else if (/Safari/i.test(ua)) browser = "Safari";
  else if (/Firefox/i.test(ua)) browser = "Firefox";

  const backendUrl = "https://core-service-production-66e9.up.railway.app";
  const organizationId = "YOUR_ORG_UUID"; // ⬅️ Replace

  try {
    await fetch(
      `${backendUrl}/api/v1/analytics/scans/ingest?organization_id=${organizationId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          serial_number: serialNumber,
          product_item_id: null,
          device_type: deviceType,
          os,
          browser,
          ip_address: null,
          latitude: null,
          longitude: null,
          city: null,
          state: null,
          country: null,
          extra_data: {},
        }),
      },
    );
  } catch {
    // Fire-and-forget — don't block the page
    console.warn("Analytics ingest failed");
  }
}
```

### Tips

- **Fire and forget** — don't block page rendering or show errors to users.
- **IP address** — leave `null`; the backend captures it server-side.
- **City/State/Country** — leave `null` if you don't have reliable geo data.

---

## 5. Image Upload

```
POST /api/v1/products/{productId}/landing-page/upload-image
Authorization: Bearer {token}
Content-Type: multipart/form-data
```

### Form Fields

| Field        | Type   | Required | Description            |
| ------------ | ------ | -------- | ---------------------- |
| `file`       | File   | Yes      | PNG or JPEG, max 5 MB  |
| `image_type` | String | Yes      | `"logo"` or `"banner"` |

### JavaScript Example

```javascript
async function uploadImage(productId, file, imageType, token) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("image_type", imageType);

  const response = await fetch(
    `https://core-service-production-66e9.up.railway.app/api/v1/products/${productId}/landing-page/upload-image`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData, // ⬅️ Don't set Content-Type — browser sets it with boundary
    },
  );

  const { url } = await response.json();
  return url; // Use this URL in logo_url or banner_image_url
}
```

### Recommended Dimensions

- **Logo:** 300×300 px (displayed at 80×80 px)
- **Banner:** 1200×400 px (3:1 aspect ratio)

---

## 6. Complete Consumer QR Page Flow

When your frontend page at `https://v0-horizon-sync.vercel.app/g/{gtin}/s/{serial}/{ts}?c={sig}` loads:

```javascript
// Step 1: Parse QR URL
const qrData = parseQrUrl();
if (!qrData) {
  showError("Invalid QR code");
  return;
}

// Step 2: Look up product/org IDs (choose your method)
const { productId, orgId } = await lookupProduct(qrData.serial_number);

// Step 3: Fire analytics (don't wait)
sendScanEvent(qrData.serial_number);

// Step 4: Fetch landing page config
fetch(
  `https://core-service-production-66e9.up.railway.app/api/v1/public/products/${productId}/landing-page?organization_id=${orgId}`,
)
  .then((res) => res.json())
  .then((data) => {
    const config = data.config;
    // Step 5: Render the page with the config
    renderLandingPage(config, qrData);
  })
  .catch(() => {
    // Step 6: Fallback — render default verification page
    renderDefaultPage(qrData);
  });
```

### Rendering the Config

| Config Section                        | What to Render                          |
| ------------------------------------- | --------------------------------------- |
| `logo_url` / `banner_image_url`       | Hero images                             |
| `primary_color` / `accent_color`      | Theme colors (buttons, headers)         |
| `product_details.show_*`              | Toggle visibility of GTIN, batch, dates |
| `product_details.custom_fields`       | Extra key-value rows                    |
| `social_links` (enabled ones)         | Social media icon links                 |
| `feedback`                            | Feedback form or survey link            |
| `warranty`                            | Warranty registration CTA card          |
| `custom_cta`                          | Call-to-action button                   |
| `footer.text` / `footer.custom_links` | Footer section                          |

---

## 7. Permissions

The admin dashboard endpoints require these permissions (assign to roles in identity-service):

| Permission                  | Required For                     |
| --------------------------- | -------------------------------- |
| `landing_page.create`       | POST create config               |
| `landing_page.read`         | GET fetch config (authenticated) |
| `landing_page.update`       | PATCH update config              |
| `landing_page.delete`       | DELETE config                    |
| `landing_page.upload_image` | POST upload image                |

Run this to seed the permissions:

```bash
docker compose exec core-service python scripts/seed_brand_permissions.py
```
