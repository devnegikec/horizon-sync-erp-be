# Design Document: Key Generation & QR Block Creation

## Overview

This design extends the existing `core-service` Product & QR module with ECDSA P-256 digital signing capabilities. It adds a Brand entity with encrypted key pairs, enhances QR block generation with cryptographic signing, and upgrades scan verification from simple lookup to signature-based authentication.

The changes integrate into the existing codebase patterns:

- Synchronous SQLAlchemy with `Session` (not async)
- Repository pattern with `__init__(self, db: Session)`
- Service pattern with `__init__(self, db: Session)` creating repos internally
- Permission-based auth via `require_permission()` dependency
- `organization_id` for tenant isolation (not `tenant_id`)
- Pydantic v2 schemas with `model_config = {"from_attributes": True}`

### Core Capabilities

1. **Brand Management with ECDSA Key Pairs** — New Brand entity owns ECDSA P-256 key pairs. Private keys are Fernet-encrypted at rest.
2. **QRProduct → Brand Linking** — Existing QRProducts gain an optional `brand_id` FK. Products without a brand continue working as before.
3. **Signed QR Block Generation** — Block generation signs each ProductItem with the Brand's private key when a brand is linked.
4. **Cryptographic Scan Verification** — New `/authenticate` endpoint verifies ECDSA signatures from scanned QR codes.
5. **Enhanced QR Credit System** — New `QRCreditBalance` and `QRCreditLedger` tables replace the monthly-sum approach.

### Key Design Decisions

| Decision                                      | Rationale                                                                  |
| --------------------------------------------- | -------------------------------------------------------------------------- |
| ECDSA P-256 over P-192                        | Stronger security; P-192 is deprecated by NIST                             |
| `cryptography` library over `ecdsa`           | Audited, maintained, supports P-256 natively                               |
| Fernet for private key encryption             | Symmetric, simple, built into `cryptography`; single env secret            |
| Synchronous key generation                    | Key pairs are small/fast; matches existing sync SQLAlchemy patterns        |
| Synchronous block generation (initially)      | No Celery configured in project; can be migrated to background tasks later |
| Brand-level keys (not Org-level)              | Multiple brands per org may need independent signing identities            |
| Optional brand_id on QRProduct                | Backward compatible — existing products without brands keep working        |
| Extend existing service, not new microservice | All QR logic already lives in core-service; no need for a separate service |

## Architecture

```
core-service/
├── app/
│   ├── api/v1/endpoints/
│   │   ├── brands.py                    # NEW — Brand CRUD endpoints
│   │   ├── qr_products.py              # MODIFIED — add brand_id, authenticate endpoint
│   │   └── ...
│   ├── models/
│   │   ├── brand.py                     # NEW — Brand model with key pair
│   │   ├── qr_product.py               # MODIFIED — add brand_id FK
│   │   ├── qr_block.py                 # MODIFIED — add status, task_id, download_url
│   │   ├── product_item.py             # MODIFIED — add qr_active, scan_count, last_scanned_at
│   │   ├── qr_credit.py                # MODIFIED — add QRCreditBalance, QRCreditLedger
│   │   └── ...
│   ├── schemas/
│   │   ├── brand.py                     # NEW — Brand request/response schemas
│   │   ├── qr_product.py               # MODIFIED — add brand_id, authenticate schemas
│   │   └── ...
│   ├── services/
│   │   ├── key_service.py               # NEW — ECDSA key generation & encryption
│   │   ├── brand_service.py             # NEW — Brand CRUD orchestration
│   │   ├── credit_service.py            # NEW — Credit balance & ledger management
│   │   ├── qr_product_service.py        # MODIFIED — signed block generation, authenticate
│   │   └── ...
│   ├── repositories/
│   │   ├── brand_repository.py          # NEW — Brand data access
│   │   ├── credit_repository.py         # NEW — Credit balance & ledger data access
│   │   ├── qr_product_repository.py     # MODIFIED — enhanced queries
│   │   └── ...
│   └── config.py                        # MODIFIED — add BRAND_KEY_ENCRYPTION_SECRET
```

### Request Flow: Brand Creation

```
Client → POST /api/v1/brands {name, short_code}
  → require_permission("brand.create")
  → BrandService.create(db, organization_id, user_id, data)
    → KeyService.generate_key_pair()
      → returns (encrypted_private_key, public_key_hex)
    → BrandRepository.create(db, brand_data)
      → INSERT INTO brands
  → return 201 BrandResponse (excludes private_key_encrypted)
```

### Request Flow: Signed QR Block Creation

```
Client → POST /api/v1/qr-products/{product_id}/blocks {batch, quantity, ...}
  → require_permission("qr_product.create")
  → QRProductService.generate_block(product_id, data, organization_id, user_id)
    → Validate product exists and belongs to org
    → CreditService.check_balance(db, organization_id, quantity)
    → Create Block record (status="pending")
    → If product has brand_id:
      → KeyService.decrypt_private_key(brand.private_key_encrypted)
      → For each item: generate serial, sign message, build URL, create ProductItem
    → Else:
      → For each item: generate serial, create ProductItem (no signing)
    → Generate Excel, upload to GCS
    → Update Block status to "completed", set download_url
    → CreditService.deduct_credits(db, organization_id, block_id, quantity)
  → return 201 BlockResponse
```

### Request Flow: Cryptographic Verification

```
Scanner → POST /api/v1/qr-products/authenticate {serial_number, nonce, cipher}
  → No auth required (public endpoint)
  → QRProductService.authenticate(organization_id, data)
    → Look up ProductItem by serial_number
    → Load Brand via ProductItem → QRProduct → Brand
    → Check qr_active (for post-activation products)
    → Reconstruct message: "{serial_number}~{nonce}"
    → Verify ECDSA signature using Brand's public_key
    → Increment scan_count, update last_scanned_at
  → return 200 AuthenticateResponse
```

## Components and Interfaces

### Service Interfaces

#### KeyService

Stateless utility for ECDSA key pair generation and private key encryption/decryption.

```python
class KeyService:
    def __init__(self, encryption_secret: str): ...

    def generate_key_pair(self) -> tuple[str, str]:
        """Returns (encrypted_private_key, public_key_hex).
        Uses ECDSA P-256 (SECP256R1) via cryptography library.
        Private key is Fernet-encrypted before return.
        Public key is uncompressed X9.62 hex (starts with '04', 130 hex chars)."""

    def decrypt_private_key(self, encrypted_private: str) -> ec.EllipticCurvePrivateKey:
        """Decrypts stored private key and reconstructs the signing key object."""

    def sign_message(self, private_key: ec.EllipticCurvePrivateKey, message: str) -> str:
        """Signs message with ECDSA P-256 + SHA-256, returns base64-encoded signature."""

    def verify_signature(self, public_key_hex: str, message: str, signature_b64: str) -> bool:
        """Verifies ECDSA signature. Returns True if valid, False otherwise."""
```

#### BrandService

Orchestrates brand CRUD with automatic key generation on creation. Follows existing service pattern.

```python
class BrandService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = BrandRepository(db)
        self.key_service = KeyService(settings.brand_key_encryption_secret)

    def create(self, data: BrandCreate, organization_id: UUID, user_id: UUID) -> Brand: ...
    def get_by_id(self, brand_id: UUID, organization_id: UUID) -> Brand: ...
    def list(self, organization_id: UUID, page: int, page_size: int, search: str | None) -> tuple[list[Brand], dict]: ...
    def update(self, brand_id: UUID, data: BrandUpdate, organization_id: UUID, user_id: UUID) -> Brand: ...
```

#### CreditService

Pre-flight credit checks and post-generation deduction with ledger audit trail.

```python
class CreditService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CreditRepository(db)

    def check_balance(self, organization_id: UUID, required: int) -> bool:
        """Returns True if balance_credits >= required. Raises HTTPException(422) otherwise."""

    def deduct_credits(self, organization_id: UUID, block_id: UUID, quantity: int) -> None:
        """Atomically deducts credits and writes ledger entry."""
```

#### Enhanced QRProductService (modified)

Extends existing service with signed block generation and cryptographic authentication.

```python
class QRProductService:
    # Existing methods unchanged...

    def generate_block(self, product_id, data, organization_id, user_id) -> QRBlock:
        """Enhanced: signs items when product has brand_id."""

    def authenticate(self, organization_id: UUID, data: AuthenticateRequest) -> dict:
        """NEW: ECDSA signature verification for QR scans."""
```

### Repository Interfaces

All repositories follow the existing pattern: `__init__(self, db: Session)`, all queries filter by `organization_id`.

```python
class BrandRepository:
    def __init__(self, db: Session): ...
    def create(self, data: dict) -> Brand: ...
    def get_by_id(self, brand_id: UUID, organization_id: UUID) -> Brand | None: ...
    def list(self, organization_id: UUID, page: int, page_size: int, search: str | None) -> tuple[list[Brand], int]: ...
    def update(self, brand: Brand, data: dict) -> Brand: ...

class CreditRepository:
    def __init__(self, db: Session): ...
    def get_balance(self, organization_id: UUID) -> QRCreditBalance | None: ...
    def deduct(self, organization_id: UUID, amount: int) -> None: ...
    def create_ledger_entry(self, data: dict) -> QRCreditLedger: ...
```

### Pydantic Schemas

#### Brand Schemas

```python
class BrandCreate(BaseModel):
    name: str = Field(..., max_length=256)
    short_code: str = Field(..., max_length=256)

class BrandUpdate(BaseModel):
    name: str | None = Field(None, max_length=256)
    short_code: str | None = Field(None, max_length=256)

class BrandResponse(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    short_code: str
    public_key: str
    created_by: UUID | None
    created_at: datetime
    updated_at: datetime
    # private_key_encrypted is NEVER included
    model_config = {"from_attributes": True}

class BrandListResponse(BaseModel):
    brands: list[BrandResponse]
    pagination: dict[str, Any]
```

#### Enhanced QRProduct Schemas (modified)

```python
class QRProductCreate(QRProductBase):
    brand_id: UUID | None = None  # NEW optional field

class QRProductResponse(QRProductBase):
    # ... existing fields ...
    brand_id: UUID | None = None  # NEW
```

#### Enhanced Block Schemas (modified)

```python
class QRBlockCreate(BaseModel):
    batch: str = Field(..., max_length=50)
    quantity: int = Field(..., gt=0, le=10000)
    qr_type: Literal["D", "S", "B", "O", "SC"] | None = None  # NEW validation
    serial_prefix: str | None = None
    sr_number_type: Literal["R6DAN", "R4DAN", "S8DN", "S10DN"] | None = None
    qr_image: bool = False
    # ... existing optional fields ...

class QRBlockResponse(BaseModel):
    # ... existing fields ...
    status: str  # replaces task_status
    task_id: str | None = None  # NEW
    download_url: str | None = None  # NEW
    completed_at: datetime | None = None  # NEW
```

#### Authentication Schemas (new)

```python
class AuthenticateRequest(BaseModel):
    serial_number: str
    nonce: str  # timestamp
    cipher: str  # base64 signature

class AuthenticateResponse(BaseModel):
    message: str
    authentic: bool
    product_name: str | None = None
    brand_name: str | None = None
    gtin: str | None = None
    serial_number: str | None = None
```

### API Endpoints Summary

| Method | Path                                    | Description                       | Auth                |
| ------ | --------------------------------------- | --------------------------------- | ------------------- |
| POST   | `/api/v1/brands`                        | Create brand + key pair           | `brand.create`      |
| GET    | `/api/v1/brands`                        | List brands                       | `brand.read`        |
| GET    | `/api/v1/brands/{id}`                   | Get brand                         | `brand.read`        |
| PATCH  | `/api/v1/brands/{id}`                   | Update brand metadata             | `brand.update`      |
| POST   | `/api/v1/qr-products/authenticate`      | Verify QR signature               | public              |
| POST   | `/api/v1/qr-products/{id}/blocks`       | Create block (existing, enhanced) | `qr_product.create` |
| GET    | `/api/v1/qr-products/{id}/blocks`       | List blocks (existing)            | `qr_product.read`   |
| GET    | `/api/v1/qr-products/blocks/{id}/items` | List block items (existing)       | `qr_product.read`   |

## Data Models

### Entity Relationship Diagram

```
Brand (NEW)
├── id: UUID PK
├── organization_id: UUID (indexed, not null)
├── name: String(256)
├── short_code: String(256)
├── public_key: String(512)
├── private_key_encrypted: Text
├── created_by, updated_by: UUID
├── created_at, updated_at, deleted_at: DateTime
└── relationships: qr_products[]

QRProduct (MODIFIED)
├── ... existing fields ...
├── brand_id: UUID FK → brands.id (NEW, nullable)
└── relationships: brand, qr_blocks[], product_items[]

QRBlock (MODIFIED)
├── ... existing fields ...
├── status: String(20) — replaces task_status
├── task_id: String(255) (NEW)
├── download_url: Text (NEW)
├── completed_at: DateTime (NEW)
└── relationships: product, product_items[], credit_usage[]

ProductItem (MODIFIED)
├── ... existing fields ...
├── qr_active: Boolean (NEW, default True)
├── scan_count: Integer (NEW, default 0)
├── last_scanned_at: DateTime (NEW)
├── secret_code: String(50) — existing secrete_code field reused
└── relationships: product, block, scan_events[]

QRCreditBalance (NEW)
├── id: UUID PK
├── organization_id: UUID (unique, not null)
├── total_credits: Integer
├── used_credits: Integer
├── balance_credits: Integer
└── updated_at: DateTime

QRCreditLedger (NEW)
├── id: UUID PK
├── organization_id: UUID (indexed, not null)
├── block_id: UUID FK → qr_blocks.id
├── quantity_deducted: Integer
├── balance_after: Integer
├── created_at: DateTime
```

### Model Details

#### Brand (NEW)

- `organization_id`: Non-null, indexed. All queries filter by this.
- `public_key`: Uncompressed X9.62 hex-encoded ECDSA P-256 public key (max 512 chars). Exposed in API responses.
- `private_key_encrypted`: Fernet-encrypted hex of the private key scalar. Never exposed in API responses.
- Follows existing model patterns: UUID PK, audit fields (created_by, updated_by, created_at, updated_at, deleted_at).
- No DELETE endpoint. Keys persist indefinitely.

#### QRProduct (MODIFIED)

- `brand_id`: Optional FK to `brands.id`. Nullable for backward compatibility.
- Immutable after creation (PATCH rejects brand_id changes).

#### QRBlock (MODIFIED)

- `status`: Replaces `task_status`. Lifecycle: `pending` → `in_progress` → `completed` | `failed`.
- `task_id`: Reserved for future Celery integration.
- `download_url`: GCS URL for the generated Excel file, set on completion.

#### ProductItem (MODIFIED)

- `qr_active`: Defaults to `True` for `pre` activation, `False` for `post`. Used by verification.
- `scan_count`: Replaces `scans` for clarity. Incremented on each successful verification.
- `last_scanned_at`: Replaces `scan_date` for clarity.
- `secret_code`: Reuses existing `secrete_code` column for SecureCode QR type.

## Correctness Properties

### Property 1: Key pair generation produces valid P-256 keys

For any brand creation, the generated public key SHALL be a valid uncompressed X9.62 P-256 point (hex string starting with "04", 130 hex characters), and the encrypted private key SHALL decrypt to a valid P-256 private scalar that derives the same public key.

**Validates: Requirements 1.1, 1.2, 1.4**

### Property 2: Private key encryption round-trip

For any ECDSA P-256 private key generated by KeyService, encrypting then decrypting SHALL recover the original private key value. The encrypted form SHALL NOT equal the plaintext hex.

**Validates: Requirements 1.3, 12.1, 12.5**

### Property 3: Sign-then-verify round-trip

For any serial number and timestamp, signing `{serial_number}~{timestamp}` with a brand's private key and verifying with the corresponding public key SHALL succeed. Verifying with a different key or tampered message SHALL fail.

**Validates: Requirements 7.3, 9.5, 9.6, 9.7**

### Property 4: Brand response never exposes private key

For any Brand API response (create, get, list, update), the response SHALL contain `public_key` and SHALL NOT contain `private_key_encrypted`.

**Validates: Requirements 2.3, 2.4, 12.3**

### Property 5: Tenant isolation on all queries

For any two distinct organization_ids, a query scoped to org A SHALL never return records belonging to org B. Requesting a resource by ID from a different org SHALL return 404.

**Validates: Requirements 2.1, 2.5, 4.2, 10.1, 11.1**

### Property 6: Permission-gated write operations on brands

For any user without `brand.create` permission, POST to `/api/v1/brands` SHALL return 403. For any user without `brand.update` permission, PATCH SHALL return 403.

**Validates: Requirements 1.7, 3.3**

### Property 7: Brand key fields are immutable

For any PATCH request to `/api/v1/brands/{id}` that includes `public_key` or `private_key_encrypted`, the system SHALL reject with 422. Only `name` and `short_code` are updatable.

**Validates: Requirements 3.1, 3.2**

### Property 8: QRProduct brand_id is immutable after creation

For any PATCH request to a QRProduct that includes `brand_id`, the system SHALL reject with 422.

**Validates: Requirements 4.3**

### Property 9: QRProduct creation validates brand ownership

For any QRProduct creation where `brand_id` does not belong to the user's organization, the system SHALL reject. Same-org brand_id succeeds.

**Validates: Requirements 4.1, 4.2**

### Property 10: Serial number type and activation method validation

`serial_number_type` SHALL only accept {R6DAN, R4DAN, S8DN, S10DN, null}. `activation_method` SHALL only accept {"pre", "post"}, defaulting to "pre".

**Validates: Requirements existing QRProduct validation**

### Property 11: Block quantity and qr_type validation

Block creation with `quantity` ≤ 0 or > 10,000, or invalid `qr_type`, SHALL return a validation error.

**Validates: Requirements 5.3, 5.4**

### Property 12: Credit balance gate

Block creation where `balance_credits` < `quantity` SHALL be rejected with 422. When `balance_credits` >= `quantity`, the request proceeds.

**Validates: Requirements 6.1, 6.2**

### Property 13: Credits deducted only on successful generation

Successful block generation of quantity N SHALL increase `used_credits` by N and decrease `balance_credits` by N, with a QRCreditLedger entry. Failed generation leaves credits unchanged.

**Validates: Requirements 6.3, 6.4, 6.5**

### Property 14: Serial number format matches configured type

R6DAN → 6-char alphanumeric, R4DAN → 4-char alphanumeric, S8DN → zero-padded 8-digit sequential, S10DN → zero-padded 10-digit sequential.

**Validates: Requirements 7.1**

### Property 15: Block generates correct number of unique items

For a block of quantity N (qr_type != "S"), exactly N ProductItem records SHALL be created with globally unique serial_numbers.

**Validates: Requirements 7.5, 7.6**

### Property 16: Block status lifecycle

Successful generation → status "completed" with non-null `download_url`. Failed generation → status "failed".

**Validates: Requirements 7.8, 7.9**

### Property 17: QR URL format

Generated URLs SHALL match `https://{org_short_code}.{domain}/g/{gtin}/s/{serial_number}/{timestamp}?c={base64_signature}` with all non-empty components.

**Validates: Requirements 7.4**

### Property 18: Static QR uses same serial for all items

For `qr_type` "S", all ProductItems in the block SHALL share the same serial_number.

**Validates: Requirements 8.2**

### Property 19: SecureCode QR generates 12-char secret codes

For `qr_type` "SC", every ProductItem SHALL have a non-null `secret_code` of exactly 12 characters.

**Validates: Requirements 8.5**

### Property 20: OneTime QR deactivates after first verification

For `qr_type` "O", after first successful verification, `qr_active` SHALL be false and subsequent verifications SHALL fail.

**Validates: Requirements 8.4**

### Property 21: Post-activation items require qr_active for verification

For ProductItems with `activation_method` "post" and `qr_active` false, verification SHALL return 400.

**Validates: Requirements 9.3, 9.4**

### Property 22: Scan count increments on successful verification

Each successful verification SHALL increment `scan_count` by 1 and update `last_scanned_at`.

**Validates: Requirements 9.8**

## Error Handling

### HTTP Error Codes

| Code | Scenario                               | Example                                                              |
| ---- | -------------------------------------- | -------------------------------------------------------------------- |
| 400  | Invalid input / verification failure   | Invalid signature, serial number not found                           |
| 401  | Missing or expired JWT                 | No token provided                                                    |
| 403  | Insufficient permission                | User without brand.create creating a brand                           |
| 404  | Resource not found or cross-org access | Brand ID from another org                                            |
| 422  | Business rule violation                | Insufficient credits, key fields in PATCH, brand_id in product PATCH |

### Error Response Format

All errors follow the standard FastAPI format:

```json
{ "detail": "Human-readable error message" }
```

### Service-Level Error Handling

| Service             | Error Condition                      | Behavior                                                               |
| ------------------- | ------------------------------------ | ---------------------------------------------------------------------- |
| KeyService          | Invalid encryption secret            | Raise on startup (fail fast)                                           |
| KeyService          | Decryption failure (corrupted data)  | Raise `ValueError`; block generation catches and marks block as failed |
| BrandService        | Duplicate short_code within org      | Return 409 Conflict                                                    |
| QRProductService    | brand_id not found in org            | Return 404                                                             |
| QRProductService    | brand_id in PATCH payload            | Return 422                                                             |
| CreditService       | Insufficient credits                 | Return 422                                                             |
| CreditService       | No QRCreditBalance record for org    | Return 422 ("No credit balance configured")                            |
| VerificationService | Serial number not found              | Return 400                                                             |
| VerificationService | qr_active is false (post-activation) | Return 400                                                             |
| VerificationService | Signature verification fails         | Return 400                                                             |
| Block generation    | Serial number collision              | Retry with new serial; max 3 retries per item                          |
| Block generation    | GCS upload failure                   | Mark block as failed, do not deduct credits                            |

## Testing Strategy

### Testing Framework

- **Unit tests**: `pytest` with existing test infrastructure in `core-service/tests/`
- **Property-based tests**: `hypothesis` library (already in project — `.hypothesis/` directory exists)
- **Mocking**: `unittest.mock` for external dependencies (GCS, KeyService in endpoint tests)
- **Database**: Use test PostgreSQL instance with transaction rollback per test

### Unit Tests

- Brand creation with valid input produces correct response shape
- Brand PATCH with key fields returns 422
- QRProduct creation with invalid brand_id returns 404
- QRProduct PATCH with brand_id returns 422
- Block creation with quantity=0 or quantity=10001 returns validation error
- Verification with non-existent serial returns 400
- Verification with inactive post-activation item returns 400
- Credit check with zero balance rejects block creation

### Property-Based Tests

Each correctness property maps to a property-based test using `hypothesis`. Tests run minimum 100 iterations.

| Property | Test Description            | Key Generators                                |
| -------- | --------------------------- | --------------------------------------------- |
| 1        | Valid P-256 key generation  | Random name/short_code strings                |
| 2        | Encryption round-trip       | Random P-256 private keys                     |
| 3        | Sign-then-verify round-trip | Random serial numbers, timestamps             |
| 4        | No private key in response  | Random brand creation payloads                |
| 5        | Tenant isolation            | Random organization_id pairs                  |
| 6        | Permission-gated writes     | Random user permission sets                   |
| 7        | Key field immutability      | Random PATCH payloads with/without key fields |
| 8        | brand_id immutability       | Random product PATCH payloads                 |
| 11       | Quantity/qr_type validation | Random integers, random strings               |
| 12       | Credit balance gate         | Random balance/quantity pairs                 |
| 14       | Serial number format        | Random serial_number_type values              |
| 15       | Item count and uniqueness   | Random block quantities                       |
| 18       | Static QR same serial       | Random Static block quantities                |
| 19       | SecureCode secret length    | Random SC block quantities                    |
| 20       | OneTime deactivation        | Random OneTime items, multiple verifications  |
| 22       | Scan count increment        | Random items, multiple verifications          |
