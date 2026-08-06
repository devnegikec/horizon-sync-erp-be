## QR Code Parent-Child Relationship System

### 📊 Underlying Data Models

The system uses **3 models** to represent the hierarchy:

#### 1. `QRActivationTrack` — The Hierarchy Container Model

| Field             | Type           | Purpose                                                              |
| ----------------- | -------------- | -------------------------------------------------------------------- |
| `qr_type`         | `CharField`    | QR level: `"shipper"`, `"pallet"`, or `"container"`                  |
| `name`            | `CharField`    | Alphanumeric name (max 20 chars)                                     |
| `capacity`        | `IntegerField` | How many children this box can hold                                  |
| `serial_number`   | `CharField`    | Unique identifier (8 chars)                                          |
| `parent`          | `FK → self`    | **Dashboard hierarchy** — links child → parent within the same model |
| `parent_app`      | `FK → self`    | **App cascade hierarchy** — links child → parent via mobile app      |
| `app_cascade_map` | `BooleanField` | Flag: `True` when this parent has been cascaded in the app           |
| `qr_code_link`    | `URLField`     | URL to download the QR label                                         |

#### 2. `QRActivationParameters` — Individual Unit/Shipper Parameters

| Field                                                              | Type                     | Purpose                                                               |
| ------------------------------------------------------------------ | ------------------------ | --------------------------------------------------------------------- |
| `parent`                                                           | `FK → QRActivationTrack` | Links individual units to a **shipper-level** parent                  |
| `parent_app`                                                       | `FK → QRActivationTrack` | Links units to a parent via **app cascade**                           |
| `qr_cascade`                                                       | `BooleanField`           | `True` when all units in a dispatch batch are fully cascaded          |
| `qr_settings`                                                      | `BooleanField`           | Distinguishes settings templates (`True`) from actual units (`False`) |
| `dispatch_batch`, `manufacturing_date`, `expiry_date`, `mrp`, etc. | —                        | Product activation metadata                                           |

#### 3. `ProductItem` — The Physical QR Block

The atomic unit — each block has a `serial_number`, `qr_deactive`/`qr_deactive_unit` status flags, and scan counts.

---

### 🏗️ Three-Level Hierarchy

```
Container (topmost)
  └── Pallet (middle)
        └── Shipper (bottom)
              └── Individual Units (QRActivationParameters)
```

- **Container** → contains multiple **Pallets**
- **Pallet** → contains multiple **Shippers**
- **Shipper** → contains multiple individual dispatched units

---

### 🔗 Two Ways to Link Child QR Codes to a Parent

#### A. Dashboard-Side Linking (via `QRActivationTrackForm`)

When creating a new `QRActivationTrack` via the dashboard:

- **Creating a Shipper**: You select dispatch batches (`QRActivationParameters`) as children. The form calls:

  ```python
  QRActivationParameters.objects.filter(
      dispatch_batch__in=dispatch_ids,
      parent__isnull=True,
      qr_settings=False
  ).update(parent=instance_id)
  ```

  This sets the `parent` FK on all matching `QRActivationParameters` records.

- **Creating a Pallet**: You select existing shipper-level `QRActivationTrack` records. The form calls:

  ```python
  QRActivationTrack.objects.filter(id__in=child_ids).update(parent=instance_id)
  ```

- **Creating a Container**: Same pattern — select pallet-level `QRActivationTrack` records.

#### B. App-Side Cascade Linking (via REST API)

Three API endpoints handle mobile-app cascade:

| Endpoint               | Method              | Purpose                                                                             |
| ---------------------- | ------------------- | ----------------------------------------------------------------------------------- |
| `POST /api/scanqrs/`   | `QRScancascadeView` | Scans a QR code and validates it — returns its serial number for parenting          |
| `POST /api/child_qrs/` | `ChildQRView`       | Given a parent serial number, validates which children (by type) can be linked      |
| `POST /api/map_qrs/`   | `MappingchildView`  | **Performs the actual linking** — updates `parent_app` on children and marks parent |

The cascade logic in `MappingchildView`:

1. Looks up the parent by `serial_number`
2. Checks `capacity` — rejects if children exceed box capacity
3. Checks `app_cascade_map` — rejects if already cascaded
4. Based on parent's `qr_type`, updates the right model:
   - **Shipper parent** → updates `QRActivationParameters.parent_app`
   - **Pallet/Container parent** → updates `QRActivationTrack.parent_app`
5. Sets `parent.app_cascade_map = True`

The type validation in `ChildQRView`:

- **Shipper parent** → children must be `QRActivationParameters` serial numbers
- **Pallet parent** → children must be `QRActivationTrack` with `qr_type='shipper'`
- **Container parent** → children must be `QRActivationTrack` with `qr_type='pallet'`

---

### 🎯 Key Features

| Feature                    | Description                                                                                           |
| -------------------------- | ----------------------------------------------------------------------------------------------------- |
| **Capacity enforcement**   | Parent's `capacity` limits how many children can be cascaded                                          |
| **One-time cascade**       | `app_cascade_map` prevents re-cascading the same parent                                               |
| **Type-safe linking**      | Only the correct child type can be linked (shipper→pallet→container)                                  |
| **QR label download**      | `QRLabelDownloadView` returns the `qr_code_link` for a parent                                         |
| **Cascade history**        | `HistoryQRViewSet` (`/api/cascade-history/`) lists all QR codes with `app_cascade_map=True`           |
| **Batch cascade tracking** | `qr_cascade` flag on `QRActivationParameters` tracks whether all units in a dispatch batch are mapped |
| **Duplicate prevention**   | Both `parent__isnull` filter and unique constraint checks prevent double-linking                      |

---

### 📝 Summary

To link a child QR to a parent in the app, you call `POST /api/map_qrs/` with:

```json
{
  "parent_srnumber": "ABC12345",
  "srnumber": "CHILD001,CHILD002,CHILD003"
}
```

The system validates the type hierarchy (shipper → pallet → container), checks capacity, then updates the `parent_app` foreign key on all child records and flags the parent as cascaded via `app_cascade_map = True`.
