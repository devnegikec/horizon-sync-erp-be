# QR Code Image in Excel - Implementation Guide

## Overview

This document describes the implementation of QR code image embedding in Excel files for QR block downloads.

## Feature Description

When creating a QR block, users can now set `qr_image: true` to include actual QR code images in the downloaded Excel file, in addition to the QR URLs.

## Implementation Details

### 1. Database Schema

The `qr_blocks` table already has the `qr_image` field:

```sql
qr_image BOOLEAN DEFAULT FALSE
```

### 2. API Request

When creating a QR block via `POST /api/v1/qr-products/{product_id}/blocks`:

```json
{
  "batch": "BATCH-2025-01",
  "quantity": 500,
  "qr_type": "D",
  "qr_image": true, // ← Set to true to include QR images
  "serial_prefix": "PROD",
  "sr_number_type": "S8DN"
}
```

### 3. Excel Generation Logic

#### Updated `_build_excel()` Function

Location: `core-service/app/services/qr_product_service.py`

**Key Changes:**

1. **New Parameter**: Added `include_qr_image: bool = False` parameter
2. **Dynamic Headers**: Headers change based on QR type and whether images are included
3. **QR Image Generation**: Calls `_generate_qr_image()` to create QR code images
4. **Image Embedding**: Uses `openpyxl.drawing.image.Image` to embed images in cells
5. **Row Height Adjustment**: Sets row height to 75 points (100 pixels) when images are included
6. **Column Width**: Sets image column width to 15 units

#### New `_generate_qr_image()` Function

Generates QR code images using the `qrcode` library:

```python
def _generate_qr_image(data: str):
    """Generate a QR code image and return it as a BytesIO object."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
```

#### New `_build_excel_for_block()` Method

Added to `QRProductService` class to support the async task:

```python
def _build_excel_for_block(
    self, block_id: UUID, organization_id: UUID
) -> tuple[bytes, str]:
    """
    Generate Excel file for a block (used by async task).
    This is an alias for get_block_excel_stream for backward compatibility.
    """
    return self.get_block_excel_stream(block_id, organization_id)
```

### 4. Excel Layout by QR Type

#### Standard Types (D, S, O)

**Without Images:**
| QR URL | Serial Number |
|--------|---------------|

**With Images:**
| QR Image | QR URL | Serial Number |
|----------|--------|---------------|
| [QR PNG] | https://... | PROD-00000001 |

#### Dual Type (B)

**Without Images:**
| URL (Overt) | URL (Covert) | Serial Number |
|-------------|--------------|---------------|

**With Images:**
| QR Image (Overt) | URL (Overt) | QR Image (Covert) | URL (Covert) | Serial Number |
|------------------|-------------|-------------------|--------------|---------------|
| [QR PNG] | https://... | [QR PNG] | https://... | PROD-00000001 |

#### Secure Code Type (SC)

**Without Images:**
| QR URL | Serial Number | Secret Code |
|--------|---------------|-------------|

**With Images:**
| QR Image | QR URL | Serial Number | Secret Code |
|----------|--------|---------------|-------------|
| [QR PNG] | https://... | PROD-00000001 | ABC123XYZ789 |

## Technical Specifications

### QR Code Image Properties

- **Format**: PNG
- **Size**: 100x100 pixels
- **Error Correction**: Level L (Low - 7% recovery)
- **Box Size**: 10 pixels per module
- **Border**: 4 modules
- **Colors**: Black on white background

### Excel Cell Properties

- **Row Height**: 75 points (when images included)
- **Image Column Width**: 15 units
- **Text Column Width**: 50 units
- **Header Font**: Bold, centered

## Dependencies

Required Python packages (already installed):

```txt
qrcode[pil]==7.4.2
openpyxl==3.1.5
```

## Performance Considerations

### Impact of Including Images

1. **Generation Time**: Increases by ~2-3x due to QR image generation
2. **File Size**: Increases significantly (PNG images add ~1-2KB per QR code)
3. **Memory Usage**: Higher during generation (images held in memory)

### Recommendations

- **Small Batches (<1000)**: Safe to use `qr_image: true`
- **Medium Batches (1000-5000)**: Consider if images are necessary
- **Large Batches (>5000)**: Use `qr_image: false` for faster generation

## Usage Examples

### Example 1: Create Block with QR Images

```bash
curl -X POST "http://localhost:8001/api/v1/qr-products/{product_id}/blocks" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "batch": "BATCH-2025-01",
    "quantity": 100,
    "qr_type": "D",
    "qr_image": true,
    "serial_prefix": "PROD",
    "sr_number_type": "S8DN"
  }'
```

### Example 2: Create Block without QR Images (Default)

```bash
curl -X POST "http://localhost:8001/api/v1/qr-products/{product_id}/blocks" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "batch": "BATCH-2025-02",
    "quantity": 5000,
    "qr_type": "D",
    "qr_image": false,
    "serial_prefix": "PROD",
    "sr_number_type": "S8DN"
  }'
```

### Example 3: Download Excel File

```bash
curl -X GET "http://localhost:8001/api/v1/qr-products/blocks/{block_id}/download" \
  -H "Authorization: Bearer {token}"
```

Response:

```json
{
  "signed_url": "https://storage.googleapis.com/...",
  "expires_at": "2025-01-15T11:30:00Z"
}
```

## Testing

### Manual Testing Steps

1. **Create a block with images:**

   ```bash
   POST /api/v1/qr-products/{product_id}/blocks
   {
     "batch": "TEST-IMG-001",
     "quantity": 10,
     "qr_image": true
   }
   ```

2. **Wait for completion:**

   ```bash
   GET /api/v1/qr-products/blocks/{block_id}
   # Wait until status === "completed"
   ```

3. **Download the Excel file:**

   ```bash
   GET /api/v1/qr-products/blocks/{block_id}/download
   ```

4. **Verify Excel contents:**
   - Open the downloaded .xlsx file
   - Check that QR images are visible in the first column
   - Verify images are scannable (use phone camera)
   - Confirm URLs match the QR codes

### Automated Testing

```python
def test_qr_block_with_images():
    # Create block with qr_image=True
    response = client.post(
        f"/api/v1/qr-products/{product_id}/blocks",
        json={
            "batch": "TEST-001",
            "quantity": 5,
            "qr_image": True,
        }
    )
    assert response.status_code == 201
    block_id = response.json()["id"]

    # Wait for completion
    # ... polling logic ...

    # Download Excel
    download_response = client.get(
        f"/api/v1/qr-products/blocks/{block_id}/download"
    )
    assert download_response.status_code == 200

    # Verify Excel has images
    # ... openpyxl verification logic ...
```

## Troubleshooting

### Issue: Images Not Appearing in Excel

**Possible Causes:**

1. `qr_image` was set to `false` during block creation
2. Excel viewer doesn't support embedded images
3. File corruption during download

**Solution:**

- Verify `block.qr_image === true` in the database
- Try opening with Microsoft Excel or LibreOffice Calc
- Re-download the file

### Issue: Generation Takes Too Long

**Possible Causes:**

1. Large quantity with `qr_image: true`
2. Insufficient server resources

**Solution:**

- Use `qr_image: false` for large batches
- Increase Celery worker concurrency
- Monitor task progress via Flower (http://localhost:5555)

### Issue: File Size Too Large

**Possible Causes:**

1. High quantity with images enabled

**Solution:**

- Split into multiple smaller blocks
- Use `qr_image: false` and generate images separately if needed

## Future Enhancements

1. **Configurable Image Size**: Allow users to specify QR image dimensions
2. **Image Format Options**: Support JPEG for smaller file sizes
3. **Batch Compression**: Compress Excel files before upload to GCS
4. **Progressive Download**: Stream Excel generation for very large blocks
5. **Image Caching**: Cache generated QR images to speed up regeneration

## Related Files

- `core-service/app/services/qr_product_service.py` - Main implementation
- `core-service/app/tasks/qr_generation.py` - Async task
- `core-service/app/schemas/qr_product.py` - API schemas
- `core-service/app/models/qr_block.py` - Database model
- `core-service/requirements.txt` - Dependencies

## References

- [qrcode library documentation](https://pypi.org/project/qrcode/)
- [openpyxl documentation](https://openpyxl.readthedocs.io/)
- [QR Code specification](https://www.qrcode.com/en/about/standards.html)
