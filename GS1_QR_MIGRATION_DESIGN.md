# GS1 QR Migration — Design & Plan

> **Status**: Decisions locked — not yet implemented
> **Reference**: `bwmobile/docs/GS1_Offline_packing_and_aggregatino_guide.md` > **Date**: 2026-08-13

---

## 1. Goal

Adopt **GS1 Digital Link** identifiers for product QRs at two levels:

- **Unit level** — GTIN (AI `01`) + serial (AI `21`) = SGTIN
- **Master level** — SSCC (AI `00`) + contained GTIN (AI `02`) + count (AI `37`) + lot (AI `10`)

…while **preserving the existing ECDSA product-authentication flow** (the QSeal
app must still tell the user whether a scanned product is valid).

---

## 2. Decisions (locked)

| #   | Topic                     | Decision                                                                                                                 |
| --- | ------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| D1  | Authentication in GS1 URL | Append custom query params: `/01/{gtin}/21/{serial}?c={signature}&n={nonce}`. Signed message stays `"{serial}~{nonce}"`. |
| D2  | Backward compatibility    | Decoder + verify page accept **both** the old `/g/…` format and the new GS1 format.                                      |
| D3  | Master identity           | **SSCC replaces** `QSealTrack.serial_number` as the master's primary identity.                                           |

---

## 3. Current architecture (research findings)

### 3.1 QR generation (backend)

File: `core-service/app/utils/serial_generators.py`

- `sign_qr_item()` — signs `"{serial}~{timestamp_ms}"` with **ECDSA P-256 + SHA-256**
  (base64 DER signature), returns `(signature_b64, timestamp_ms)`.
- `build_qr_url()` — builds:
  ```
  {base_url}/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}
  ```
- `core-service/app/services/qr_product_service.py` (≈ line 520) stores the
  resulting URL as `ProductItem.token_id` (what actually gets printed).

### 3.2 Authentication (backend)

Endpoint: `POST /api/v1/qr-products/authenticate`
File: `core-service/app/api/v1/endpoints/qr_products.py` → `QRProductService.authenticate()`

Request: `{ "serial_number", "nonce", "cipher" }`

1. Look up `ProductItem` by `serial_number` (global, no org filter).
2. Check `qr_active` (post-activation).
3. Reconstruct message `"{serial_number}~{nonce}"`.
4. Verify ECDSA with `brand.public_key` (`key_service.verify_signature`).
5. On success → increment scan count, return `{ authentic, product_name, brand_name, gtin, serial_number }`.

### 3.3 Consumer verification (frontend)

Files:

- `apps/inventory/src/app/pages/PublicQRValidation.tsx`
- `apps/inventory/src/app/pages/QRVerifyPage.tsx`
- `apps/platform/src/app/pages/PublicQRValidation.tsx`

These parse the `/g/{gtin}/s/{serial}/{timestamp}?c={signature}` path and call
`POST /qr-products/authenticate`.

### 3.4 Inbound / put-away decoder (backend)

File: `core-service/app/services/qr_decoder.py`

- `_QR_URL_PATTERN` matches only `https?://…/g/{gtin}/s/{serial}/{nonce?}`.
- Also accepts a **bare serial** and a **JSON payload** (`{id, sku, qty, batch}`).

### 3.5 Master aggregation (current)

File: `core-service/app/models/qseal.py`

- `QSealTrack` — parent/master: `serial_number` (String(10)), `capacity`.
- `QSealParameters` — children: `serial_number`, `parent_id`, `dispatch_batch`.

---

## 4. Target formats

| Type          | New QR URL                                                           |
| ------------- | -------------------------------------------------------------------- |
| Unit (SGTIN)  | `https://{domain}/01/{gtin}/21/{serial}?c={signature}&n={nonce}`     |
| Master (SSCC) | `https://{domain}/00/{sscc}?02={contained_gtin}&37={count}&10={lot}` |

---

## 5. Gap analysis

| Area                     | Today                               | GS1 target                                 | Change                                    |
| ------------------------ | ----------------------------------- | ------------------------------------------ | ----------------------------------------- |
| Unit URL                 | `/g/{gtin}/s/{serial}/{ts}?c={sig}` | `/01/{gtin}/21/{serial}?c={sig}&n={nonce}` | `build_qr_url`, decoder, verify page      |
| Signature                | ECDSA on `{serial}~{ts}` in `?c=`   | keep, but nonce moves to `?n=`             | no crypto change                          |
| Master                   | `QSealTrack.serial_number`          | SSCC (AI `00`)                             | model + migration + generator             |
| Decoder                  | `/g/…` only                         | `/01/…`, `/00/…?02=…`                      | add GS1 parsing                           |
| Verify page              | parses `/g/…`                       | parses `/01/…`                             | frontend change                           |
| Mobile serial extraction | `/g/…/s/{serial}`                   | `/01/…/21/{serial}`                        | `qrHelpers`, inbound/direct-putaway hooks |

---

## 6. Files to change

### Backend — QR generation

- `core-service/app/utils/serial_generators.py`
  - `build_qr_url()` → emit `/01/{gtin}/21/{serial}?c={sig}&n={ts}`
  - add `build_master_sscc_url()` → `/00/{sscc}?02={gtin}&37={count}&10={lot}`
  - add `generate_sscc()` (18-digit SSCC with GS1 check digit)
  - `sign_qr_item()` unchanged

### Backend — authentication (no logic change)

- `core-service/app/services/qr_product_service.py` — `authenticate()` unchanged
  (message still `"{serial}~{nonce}"`, nonce now supplied via `?n=`).

### Backend — decoder

- `core-service/app/services/qr_decoder.py`
  - accept `/01/{gtin}/21/{serial}` (+ optional `/10/{lot}`)
  - accept `/00/{sscc}?02=…&37=…&10=…` (resolve master by SSCC)
  - keep `/g/…` and bare-serial and JSON for backward compatibility (D2)

### Backend — master / SSCC

- `core-service/app/models/qseal.py` — `QSealTrack`: replace/augment serial with `sscc`
- Alembic migration (add `sscc`, backfill if keeping existing masters)
- `core-service/app/services/qseal_service.py` — `scanQSeal` / `getLinkedUnits`
  resolve parent by SSCC
- master QR creation writes `/00/{sscc}?…` as the parent token

### Frontend — consumer verify

- `PublicQRValidation.tsx`, `QRVerifyPage.tsx` (inventory + platform)
  - parse `/01/{gtin}/21/{serial}?c=…&n=…` (keep `/g/…`)

### Mobile app (`bwmobile`)

- `src/components/putaway/qrHelpers.ts` — `extractSerial` / `isQSealUrl`
- `src/screens/InboundScreen.tsx` / `src/hooks/useInboundFlow.ts`
- `src/hooks/useDirectPutaway.ts`
  - extract serial from `/01/…/21/{serial}`
  - resolve parent QSeal by SSCC (`/00/{sscc}…`)

---

## 7. Implications / risks

- **SSCC replaces QSeal serial (D3)** — existing `QSealTrack` serials (e.g.
  `QSL29CF5FB`) stop matching unless existing master labels are reprinted.
- **Lookup switch** — `getLinkedUnits` / `scanQSeal` move from serial → SSCC.
- **Migration** — add `sscc` column; backfill existing masters only if they must
  stay valid (otherwise old masters become unreachable).

---

## 8. Remaining details to confirm (non-blocking)

1. **GTIN vs SKU** — today the URL uses `product.gtin`. Confirm it is a real GS1
   GTIN; if the internal SKU should also appear, it belongs in AI `240`.
2. **Serial length** — current generator emits 6-char alphanumerics (valid as
   GS1 AI `21`, which allows up to 20). Confirm no change needed.
3. **SSCC allocation** — which GS1 Company Prefix / extension digit to use for
   SSCC generation.

---

## 9. Suggested implementation order

1. `build_qr_url` + decoder (unit-level `/01/…`) — smallest, unblocks everything.
2. Frontend verify-page parsing (old + new).
3. Mobile serial extraction (old + new).
4. Master SSCC (model + migration + generator + qseal_service).
5. End-to-end test with a real GS1 label + authenticate call.
