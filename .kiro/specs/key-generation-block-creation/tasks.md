# Implementation Plan: Key Generation & QR Block Creation

## Overview

Incremental implementation of Brand management, ECDSA signing, and enhanced QR verification within the existing `core-service`. Each task builds on the previous, extending existing models, services, and endpoints. Property-based tests validate correctness properties from the design document.

## Tasks

- [x] 1. Add configuration and KeyService

  - [x] 1.1 Add BRAND_KEY_ENCRYPTION_SECRET to config

    - Add `brand_key_encryption_secret: str = ""` to `core-service/app/config.py` Settings class
    - Add `BRAND_KEY_ENCRYPTION_SECRET=your-32-byte-fernet-key-here` to `core-service/.env`
    - Add `qr_domain: str = "verify.example.com"` and `gcs_bucket: str = ""` to Settings
    - _Requirements: 12.2_

  - [x] 1.2 Implement KeyService

    - Create `core-service/app/services/key_service.py`
    - `generate_key_pair()` → returns (encrypted_private_key, public_key_hex) using ECDSA P-256 via `cryptography` library
    - `decrypt_private_key(encrypted_private: str)` → Fernet-decrypts and reconstructs `ec.EllipticCurvePrivateKey`
    - `sign_message(private_key, message: str)` → signs with ECDSA P-256 + SHA-256, returns base64 signature
    - `verify_signature(public_key_hex: str, message: str, signature_b64: str)` → returns bool
    - Public key serialized as uncompressed X9.62 hex (starts with "04", 130 hex chars)
    - _Requirements: 1.2, 1.3, 1.4, 12.1, 12.2, 12.4, 12.5_

  - [ ]\* 1.3 Write property tests for KeyService
    - **Property 1**: Key pair generation produces valid P-256 keys — public key is "04" prefix, 130 hex chars; decrypted private key derives same public key
    - **Property 2**: Encryption round-trip — encrypt then decrypt recovers original; encrypted form differs from plaintext
    - **Property 3**: Sign-then-verify round-trip — signing and verifying with matching keys succeeds; mismatched keys or tampered message fails
    - _Validates: Requirements 1.2, 1.3, 1.4, 7.3, 9.5, 12.1, 12.5_

- [x] 2. Create Brand model, repository, service, and schemas

  - [x] 2.1 Create Brand SQLAlchemy model

    - Create `core-service/app/models/brand.py` — Brand model with: id (UUID PK), organization_id (UUID, indexed, not null), name (String 256), short_code (String 256), public_key (String 512), private_key_encrypted (Text), created_by, updated_by, created_at, updated_at, deleted_at
    - Add `qr_products` relationship (one-to-many)
    - Register in `core-service/app/models/__init__.py`
    - _Requirements: 1.1, 11.2_

  - [x] 2.2 Add brand_id FK to QRProduct model

    - Add `brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True)` to `core-service/app/models/qr_product.py`
    - Add `brand = relationship("Brand", back_populates="qr_products")` relationship
    - _Requirements: 4.1_

  - [x] 2.3 Enhance QRBlock model

    - Rename `task_status` to `status` in `core-service/app/models/qr_block.py` (or add `status` alongside for migration)
    - Add `task_id = Column(String(255), nullable=True)`
    - Add `download_url = Column(Text, nullable=True)` (if not already `gcs_url`)
    - Add `completed_at = Column(DateTime(timezone=True), nullable=True)`
    - _Requirements: 5.1_

  - [x] 2.4 Enhance ProductItem model

    - Add `qr_active = Column(Boolean, default=True)` to `core-service/app/models/product_item.py`
    - Add `scan_count = Column(Integer, default=0)`
    - Add `last_scanned_at = Column(DateTime(timezone=True), nullable=True)`
    - Note: existing `secrete_code` column serves as `secret_code` for SecureCode QR type
    - _Requirements: 8.5, 9.3, 9.8_

  - [x] 2.5 Create QRCreditBalance and QRCreditLedger models

    - Add to `core-service/app/models/qr_credit.py`:
      - `QRCreditBalance`: id, organization_id (unique), total_credits, used_credits, balance_credits, updated_at
      - `QRCreditLedger`: id, organization_id (indexed), block_id (FK), quantity_deducted, balance_after, created_at
    - Register in `core-service/app/models/__init__.py`
    - _Requirements: 6.1, 6.5_

  - [x] 2.6 Generate Alembic migration

    - Run `alembic revision --autogenerate -m "add brands, enhance qr models, credit balance"` in `core-service/`
    - Verify migration includes: brands table, brand_id FK on qr_products, new columns on qr_blocks and product_items, qr_credit_balance and qr_credit_ledger tables
    - Apply migration with `alembic upgrade head`
    - _Requirements: 11.2_

  - [x] 2.7 Create Brand Pydantic schemas

    - Create `core-service/app/schemas/brand.py` with BrandCreate, BrandUpdate, BrandResponse, BrandListResponse
    - BrandResponse excludes private_key_encrypted, includes public_key
    - _Requirements: 2.3, 2.4, 3.1, 3.2_

  - [x] 2.8 Update QRProduct schemas

    - Add `brand_id: UUID | None = None` to QRProductCreate and QRProductResponse in `core-service/app/schemas/qr_product.py`
    - _Requirements: 4.1, 4.4_

  - [x] 2.9 Add AuthenticateRequest/Response schemas
    - Add to `core-service/app/schemas/qr_product.py`: AuthenticateRequest (serial_number, nonce, cipher), AuthenticateResponse (message, authentic, product_name, brand_name, gtin, serial_number)
    - _Requirements: 9.1, 9.6, 9.7_

- [x] 3. Implement Brand repository and service

  - [x] 3.1 Create BrandRepository

    - Create `core-service/app/repositories/brand_repository.py` with create, get_by_id, list (paginated, search), update methods
    - All queries filter by organization_id and deleted_at IS NULL
    - _Requirements: 2.1, 2.2, 2.5, 11.1_

  - [x] 3.2 Create BrandService

    - Create `core-service/app/services/brand_service.py`
    - `create()`: generates key pair via KeyService, creates brand in single transaction
    - `update()`: rejects public_key/private_key_encrypted in payload (422)
    - `get_by_id()`, `list()`: standard CRUD with org isolation
    - _Requirements: 1.1, 1.5, 1.6, 3.1, 3.2_

  - [ ]\* 3.3 Write property tests for Brand
    - **Property 4**: Brand response never exposes private key
    - **Property 5**: Tenant isolation on brand queries
    - **Property 6**: Permission-gated write operations
    - **Property 7**: Brand key fields are immutable
    - _Validates: Requirements 1.7, 2.3, 2.4, 2.5, 3.1, 3.2, 3.3, 11.1, 12.3_

- [x] 4. Create Brand API endpoints

  - [x] 4.1 Create brand endpoints

    - Create `core-service/app/api/v1/endpoints/brands.py` with:
      - POST `/` → `require_permission("brand.create")` → 201
      - GET `/` → `require_permission("brand.read")` → paginated list
      - GET `/{id}` → `require_permission("brand.read")` → single brand
      - PATCH `/{id}` → `require_permission("brand.update")` → updated brand
    - No DELETE endpoint
    - _Requirements: 1.1, 1.7, 2.1, 2.2, 3.1, 3.3, 3.4_

  - [x] 4.2 Register brand router
    - Add `from app.api.v1.endpoints import brands` to `core-service/app/api/v1/router.py`
    - Register with `api_router.include_router(brands.router, prefix="/brands", tags=["Brands"])`
    - _Requirements: 1.1_

- [x] 5. Checkpoint — Verify brands work end-to-end

  - Run tests, verify brand CRUD via Swagger UI, confirm key pair generation and private key exclusion from responses.

- [x] 6. Implement CreditService and enhance block generation

  - [x] 6.1 Create CreditRepository

    - Create `core-service/app/repositories/credit_repository.py` with get_balance, deduct (atomic), create_ledger_entry
    - _Requirements: 6.1, 6.3, 6.5_

  - [x] 6.2 Create CreditService

    - Create `core-service/app/services/credit_service.py` with check_balance (raises 422 if insufficient) and deduct_credits (atomic deduction + ledger entry)
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [x] 6.3 Implement serial number generation utilities

    - Create `core-service/app/utils/serial_generators.py` with generators for R6DAN (6-char random alphanumeric), R4DAN (4-char), S8DN (zero-padded 8-digit sequential), S10DN (zero-padded 10-digit sequential)
    - Create QR signing helper: `sign_qr_item(key_service, private_key, serial_number)` → returns (base64_signature, timestamp_ms)
    - Create QR URL builder: `build_qr_url(org_short_code, domain, gtin, serial_number, timestamp, signature)` → returns URL string
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 6.4 Enhance QRProductService.generate_block

    - Modify `core-service/app/services/qr_product_service.py` `generate_block()`:
      - Replace monthly credit check with CreditService.check_balance()
      - If product has brand_id: decrypt private key, sign each item, build URLs
      - If product has no brand_id: generate items as before (backward compatible)
      - Handle QR type-specific behavior: Static (same serial), SecureCode (12-char secret), OneTime (qr_active based on activation_method), Dual (two URLs per item)
      - Generate Excel file with QR data, upload to GCS
      - Update block status lifecycle: pending → in_progress → completed/failed
      - Deduct credits only on success via CreditService.deduct_credits()
    - _Requirements: 5.1-5.7, 6.3, 6.4, 7.1-7.9, 8.1-8.5_

  - [ ]\* 6.5 Write property tests for block generation and credits
    - **Property 11**: Block quantity and qr_type validation
    - **Property 12**: Credit balance gate
    - **Property 13**: Credits deducted only on successful generation
    - **Property 14**: Serial number format matches configured type
    - **Property 15**: Block generates correct number of unique items
    - **Property 16**: Block status lifecycle
    - **Property 17**: QR URL format
    - **Property 18**: Static QR uses same serial for all items
    - **Property 19**: SecureCode QR generates 12-char secret codes
    - _Validates: Requirements 5.3, 5.4, 6.1-6.5, 7.1-7.9, 8.2, 8.5_

- [x] 7. Checkpoint — Verify block generation with signing

  - Run tests, create a brand, create a product linked to the brand, generate a block, verify signed items are created.

- [x] 8. Implement cryptographic verification endpoint

  - [x] 8.1 Add authenticate method to QRProductService

    - Add `authenticate(self, organization_id: UUID, data: AuthenticateRequest) -> dict` to `core-service/app/services/qr_product_service.py`
    - Look up ProductItem by serial_number and organization_id
    - Load Brand via ProductItem → QRProduct → Brand relationship
    - Check qr_active for post-activation products (400 if inactive)
    - Reconstruct message: `{serial_number}~{nonce}`
    - Verify ECDSA signature using Brand's public_key via KeyService.verify_signature()
    - On valid: return authentic=True with product info, increment scan_count, update last_scanned_at
    - On invalid: return authentic=False with 400
    - For OneTime QR (qr_type "O"): set qr_active=False after first successful verification
    - _Requirements: 9.1-9.9, 8.4_

  - [x] 8.2 Add authenticate endpoint

    - Add POST `/authenticate` to `core-service/app/api/v1/endpoints/qr_products.py`
    - Public endpoint (no auth required), takes organization_id as query param
    - Returns AuthenticateResponse
    - _Requirements: 9.1, 9.9_

  - [ ]\* 8.3 Write property tests for verification
    - **Property 20**: OneTime QR deactivates after first verification
    - **Property 21**: Post-activation items require qr_active for verification
    - **Property 22**: Scan count increments on successful verification
    - _Validates: Requirements 8.4, 9.3, 9.4, 9.8_

- [x] 9. Update QRProduct endpoints for brand_id

  - [x] 9.1 Update QRProduct create/update logic

    - Modify `QRProductService.create_product()` to validate brand_id belongs to org when provided
    - Modify `QRProductService.update_product()` to reject brand_id in PATCH payload (422)
    - _Requirements: 4.2, 4.3_

  - [ ]\* 9.2 Write property tests for QRProduct-Brand linking
    - **Property 8**: brand_id is immutable after creation
    - **Property 9**: QRProduct creation validates brand ownership
    - _Validates: Requirements 4.2, 4.3_

- [x] 10. Final checkpoint — Full integration verification
  - Run all tests
  - End-to-end flow: Create Brand → Create QRProduct with brand_id → Generate signed Block → Authenticate QR code via public endpoint
  - Verify backward compatibility: QRProducts without brand_id still work with existing validate endpoint

## Notes

- Tasks marked with `*` are optional property-based tests and can be skipped for faster MVP
- All code lives within `core-service/` — no new microservice
- Uses synchronous SQLAlchemy (Session), matching existing codebase patterns
- No Celery dependency — block generation is synchronous (can be migrated to background tasks later)
- Auth uses `require_permission()` dependency, not role-based checks
- `organization_id` is used everywhere (not `tenant_id`)
- Existing QRProduct/QRBlock/ProductItem models are extended, not replaced
- Backward compatibility: products without brand_id continue working with existing validate endpoint
- The `cryptography` library needs to be added to project dependencies
