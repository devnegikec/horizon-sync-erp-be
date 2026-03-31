# FastAPI Microservice: Product & QR Service

(Full document content — backend migration plan)

## Purpose and goals
- Extract QR block generation (cryptoblocks) from Django monolith into a dedicated FastAPI microservice.
- Make block generation asynchronous, tenant-aware, and scalable (Celery/RabbitMQ or Redis).
- Preserve existing QR types, signing/verification semantics (ECDSA), Excel generation, and storage (GCS).
- Provide clear API surface for the frontend and other services (create block, block status, list items, verify QR).

## Scope
- Implement endpoints for:
  - Create Block (validate credits, create Block record, queue generation)
  - Get Block status and download URL
  - List Block items (pagination)
  - Verify QR signature / authenticate a scanned QR (public endpoint)
  - Short URL redirect handler if required
- Background Celery tasks include block generation and helpers (serial generation, long-url builder, shortener).

## Data model (core)
- Brand: id, name, public_key, private_key_encrypted, tenant_id, created_at
- Product: id, brand_id, gtin, name, activation_method, serialnumformat, tenant_id
- Block (Order): id, product_id, tenant_id, created_by, quantity, qr_type, status, download_url, completed_at
- ProductItem: id, block_id, product_id, tenant_id, serial_number, secret_code, long_url, short_url, signature, timestamp, qr_image_uri, is_active
- QRCredit / QRCreditUsage: tenant_id, total_credits, used_credits, ledger

## API contract (examples)
- POST /api/v1/blocks
- GET /api/v1/blocks/{id}
- GET /api/v1/blocks/{id}/items
- POST /api/v1/products/authenticate

## Internal signing & URL format
- long_url = https://\{tenant\}.\{domain\}/g/\{gtin\}/s/\{serial\}/\{timestamp\}\?c\=\{base64_signature\}
- Use cryptography for ECDSA (P-256 recommended) and Fernet/KMS for private key encryption.

## Asynchronous generation tasks
- block_qr orchestrates serial generation, signing, URL shortening, QR image generation, Excel writing, upload to GCS, and final DB updates.

## Implementation details & libraries
- FastAPI, SQLAlchemy, Alembic, Celery, qrcode, openpyxl/xlsxwriter, google-cloud-storage, cryptography.

## Migration checklist & milestones
- M1: Design & infra
- M2: Data model & migrations
- M3: Signing utils & Key mgmt
- M4: Core API endpoints
- M5: Celery worker & block_qr orchestration
- M6: Integrations
- M7: Credit system & ledger
- M8: Verification endpoint & tests
- M9: Load tests, monitoring & deployment
- M10: Cutover & rollback

