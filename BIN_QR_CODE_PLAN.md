# Bin Location QR Code — Implementation Plan

> **Date**: 2026-06-20
> **Goal**: Generate QR codes for bin locations so mobile app can scan them during inbound/outbound to identify the exact bin for put-away or picking.

---

## 1. Overview

```
┌──────────────────────────────────────────────────────────────┐
│  Admin prints bin QR labels → sticks on each bin             │
│                                                              │
│  Worker scans bin QR with mobile app                         │
│    → App decodes JSON payload                                │
│    → Knows: org, warehouse, location_id, full_path           │
│    → Uses for: put-away confirmation, pick start/finish      │
└──────────────────────────────────────────────────────────────┘
```

### Current state

| What exists | Where |
|-------------|-------|
| Worker QR codes (for login) | `identity-service` → `GET /identity/workers/{id}/qr-image` |
| `qrcode` library | Already installed in identity-service |
| Location hierarchy | `core-service` → `warehouse_locations` table (Zone→Aisle→Bay→Level→Bin) |
| `full_path` column | e.g. `Z01-A01-B01-L01-BN001` — already stored |
| Location scans | `POST /location-scans` — records start/finish at bin |

### What's missing

- No endpoint to generate a QR code FOR a bin location
- No standard QR payload format for locations
- No bulk label printing endpoint

---

## 2. QR Payload Design

### Format: JSON (same as existing QR decoder supports)

```json
{
  "type": "location",
  "org_id": "8614e0b8-3316-4f84-a6bb-92791ceacd23",
  "org_name": "Acme Logistics",
  "warehouse_id": "f2c7ea58-5bcf-408c-a506-755da6a67ba8",
  "warehouse_code": "WH-001",
  "warehouse_name": "Main Warehouse",
  "location_id": "0cbc00c4-7315-44e5-8fb3-687affa1e0ea",
  "full_path": "Z01-A01-B01-L01-BN001",
  "location_type": "bin",
  "location_code": "BN001"
}
```

### Why JSON?

1. **Already supported** — `core-service/app/services/qr_decoder.py` handles JSON natively
2. **Self-describing** — mobile app gets everything it needs without DB lookup
3. **Extensible** — can add fields later (e.g., `capacity`, `zone_name`)
4. **Human-readable** — admins can scan with any QR reader to verify

### Alternative: Short-code + API lookup

QR encodes just `location_id`, mobile app calls `GET /warehouse-locations/{id}`. Simpler QR but requires network. **Decision**: use JSON (self-contained, works offline).

---

## 3. API Design

### 3.1 Single Location QR

```
GET /api/v1/warehouse-locations/{location_id}/qr-image
Authorization: Bearer <token>

Response: image/png (330×330px QR code)
```

**Implementation**: core-service `warehouse_locations.py`

**Logic**:
1. Look up `WarehouseLocation` by ID
2. Look up parent `Warehouse` for name/code
3. Look up `Organization` for name
4. Build JSON payload
5. Generate QR PNG using `qrcode` library
6. Return `StreamingResponse`

### 3.2 Bulk Label Print (Optional — Phase 2)

```
POST /api/v1/warehouse-locations/qr-labels/bulk
Authorization: Bearer <token>
Body: { "location_ids": ["uuid1", "uuid2", ...] }

Response: application/pdf (printable sheet of QR labels)
```

### 3.3 QR Download by Warehouse/Zone (Optional — Phase 2)

```
GET /api/v1/warehouse-locations/qr-labels?warehouse_id=<uuid>&location_type=bin
Authorization: Bearer <token>

Response: application/zip (ZIP of PNG files, one per bin)
```

---

## 4. Files to Create/Modify

### core-service

| File | Action | Purpose |
|------|--------|---------|
| `app/api/v1/endpoints/warehouse_locations.py` | **Modify** | Add `GET /{location_id}/qr-image` endpoint |
| `app/services/layout_service.py` | **Modify** | Add `get_location_with_context()` method (loads org + warehouse) |
| `app/schemas/warehouse_location.py` | **Modify** | Add `LocationQRPayload` schema |
| `pyproject.toml` | **Modify** | Add `qrcode` + `Pillow` dependencies |

### Dependencies to add (core-service)

```
qrcode>=7.4
Pillow>=10.0
```

---

## 5. Implementation Steps

### Step 1: Add dependencies

Add `qrcode` and `Pillow` to `core-service/pyproject.toml`.

### Step 2: Add QR schema

```python
# core-service/app/schemas/warehouse_location.py

class LocationQRPayload(BaseModel):
    """QR code payload for a bin location"""
    type: str = "location"
    org_id: UUID
    org_name: str
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    location_id: UUID
    full_path: str
    location_type: str
    location_code: str
```

### Step 3: Add service method

```python
# core-service/app/services/layout_service.py

def get_location_qr_payload(self, location_id: UUID, organization_id: UUID) -> LocationQRPayload:
    """Build QR payload with org, warehouse, and location context."""
    location = self._get_location(location_id, organization_id)
    warehouse = self.db.query(Warehouse).filter(Warehouse.id == location.warehouse_id).first()
    org = self.db.query(Organization).filter(Organization.id == organization_id).first()

    return LocationQRPayload(
        org_id=organization_id,
        org_name=org.name if org else "",
        warehouse_id=location.warehouse_id,
        warehouse_code=warehouse.code if warehouse else "",
        warehouse_name=warehouse.name if warehouse else "",
        location_id=location.id,
        full_path=location.full_path or "",
        location_type=location.location_type,
        location_code=location.code,
    )
```

### Step 4: Add endpoint

```python
# core-service/app/api/v1/endpoints/warehouse_locations.py

@router.get(
    "/{location_id}/qr-image",
    responses={404: {"description": "Location not found"}},
    summary="Generate QR code image for a bin location",
)
async def get_location_qr_image(
    location_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Generate a printable QR code for a bin location.

    The QR encodes org, warehouse, and full bin path as JSON.
    Mobile app scans this to identify the exact bin during inbound/outbound.
    """
    layout_service = LayoutService(db)
    payload = layout_service.get_location_qr_payload(location_id, current_user.organization_id)

    import qrcode, io
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(payload.model_dump_json())
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(
        buf,
        media_type="image/png",
        headers={"Content-Disposition": f"inline; filename=bin-qr-{payload.full_path}.png"},
    )
```

### Step 5: Mobile App Integration

The mobile app's existing QR scanner already handles JSON payloads (via `qr_decoder.py`). For location QR codes:

```typescript
// Mobile app — on QR scan
function onQRScanned(qrText: string) {
  const payload = JSON.parse(qrText);

  if (payload.type === "location") {
    // Worker scanned a bin QR during put-away or picking
    setCurrentLocation({
      locationId: payload.location_id,
      fullPath: payload.full_path,
      warehouseId: payload.warehouse_id,
      warehouseName: payload.warehouse_name,
    });

    // Confirm: "You are at Z01-A01-B01-L01-BN001 in Main Warehouse"
    // Continue with put-away or pick operation
  }
}
```

---

## 6. Frontend (Admin Portal) Integration

### Print QR Labels button

In the warehouse location tree view, add a QR icon next to each bin:

```
┌──────────────────────────────────────────────────────┐
│  Warehouse Locations — Main Warehouse                │
│                                                      │
│  ▼ Zone Z-01 (Receiving)                             │
│    ▼ Aisle A-01                                       │
│      ▼ Bay B-01                                       │
│        ▼ Level L-01                                   │
│          ■ BN-001  [ 📱 QR ]  [ ✏️ Edit ]            │
│          ■ BN-002  [ 📱 QR ]  [ ✏️ Edit ]            │
│          ■ BN-003  [ 📱 QR ]  [ ✏️ Edit ]            │
└──────────────────────────────────────────────────────┘
```

Clicking the QR icon opens a print modal with:
- QR code image
- Location path text below
- "Print Label" button
- "Download PNG" button

---

## 7. QR Code Label Design (Physical Print)

```
┌─────────────────────────┐
│                         │
│   ██████████████████    │
│   ██ ████ ██ ████ ██    │
│   ██ ████ ██ ████ ██    │  ← QR Code
│   ██████████████████    │
│                         │
│  Main Warehouse          │
│  Z01-A01-B01-L01-BN001   │  ← Human-readable text
│                         │
└─────────────────────────┘
     5cm × 5cm label
```

---

## 8. Summary

| Deliverable | Service | Effort |
|-------------|---------|--------|
| `GET /warehouse-locations/{id}/qr-image` | core-service | 1 endpoint + 1 service method |
| QR payload schema | core-service | 1 Pydantic model |
| `qrcode` + `Pillow` dependency | core-service | `pyproject.toml` |
| Frontend QR icon + print modal | Admin Portal | UI component |
| Mobile app location QR handler | Mobile App | Parse `type: "location"` JSON |

**Total backend effort**: ~50 lines of new code across 3 files.
