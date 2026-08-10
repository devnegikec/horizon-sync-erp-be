# QR Analytics — Frontend Dashboard Integration Guide

> **Audience:** Frontend developers building the QSeal analytics dashboard
> **Base URL:** `https://core-xxxxx.snapdeploy.dev/api/v1/analytics` > **Auth:** Bearer token from Identity Service login

---

## 1. Quick Reference — All Endpoints

| #   | Method   | Endpoint                    | Auth       | Purpose                                                        |
| --- | -------- | --------------------------- | ---------- | -------------------------------------------------------------- |
| 1   | `POST`   | `/scans/ingest`             | **Public** | Record a QR scan (called by QR landing page, not dashboard)    |
| 2   | `GET`    | `/scans`                    | ✅ Auth    | Paginated list of all scan events                              |
| 3   | `GET`    | `/scans/summary`            | ✅ Auth    | Aggregate: total scans, unique serials, by date/country/device |
| 4   | `GET`    | `/scans/cta-breakdown`      | ✅ Auth    | CTA action distribution (view_product vs call vs website)      |
| 5   | `GET`    | `/scans/geo-heatmap`        | ✅ Auth    | Scans grouped by city with lat/lng (map-ready)                 |
| 6   | `GET`    | `/scans/device-timeline`    | ✅ Auth    | Scans over time, pivoted by mobile/desktop/tablet              |
| 7   | `GET`    | `/scans/interaction-funnel` | ✅ Auth    | Funnel: scans → CTA clicks → conversion rate                   |
| 8   | `POST`   | `/scans/{id}/interactions`  | **Public** | Record post-scan action (called by QR landing page)            |
| 9   | `GET`    | `/scans/{id}/interactions`  | ✅ Auth    | List interactions for a specific scan                          |
| 10  | `POST`   | `/products/{pid}/ctas`      | ✅ Auth    | Create CTA button config                                       |
| 11  | `GET`    | `/products/{pid}/ctas`      | ✅ Auth    | List CTA configs for a product                                 |
| 12  | `GET`    | `/products/{pid}/ctas/{id}` | ✅ Auth    | Get single CTA config                                          |
| 13  | `PUT`    | `/products/{pid}/ctas/{id}` | ✅ Auth    | Update CTA config                                              |
| 14  | `DELETE` | `/products/{pid}/ctas/{id}` | ✅ Auth    | Delete CTA config                                              |

Endpoints 1 & 8 are **public** — called by the QR landing page when a consumer scans a code.
All others require an **auth token** — used by the dashboard.

---

## 2. Authentication

### 2.1 Get a Token

```bash
POST https://identity-xxxxx.snapdeploy.dev/api/v1/identity/login
Content-Type: application/json

{
  "email": "admin@organization.com",
  "password": "your-password"
}
```

Response:

```json
{
  "access_token": "eyJhbGciOi...",
  "refresh_token": "eyJhbGciOi...",
  "token_type": "bearer"
}
```

### 2.2 Use the Token

Every authenticated request needs:

```
Authorization: Bearer eyJhbGciOi...
```

The `organization_id` is automatically resolved from the token — you never need to pass it.

### 2.3 Token Expiry

- `access_token` expires after `ACCESS_TOKEN_EXPIRE_MINUTES` (default: 4320 min = 3 days)
- Use `/api/v1/identity/refresh` to get a new token without re-login

---

## 3. Dashboard Pages & Widgets

### Page A: Overview Dashboard

**Purpose:** Executive summary — key metrics at a glance.

| Widget                           | Endpoint             | Key Fields                             |
| -------------------------------- | -------------------- | -------------------------------------- |
| **Total Scans (KPI card)**       | `GET /scans/summary` | `total_scans`, `unique_serials`        |
| **Scans Over Time (line chart)** | `GET /scans/summary` | `by_date[]` → `{date, count}`          |
| **Top Countries (bar chart)**    | `GET /scans/summary` | `by_country[]` → `{country, count}`    |
| **Device Split (pie chart)**     | `GET /scans/summary` | `by_device[]` → `{device_type, count}` |

**Single API call covers all 4 widgets:**

```javascript
const { total_scans, unique_serials, by_date, by_country, by_device } =
  await api.get("/analytics/scans/summary", {
    params: { date_from: "2026-06-01", date_to: "2026-07-13" },
  });
```

---

### Page B: CTA Performance

**Purpose:** Which Call-to-Action buttons are driving engagement?

| Widget                                | Endpoint                        | Key Fields                                                                 |
| ------------------------------------- | ------------------------------- | -------------------------------------------------------------------------- |
| **CTA Distribution (donut chart)**    | `GET /scans/cta-breakdown`      | `breakdown[]` → `{cta_action, count}`                                      |
| **Total Scans with CTA (metric)**     | `GET /scans/cta-breakdown`      | `total_scans_with_cta`                                                     |
| **Conversion Funnel (funnel chart)**  | `GET /scans/interaction-funnel` | `total_scans → scans_with_cta → scans_with_interactions → conversion_rate` |
| **Top Interaction Types (bar chart)** | `GET /scans/interaction-funnel` | `top_interaction_types[]` → `{interaction_type, count}`                    |

**Example Response — CTA Breakdown:**

```json
{
  "breakdown": [
    { "cta_action": "view_product", "count": 452 },
    { "cta_action": "visit_website", "count": 287 },
    { "cta_action": "verify_auth", "count": 193 },
    { "cta_action": "call_support", "count": 68 }
  ],
  "total_scans_with_cta": 1000
}
```

**Example Response — Interaction Funnel:**

```json
{
  "total_scans": 1000,
  "scans_with_cta": 1000,
  "scans_with_interactions": 320,
  "total_interactions": 485,
  "conversion_rate": 0.32,
  "top_interaction_types": [
    { "interaction_type": "click", "count": 245 },
    { "interaction_type": "share", "count": 120 },
    { "interaction_type": "call", "count": 68 },
    { "interaction_type": "form_submit", "count": 52 }
  ]
}
```

---

### Page C: Geographic Heatmap

**Purpose:** World/region map showing scan density.

| Widget                      | Endpoint                           | Key Fields                                             |
| --------------------------- | ---------------------------------- | ------------------------------------------------------ |
| **Geo Heatmap (map tiles)** | `GET /scans/geo-heatmap?limit=500` | `[{city, state, country, latitude, longitude, count}]` |

**Response:**

```json
[
  {
    "city": "Mumbai",
    "state": "Maharashtra",
    "country": "India",
    "latitude": 19.07,
    "longitude": 72.87,
    "count": 145
  },
  {
    "city": "Delhi",
    "state": "Delhi",
    "country": "India",
    "latitude": 28.61,
    "longitude": 77.23,
    "count": 98
  },
  {
    "city": "Dubai",
    "state": null,
    "country": "UAE",
    "latitude": 25.2,
    "longitude": 55.27,
    "count": 42
  },
  {
    "city": "New York",
    "state": "New York",
    "country": "United States",
    "latitude": 40.71,
    "longitude": -74.0,
    "count": 31
  }
]
```

**Mapping library integration (Leaflet example):**

```javascript
const points = await api.get("/analytics/scans/geo-heatmap", {
  params: { date_from: "2026-06-01", limit: 500 },
});

points.forEach((p) => {
  L.circleMarker([p.latitude, p.longitude], {
    radius: Math.min(p.count / 5, 20),
    fillColor: "#3B82F6",
    fillOpacity: 0.6,
  })
    .bindPopup(`${p.city}, ${p.country}<br><b>${p.count} scans</b>`)
    .addTo(map);
});
```

---

### Page D: Device Timeline

**Purpose:** Track device adoption — are users on mobile, desktop, or tablet?

| Widget                                   | Endpoint                     | Key Fields                                   |
| ---------------------------------------- | ---------------------------- | -------------------------------------------- |
| **Device Timeline (stacked area chart)** | `GET /scans/device-timeline` | `[{date, mobile, desktop, tablet, unknown}]` |

**Response:**

```json
[
  {
    "date": "2026-07-10",
    "mobile": 45,
    "desktop": 12,
    "tablet": 3,
    "unknown": 0
  },
  {
    "date": "2026-07-11",
    "mobile": 52,
    "desktop": 15,
    "tablet": 5,
    "unknown": 1
  },
  {
    "date": "2026-07-12",
    "mobile": 61,
    "desktop": 10,
    "tablet": 2,
    "unknown": 0
  },
  {
    "date": "2026-07-13",
    "mobile": 38,
    "desktop": 18,
    "tablet": 4,
    "unknown": 0
  }
]
```

**Chart.js stacked bar example:**

```javascript
const timeline = await api.get("/analytics/scans/device-timeline");

new Chart(ctx, {
  type: "bar",
  data: {
    labels: timeline.map((d) => d.date),
    datasets: [
      {
        label: "Mobile",
        data: timeline.map((d) => d.mobile),
        backgroundColor: "#3B82F6",
      },
      {
        label: "Desktop",
        data: timeline.map((d) => d.desktop),
        backgroundColor: "#10B981",
      },
      {
        label: "Tablet",
        data: timeline.map((d) => d.tablet),
        backgroundColor: "#F59E0B",
      },
    ],
  },
  options: {
    scales: { x: { stacked: true }, y: { stacked: true } },
  },
});
```

---

### Page E: Scan Event Log

**Purpose:** Drill-down table — see individual scan records with all enriched data.

| Widget                | Endpoint                         | Key Fields                                                 |
| --------------------- | -------------------------------- | ---------------------------------------------------------- |
| **Scan Events Table** | `GET /scans?page=1&page_size=50` | `events[]`, `pagination`                                   |
| **Filters**           | Query params                     | `serial_number`, `date_from`, `date_to`, `product_item_id` |

**Response:**

```json
{
  "events": [
    {
      "id": "29da1133-3072-407a-9606-7c62c50ed808",
      "serial_number": "PROD-ABC-12345",
      "scan_timestamp": "2026-07-13T16:57:50.129Z",
      "cta_action": "view_product",
      "qr_type": "product_auth",
      "device_type": "mobile",
      "os": "iOS",
      "browser": "Mobile Safari",
      "city": "Mumbai",
      "state": "Maharashtra",
      "country": "India",
      "ip_address": "103.15.xx.xx",
      "referrer_url": "https://instagram.com/p/...",
      "language": "en-IN",
      "user_agent_parsed": {
        "browser": "Mobile Safari",
        "browser_version": "17.0",
        "os": "iOS",
        "os_version": "17.0",
        "device_type": "mobile",
        "is_mobile": true,
        "is_tablet": false,
        "is_pc": false
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 1247,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

**Table columns to display:**

| Column   | Field             | Notes                                        |
| -------- | ----------------- | -------------------------------------------- |
| Time     | `scan_timestamp`  | Format: `Jul 13, 2026 4:57 PM`               |
| Serial   | `serial_number`   | Link to product detail                       |
| CTA      | `cta_action`      | Badge: `view_product`, `visit_website`, etc. |
| Device   | `os` / `browser`  | Icon + text                                  |
| Location | `city`, `country` | Flag emoji + text                            |
| Referrer | `referrer_url`    | Truncated, link if present                   |
| Details  | `id`              | Link to scan detail with interactions        |

---

### Page F: Product CTA Configuration

**Purpose:** Admin page to configure which CTA buttons appear on each product's QR landing page.

| Action     | Endpoint                                    |
| ---------- | ------------------------------------------- |
| List CTAs  | `GET /products/{productId}/ctas`            |
| Add CTA    | `POST /products/{productId}/ctas`           |
| Edit CTA   | `PUT /products/{productId}/ctas/{ctaId}`    |
| Remove CTA | `DELETE /products/{productId}/ctas/{ctaId}` |

**CTA Config Object:**

```json
{
  "id": "0145a024-0e94-477f-b24d-917fbc34562a",
  "product_id": "57560cb3-419f-471d-a946-8e34d6291b15",
  "cta_type": "verify_auth",
  "cta_label": "Verify Authenticity",
  "cta_target": null,
  "display_order": 1,
  "is_active": true
}
```

**UI: Drag-and-drop reorder list + inline edit form**

```
┌─────────────────────────────────────────────┐
│  CTA Buttons for "Nike Air Max"             │
│                                             │
│  ☰ 1. [Verify Authenticity]    [✏️] [🗑️]    │
│  ☰ 2. [Visit Website      ]    [✏️] [🗑️]    │
│  ☰ 3. [Call Support       ]    [✏️] [🗑️]    │
│                                             │
│  [+ Add CTA Button]                         │
└─────────────────────────────────────────────┘
```

---

## 4. Common Patterns

### 4.1 Date Filters

All summary/analytics endpoints support `date_from` and `date_to` (ISO 8601):

```javascript
// Last 30 days
const from = new Date(Date.now() - 30 * 86400000).toISOString();
const to = new Date().toISOString();

const summary = await api.get("/analytics/scans/summary", {
  params: { date_from: from, date_to: to },
});
```

### 4.2 Auto-Refresh

Dashboard widgets should poll every 30-60 seconds:

```javascript
const useAnalytics = (endpoint, params, interval = 60000) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetch = () => api.get(endpoint, { params }).then(setData);
    fetch(); // initial load
    const timer = setInterval(fetch, interval);
    return () => clearInterval(timer);
  }, [endpoint, JSON.stringify(params)]);

  return data;
};

// Usage
const summary = useAnalytics("/analytics/scans/summary", {
  date_from,
  date_to,
});
```

### 4.3 Error Handling

```javascript
try {
  const data = await api.get("/analytics/scans/summary");
} catch (error) {
  if (error.response?.status === 401) {
    // Token expired — redirect to login
    router.push("/login");
  } else if (error.response?.data?.code === "FEATURE_DISABLED") {
    // Analytics module not enabled for this org
    showBanner("Analytics module is not enabled. Contact your administrator.");
  } else {
    showToast("Failed to load analytics. Please try again.");
  }
}
```

### 4.4 Empty State

When an org has no scan data yet:

```
┌─────────────────────────────────┐
│                                 │
│        📊  No data yet          │
│                                 │
│   QR scans will appear here     │
│   once consumers start scanning │
│   your product QR codes.        │
│                                 │
│      [View Integration Guide]   │
└─────────────────────────────────┘
```

---

## 5. Complete API Service (TypeScript)

```typescript
// services/analyticsApi.ts

const BASE = "/api/v1/analytics";

interface DateRange {
  date_from?: string;
  date_to?: string;
}

export const analyticsApi = {
  // ── Overview ──────────────────────────────────────────────
  getSummary(params?: DateRange & { serial_number?: string }) {
    return api.get(`${BASE}/scans/summary`, { params });
  },

  // ── CTA & Funnel ──────────────────────────────────────────
  getCTABreakdown(params?: DateRange) {
    return api.get(`${BASE}/scans/cta-breakdown`, { params });
  },

  getInteractionFunnel(params?: DateRange) {
    return api.get(`${BASE}/scans/interaction-funnel`, { params });
  },

  // ── Geo ───────────────────────────────────────────────────
  getGeoHeatmap(params?: DateRange & { limit?: number }) {
    return api.get(`${BASE}/scans/geo-heatmap`, { params });
  },

  // ── Device ────────────────────────────────────────────────
  getDeviceTimeline(params?: DateRange) {
    return api.get(`${BASE}/scans/device-timeline`, { params });
  },

  // ── Scan Log ──────────────────────────────────────────────
  getScans(
    params?: DateRange & {
      page?: number;
      page_size?: number;
      serial_number?: string;
    },
  ) {
    return api.get(`${BASE}/scans`, { params });
  },

  getScanInteractions(scanId: string) {
    return api.get(`${BASE}/scans/${scanId}/interactions`);
  },

  // ── CTA Config (Admin) ────────────────────────────────────
  listCTAConfigs(productId: string) {
    return api.get(`${BASE}/products/${productId}/ctas`);
  },

  createCTAConfig(productId: string, data: CTAConfigInput) {
    return api.post(`${BASE}/products/${productId}/ctas`, data);
  },

  updateCTAConfig(
    productId: string,
    ctaId: string,
    data: Partial<CTAConfigInput>,
  ) {
    return api.put(`${BASE}/products/${productId}/ctas/${ctaId}`, data);
  },

  deleteCTAConfig(productId: string, ctaId: string) {
    return api.delete(`${BASE}/products/${productId}/ctas/${ctaId}`);
  },
};
```

---

## 6. Wireframe — Dashboard Layout

```
┌──────────────────────────────────────────────────────────────┐
│  📊 Analytics Dashboard              [Last 30 Days ▼] [🔄]   │
├──────────┬──────────┬──────────┬──────────────────────────────┤
│ Total    │ Unique   │ CTA      │ Conversion                   │
│ Scans    │ Products │ Rate     │ Rate                         │
│  1,247   │   89     │  80%     │  32%                         │
├──────────┴──────────┴──────────┴──────────────────────────────┤
│                                                               │
│  📈 Scans Over Time (Line Chart)                              │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │     ╱╲        ╱╲                                       │  │
│  │    ╱  ╲      ╱  ╲    ╱╲                                │  │
│  │   ╱    ╲╱╲╱╲╱    ╲╱╲╱  ╲                               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                               │
├─────────────────────────────┬─────────────────────────────────┤
│  🌍 Top Countries           │  📱 Device Split               │
│  ┌───────────────────────┐  │  ┌──────────┐                  │
│  │ India     ████████ 580│  │  │ Mobile   │ ████████ 72%    │
│  │ UAE       ████ 210    │  │  │ Desktop  │ ███ 18%         │
│  │ USA       ███ 145     │  │  │ Tablet   │ █ 10%           │
│  │ UK        ██ 98       │  │  └──────────┘                  │
│  └───────────────────────┘  │                                 │
├─────────────────────────────┴─────────────────────────────────┤
│  🔄 CTA Performance                                           │
│  ┌──────────────────────┐  ┌───────────────────────────────┐  │
│  │ View Product    ████ │  │ Scans → CTA → Interactions    │  │
│  │ Visit Website   ███  │  │ 1000  →  800  →   320 (32%)  │  │
│  │ Verify Auth     ██   │  │                               │  │
│  │ Call Support    █    │  │ Top: click(245) share(120)    │  │
│  └──────────────────────┘  └───────────────────────────────┘  │
├───────────────────────────────────────────────────────────────┤
│  🌏 Geographic Heatmap                                        │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    [World Map]                           │  │
│  │              ● Delhi (98)    ● Dubai (42)               │  │
│  │       ● Mumbai (145)                                     │  │
│  │                                          ● NYC (31)      │  │
│  └─────────────────────────────────────────────────────────┘  │
├───────────────────────────────────────────────────────────────┤
│  📋 Recent Scans                                              │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────┐  │
│  │ Time     │ Serial   │ CTA      │ Device   │ Location   │  │
│  ├──────────┼──────────┼──────────┼──────────┼────────────┤  │
│  │ 4:57 PM  │ ABC-123  │ view💊   │ 📱 iOS   │ 🇮🇳 Mumbai │  │
│  │ 4:55 PM  │ XYZ-456  │ website🌐│ 💻 Win   │ 🇦🇪 Dubai  │  │
│  │ 4:52 PM  │ DEF-789  │ verify✅ │ 📱 And   │ 🇮🇳 Delhi  │  │
│  └──────────┴──────────┴──────────┴──────────┴────────────┘  │
│                                          [1] 2 3 ... 25 →    │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. API Call Summary Per Dashboard Load

| Dashboard Page     | APIs Called                                              | Total Requests |
| ------------------ | -------------------------------------------------------- | -------------- |
| Overview           | `/scans/summary`                                         | **1**          |
| CTA Performance    | `/scans/cta-breakdown` + `/scans/interaction-funnel`     | **2**          |
| Geo Heatmap        | `/scans/geo-heatmap`                                     | **1**          |
| Device Timeline    | `/scans/device-timeline`                                 | **1**          |
| Scan Log           | `/scans` (+ `/scans/{id}/interactions` on row click)     | **1-2**        |
| CTA Config (Admin) | `/products/{pid}/ctas` (list), POST/PUT/DELETE on action | **1-2**        |

**Recommended:** Load all summary endpoints in parallel on dashboard mount:

```typescript
const [summary, ctaBreakdown, funnel, heatmap, timeline] = await Promise.all([
  analyticsApi.getSummary(dateRange),
  analyticsApi.getCTABreakdown(dateRange),
  analyticsApi.getInteractionFunnel(dateRange),
  analyticsApi.getGeoHeatmap({ ...dateRange, limit: 200 }),
  analyticsApi.getDeviceTimeline(dateRange),
]);
```

---

## 8. Environment Configuration

```env
# .env (frontend)
VITE_API_BASE_URL=https://core-xxxxx.snapdeploy.dev/api/v1
VITE_IDENTITY_URL=https://identity-xxxxx.snapdeploy.dev/api/v1
```

The frontend calls **Core Service** for all analytics. Core Service internally calls Identity Service for auth validation — the frontend never calls Identity directly except for login/refresh.

---

## 9. Notes

- **Feature flag:** Analytics endpoints return `FEATURE_DISABLED` if the org hasn't enabled `analytics_module_enabled`. Handle this in the UI.
- **Geo data accuracy:** City/country comes from either client GPS (if the QR landing page sends it) or server-side IP geolocation fallback. Accuracy varies by IP.
- **Device detection:** `device_type` on scan events is from the parsed User-Agent header. It detects mobile/desktop/tablet but won't identify specific models beyond what the UA string provides.
- **Rate limiting:** Authenticated endpoints share the org's rate limit. Public ingest endpoints have a higher limit.
