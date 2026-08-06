# QR Code Scan Analytics — Frontend Integration Guide

## Overview

When a consumer scans a product QR code and lands on your verification page, you need to send a scan event to the backend. This powers the analytics dashboard (scans by date, country, device, etc.).

## API Endpoint

| Field            | Value                                                                  |
| ---------------- | ---------------------------------------------------------------------- |
| **Method**       | `POST`                                                                 |
| **URL**          | `{BACKEND_API}/api/v1/analytics/scans/ingest?organization_id={ORG_ID}` |
| **Auth**         | **None** (public endpoint)                                             |
| **Content-Type** | `application/json`                                                     |

- `{BACKEND_API}` — your backend base URL (e.g., `https://api.horizonsync.com`)
- `{ORG_ID}` — the UUID of the organization that owns the QR product

## Request Body

```json
{
  "serial_number": "4A8HON",
  "product_item_id": null,
  "device_type": "mobile",
  "os": "iOS",
  "browser": "Safari",
  "ip_address": null,
  "latitude": 28.6139,
  "longitude": 77.209,
  "city": "New Delhi",
  "state": "Delhi",
  "country": "IN",
  "extra_data": {}
}
```

### Field Details

| Field             | Type        | Required | Description                                                |
| ----------------- | ----------- | -------- | ---------------------------------------------------------- |
| `serial_number`   | string      | **Yes**  | The serial from the URL path (`/s/{serial}/`)              |
| `product_item_id` | UUID/null   | No       | The `product_item` UUID if available                       |
| `device_type`     | string/null | No       | `"mobile"`, `"tablet"`, `"desktop"`, or `null`             |
| `os`              | string/null | No       | OS name, e.g., `"iOS"`, `"Android"`, `"Windows"`           |
| `browser`         | string/null | No       | Browser name, e.g., `"Safari"`, `"Chrome"`                 |
| `ip_address`      | string/null | No       | Client IP (leave `null` — backend captures it server-side) |
| `latitude`        | float/null  | No       | Approximate latitude                                       |
| `longitude`       | float/null  | No       | Approximate longitude                                      |
| `city`            | string/null | No       | City name                                                  |
| `state`           | string/null | No       | State/province name                                        |
| `country`         | string/null | No       | ISO country code, e.g., `"IN"`, `"US"`                     |
| `extra_data`      | object/null | No       | Any additional key-value metadata                          |

## JavaScript Example (Frontend)

```javascript
// Place this in your QR verification landing page, on page load.

async function sendScanEvent() {
  // 1. Extract serial_number from the URL
  //    URL format: /g/{gtin}/s/{serial_number}/{timestamp}?c={signature}
  const pathMatch = window.location.pathname.match(/\/s\/([^/]+)/);
  const serialNumber = pathMatch ? pathMatch[1] : null;
  if (!serialNumber) return;

  // 2. Detect device / OS / browser from user-agent
  const ua = navigator.userAgent;
  const deviceType = /Mobi|Android/i.test(ua)
    ? "mobile"
    : /iPad|Tablet/i.test(ua)
      ? "tablet"
      : "desktop";

  let os = "Unknown";
  if (/Windows/i.test(ua)) os = "Windows";
  else if (/Mac/i.test(ua)) os = "macOS";
  else if (/Linux/i.test(ua)) os = "Linux";
  else if (/Android/i.test(ua)) os = "Android";
  else if (/iPhone|iPad|iPod/i.test(ua)) os = "iOS";

  let browser = "Unknown";
  if (/Edg\//i.test(ua)) browser = "Edge";
  else if (/Chrome/i.test(ua) && !/Edg\//i.test(ua)) browser = "Chrome";
  else if (/Safari/i.test(ua) && !/Chrome/i.test(ua)) browser = "Safari";
  else if (/Firefox/i.test(ua)) browser = "Firefox";

  // 3. (Optional) Get approximate location via browser geolocation
  let lat = null,
    lng = null;
  try {
    const pos = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        timeout: 3000,
      });
    });
    lat = pos.coords.latitude;
    lng = pos.coords.longitude;
  } catch {
    // Geolocation denied or unavailable — leave as null
  }

  // 4. Send to backend
  const backendUrl = "https://api.horizonsync.com"; // <-- REPLACE with your backend URL
  const organizationId = "YOUR_ORG_UUID"; // <-- REPLACE with the org UUID

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
          os: os,
          browser: browser,
          ip_address: null,
          latitude: lat,
          longitude: lng,
          city: null,
          state: null,
          country: null,
          extra_data: {},
        }),
      },
    );
  } catch (err) {
    // Fire-and-forget — don't block the page if analytics fails
    console.warn("Analytics ingest failed:", err);
  }
}

// Call on page load
sendScanEvent();
```

## Expected Response

**201 Created:**

```json
{
  "id": "a1b2c3d4-...",
  "organization_id": "...",
  "serial_number": "4A8HON",
  "product_item_id": null,
  "scan_timestamp": "2026-07-26T10:30:00Z",
  "device_type": "mobile",
  "os": "iOS",
  "browser": "Safari",
  "city": null,
  "state": null,
  "country": null
}
```

## Key Notes

1. **Fire-and-forget**: The analytics call should NOT block page rendering. Use `async`/`await` but don't tie it to the user experience.
2. **No auth required**: This is a public endpoint. The `organization_id` query parameter identifies the owner.
3. **How to get `organization_id`**: Pass it from the backend when generating the QR block, or store it in a lookup by serial number, or include it as a query parameter in the QR URL itself.
4. **IP address**: Leave `null`. The backend captures the real client IP server-side.
5. **City/State/Country**: Can be resolved server-side via IP geolocation. Leave `null` in the frontend request unless you have reliable data.
6. **QR URL format**: The URL pattern is `{base_url}/g/{gtin}/s/{serial}/{timestamp}?c={signature}`. Extract `serial` from between `/s/` and the next `/`.
