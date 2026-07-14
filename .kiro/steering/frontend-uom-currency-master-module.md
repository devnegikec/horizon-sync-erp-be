---
inclusion: manual
---

# Frontend UOM & Currency Master Module - Integration Guide

Complete API reference for integrating UOM, UOM Conversion, Currency, and Exchange Rate master data into the frontend.

## Base URL & Auth

```
Base: http://localhost:8001/api/v1
Auth: Authorization: Bearer {token}
```

All endpoints require a valid Bearer token. Token is stored in `localStorage.getItem("token")`.

---

## 1. UOM (Unit of Measure) API

### Create UOM

```
POST /uoms
```

```json
{
  "name": "Kilogram",
  "abbreviation": "Kg",
  "description": "Metric unit of mass"
}
```

Response: `UOMResponse` (201)

### List UOMs

```
GET /uoms?page=1&page_size=20&search=keyword
```

Response:

```json
{
  "uoms": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "name": "Kilogram",
      "abbreviation": "Kg",
      "description": "Metric unit of mass",
      "created_by": "uuid | null",
      "updated_by": "uuid | null",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 12,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### Get UOM

```
GET /uoms/{id}
```

### Update UOM

```
PATCH /uoms/{id}
```

```json
{
  "name": "Kilogramme",
  "abbreviation": "Kg",
  "description": "Updated description"
}
```

All fields optional.

### Delete UOM (soft delete)

```
DELETE /uoms/{id}
```

Returns 204.

### Error Codes

| Scenario               | Status | Detail                                                             |
| ---------------------- | ------ | ------------------------------------------------------------------ |
| Duplicate name         | 409    | `"UOM with name 'Kg' already exists in this organization"`         |
| Duplicate abbreviation | 409    | `"UOM with abbreviation 'Kg' already exists in this organization"` |
| Not found / wrong org  | 404    | `"UOM not found"`                                                  |

---

## 2. UOM Conversion API

Stores per-item conversion factors. Formula: `Base_Qty = Transaction_Qty × conversion_factor`

### Create UOM Conversion

```
POST /uom-conversions
```

```json
{
  "item_id": "uuid",
  "from_uom": "Box",
  "to_uom": "Nos",
  "conversion_factor": 12.0
}
```

Response: `UOMConversionResponse` (201)

### List UOM Conversions

```
GET /uom-conversions?page=1&page_size=20&item_id={uuid}
```

Filter by `item_id` to show conversions for a specific item.

Response:

```json
{
  "uom_conversions": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "item_id": "uuid",
      "from_uom": "Box",
      "to_uom": "Nos",
      "conversion_factor": 12.0,
      "created_by": "uuid | null",
      "updated_by": "uuid | null",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "pagination": { "..." }
}
```

### Get UOM Conversion

```
GET /uom-conversions/{id}
```

### Update UOM Conversion

```
PATCH /uom-conversions/{id}
```

```json
{
  "from_uom": "Carton",
  "to_uom": "Nos",
  "conversion_factor": 24.0
}
```

All fields optional.

### Delete UOM Conversion (soft delete)

```
DELETE /uom-conversions/{id}
```

Returns 204.

### Error Codes

| Scenario                       | Status | Detail                                                                |
| ------------------------------ | ------ | --------------------------------------------------------------------- |
| Duplicate (item + from + to)   | 409    | `"UOM conversion for item '{id}' from 'Box' to 'Nos' already exists"` |
| Non-positive conversion_factor | 422    | `"conversion_factor must be greater than 0"`                          |
| Item not found                 | 404    | `"Item '{id}' not found in this organization"`                        |
| Conversion not found           | 404    | `"UOM conversion not found"`                                          |

---

## 3. Currency Master API

### Create Currency

```
POST /currencies
```

```json
{
  "code": "USD",
  "name": "US Dollar",
  "symbol": "$",
  "is_base_currency": true
}
```

When `is_base_currency` is `true`, all other currencies in the org are automatically set to `false`.

Response: `CurrencyMasterResponse` (201)

### List Currencies

```
GET /currencies?page=1&page_size=20&search=keyword
```

Response:

```json
{
  "currencies": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "code": "USD",
      "name": "US Dollar",
      "symbol": "$",
      "is_base_currency": true,
      "created_by": "uuid | null",
      "updated_by": "uuid | null",
      "created_at": "datetime",
      "updated_at": "datetime"
    }
  ],
  "pagination": { "..." }
}
```

### Get Currency

```
GET /currencies/{id}
```

### Update Currency

```
PATCH /currencies/{id}
```

```json
{
  "name": "United States Dollar",
  "symbol": "$",
  "is_base_currency": false
}
```

All fields optional. Setting `is_base_currency: true` clears the flag on all other currencies.

### Delete Currency (soft delete)

```
DELETE /currencies/{id}
```

Returns 204.

### Error Codes

| Scenario              | Status | Detail                                                           |
| --------------------- | ------ | ---------------------------------------------------------------- |
| Duplicate code        | 409    | `"Currency with code 'USD' already exists in this organization"` |
| Invalid code format   | 422    | `"code must be exactly 3 uppercase letters"`                     |
| Not found / wrong org | 404    | `"Currency not found"`                                           |

---

## 4. Exchange Rate API (Organization-Scoped)

New org-scoped endpoints. The legacy `/currency/exchange-rates` endpoints continue to work.

### Create Exchange Rate

```
POST /exchange-rates
```

```json
{
  "from_currency": "USD",
  "to_currency": "INR",
  "rate": 83.25,
  "effective_date": "2026-02-24"
}
```

`effective_date` defaults to today if omitted. If a rate for the same (org, from, to, date) already exists, it is updated (upsert).

Response: `ExchangeRateResponse` (201)

### List Exchange Rates

```
GET /exchange-rates?page=1&page_size=20&from_currency=USD&to_currency=INR&start_date=2026-01-01&end_date=2026-12-31
```

All query params optional.

Response:

```json
{
  "exchange_rates": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "from_currency": "USD",
      "to_currency": "INR",
      "rate": 83.25,
      "effective_date": "2026-02-24",
      "captured_at": "datetime",
      "created_at": "datetime"
    }
  ],
  "pagination": { "..." }
}
```

### Get Exchange Rate

```
GET /exchange-rates/{id}
```

### Update Exchange Rate

```
PUT /exchange-rates/{id}
```

```json
{
  "rate": 83.5,
  "effective_date": "2026-02-25"
}
```

### Delete Exchange Rate (hard delete)

```
DELETE /exchange-rates/{id}
```

Returns 204. Record is permanently removed.

### Error Codes

| Scenario           | Status | Detail                                              |
| ------------------ | ------ | --------------------------------------------------- |
| Same currency pair | 422    | `"from_currency and to_currency must be different"` |
| Non-positive rate  | 422    | `"rate must be greater than 0"`                     |
| Not found          | 404    | `"Exchange rate not found"`                         |

---

## 5. TypeScript Types

```typescript
// uomCurrency.types.ts

// ============================================
// UOM TYPES
// ============================================

export interface UOM {
  id: string;
  organization_id: string;
  name: string;
  abbreviation: string;
  description: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface UOMCreate {
  name: string;
  abbreviation: string;
  description?: string | null;
}

export interface UOMUpdate {
  name?: string;
  abbreviation?: string;
  description?: string | null;
}

export interface UOMListResponse {
  uoms: UOM[];
  pagination: PaginationMeta;
}

// ============================================
// UOM CONVERSION TYPES
// ============================================

export interface UOMConversion {
  id: string;
  organization_id: string;
  item_id: string;
  from_uom: string;
  to_uom: string;
  conversion_factor: number;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface UOMConversionCreate {
  item_id: string;
  from_uom: string;
  to_uom: string;
  conversion_factor: number;
}

export interface UOMConversionUpdate {
  from_uom?: string;
  to_uom?: string;
  conversion_factor?: number;
}

export interface UOMConversionListResponse {
  uom_conversions: UOMConversion[];
  pagination: PaginationMeta;
}

// ============================================
// CURRENCY TYPES
// ============================================

export interface Currency {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  symbol: string | null;
  is_base_currency: boolean;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CurrencyCreate {
  code: string;
  name: string;
  symbol?: string | null;
  is_base_currency?: boolean;
}

export interface CurrencyUpdate {
  name?: string;
  symbol?: string | null;
  is_base_currency?: boolean;
}

export interface CurrencyListResponse {
  currencies: Currency[];
  pagination: PaginationMeta;
}

// ============================================
// EXCHANGE RATE TYPES
// ============================================

export interface ExchangeRate {
  id: string;
  organization_id: string | null;
  from_currency: string;
  to_currency: string;
  rate: number;
  effective_date: string;
  captured_at: string | null;
  created_at: string;
}

export interface ExchangeRateCreate {
  from_currency: string;
  to_currency: string;
  rate: number;
  effective_date?: string;
}

export interface ExchangeRateUpdate {
  rate: number;
  effective_date?: string;
}

export interface ExchangeRateListResponse {
  exchange_rates: ExchangeRate[];
  pagination: PaginationMeta;
}

// ============================================
// SHARED
// ============================================

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
```

---

## 6. Frontend Service Layer

```typescript
import apiClient from "./apiClient";
import type {
  UOM,
  UOMCreate,
  UOMUpdate,
  UOMListResponse,
  UOMConversion,
  UOMConversionCreate,
  UOMConversionUpdate,
  UOMConversionListResponse,
  Currency,
  CurrencyCreate,
  CurrencyUpdate,
  CurrencyListResponse,
  ExchangeRate,
  ExchangeRateCreate,
  ExchangeRateUpdate,
  ExchangeRateListResponse,
} from "../types/uomCurrency.types";

// UOM Service
export const uomService = {
  create: (data: UOMCreate) => apiClient.post<UOM>("/uoms", data),
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    apiClient.get<UOMListResponse>("/uoms", { params }),
  getById: (id: string) => apiClient.get<UOM>(`/uoms/${id}`),
  update: (id: string, data: UOMUpdate) =>
    apiClient.patch<UOM>(`/uoms/${id}`, data),
  delete: (id: string) => apiClient.delete(`/uoms/${id}`),
};

// UOM Conversion Service
export const uomConversionService = {
  create: (data: UOMConversionCreate) =>
    apiClient.post<UOMConversion>("/uom-conversions", data),
  list: (params?: { page?: number; page_size?: number; item_id?: string }) =>
    apiClient.get<UOMConversionListResponse>("/uom-conversions", { params }),
  getById: (id: string) =>
    apiClient.get<UOMConversion>(`/uom-conversions/${id}`),
  update: (id: string, data: UOMConversionUpdate) =>
    apiClient.patch<UOMConversion>(`/uom-conversions/${id}`, data),
  delete: (id: string) => apiClient.delete(`/uom-conversions/${id}`),
};

// Currency Service
export const currencyService = {
  create: (data: CurrencyCreate) =>
    apiClient.post<Currency>("/currencies", data),
  list: (params?: { page?: number; page_size?: number; search?: string }) =>
    apiClient.get<CurrencyListResponse>("/currencies", { params }),
  getById: (id: string) => apiClient.get<Currency>(`/currencies/${id}`),
  update: (id: string, data: CurrencyUpdate) =>
    apiClient.patch<Currency>(`/currencies/${id}`, data),
  delete: (id: string) => apiClient.delete(`/currencies/${id}`),
};

// Exchange Rate Service
export const exchangeRateService = {
  create: (data: ExchangeRateCreate) =>
    apiClient.post<ExchangeRate>("/exchange-rates", data),
  list: (params?: {
    page?: number;
    page_size?: number;
    from_currency?: string;
    to_currency?: string;
    start_date?: string;
    end_date?: string;
  }) => apiClient.get<ExchangeRateListResponse>("/exchange-rates", { params }),
  getById: (id: string) => apiClient.get<ExchangeRate>(`/exchange-rates/${id}`),
  update: (id: string, data: ExchangeRateUpdate) =>
    apiClient.put<ExchangeRate>(`/exchange-rates/${id}`, data),
  delete: (id: string) => apiClient.delete(`/exchange-rates/${id}`),
};
```

---

## 7. Module Structure

```
src/
├── features/
│   └── master-data/
│       ├── components/
│       │   ├── uom/
│       │   │   ├── UOMForm.tsx              # Create/edit UOM
│       │   │   ├── UOMList.tsx              # Paginated list with search
│       │   │   └── UOMDetail.tsx            # Single UOM view
│       │   ├── uom-conversion/
│       │   │   ├── UOMConversionForm.tsx    # Create/edit conversion (item context)
│       │   │   ├── UOMConversionList.tsx    # List filtered by item_id
│       │   │   └── UOMConversionDetail.tsx
│       │   ├── currency/
│       │   │   ├── CurrencyForm.tsx         # Create/edit currency
│       │   │   ├── CurrencyList.tsx         # Paginated list with base currency badge
│       │   │   └── CurrencyDetail.tsx
│       │   └── exchange-rate/
│       │       ├── ExchangeRateForm.tsx     # Create/edit rate
│       │       ├── ExchangeRateList.tsx     # Filterable by currency pair + date range
│       │       └── ExchangeRateDetail.tsx
│       ├── hooks/
│       │   ├── useUOMs.ts
│       │   ├── useUOMConversions.ts
│       │   ├── useCurrencies.ts
│       │   └── useExchangeRates.ts
│       ├── services/
│       │   └── masterDataService.ts        # All 4 services above
│       └── types/
│           └── uomCurrency.types.ts
```

---

## 8. Integration Points

### Item Detail Page — UOM Conversion Tab

Show UOM conversions for the current item:

```typescript
const { data } = await uomConversionService.list({ item_id: itemId });
```

Allow adding new conversions from the item detail page with `item_id` pre-filled.

### Item Form — UOM Dropdown

Populate UOM dropdown from the UOM master:

```typescript
const { data } = await uomService.list({ page_size: 100 });
const options = data.uoms.map((u) => ({
  value: u.abbreviation,
  label: `${u.name} (${u.abbreviation})`,
}));
```

### Invoice / PO / Quotation — Currency Dropdown

Populate currency dropdown from the Currency master:

```typescript
const { data } = await currencyService.list({ page_size: 100 });
const options = data.currencies.map((c) => ({
  value: c.code,
  label: `${c.code} - ${c.name}${c.is_base_currency ? " (Base)" : ""}`,
}));
```

### Multi-Currency Transactions — Exchange Rate Lookup

When a user selects a non-base currency on a transaction, fetch the latest rate:

```typescript
const { data } = await exchangeRateService.list({
  from_currency: selectedCurrency,
  to_currency: baseCurrency,
  page_size: 1,
});
const latestRate = data.exchange_rates[0]?.rate;
```

---

## 9. UI Behavior Notes

- UOM `name` max 50 chars, `abbreviation` max 10 chars — enforce in form inputs
- Currency `code` must be exactly 3 uppercase letters — validate with `pattern="[A-Z]{3}"` and transform input to uppercase
- Only one currency can be `is_base_currency = true` per org — show a star/badge on the base currency in the list, and warn users when changing it
- Exchange Rate `effective_date` defaults to today — pre-fill the date picker
- Exchange Rate uses upsert — creating a rate for an existing (currency pair + date) updates it instead of failing
- Exchange Rate delete is permanent (hard delete) — show a confirmation dialog
- UOM, UOM Conversion, and Currency use soft delete — no confirmation needed beyond standard "Are you sure?"
- `conversion_factor` and `rate` must be positive — disable submit if value <= 0

---

## 10. Error Handling

All errors return:

```json
{ "detail": "Human-readable error message" }
```

Extract error message:

```typescript
catch (err: any) {
  const message = err.response?.data?.detail || "An error occurred";
}
```

Common status codes: `404` (not found), `409` (duplicate), `422` (validation error).
