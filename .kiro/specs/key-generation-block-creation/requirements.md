# Requirements Document

## Introduction

This document defines the requirements for adding ECDSA key pair management, a Brand entity, enhanced QR block generation with digital signing, and cryptographic scan verification to the existing core-service. The feature extends the current `QRProduct` / `QRBlock` / `ProductItem` models and `QRProductService` within `core-service/`, upgrading from simple serial-number lookup verification to ECDSA P-256 signature-based authentication, and introducing encrypted-at-rest private key storage and a Brand hierarchy above Products.

## Glossary

- **Organization**: The top-level tenant entity. Each Organization is identified by `organization_id`. All data is isolated per Organization. Already exists in the identity-service.
- **Brand**: A new entity owned by an Organization that holds an ECDSA key pair. QRProducts are linked to a Brand for digital signing.
- **QRProduct**: An existing goods item (table `qr_products`) that will gain a `brand_id` foreign key linking it to a Brand's signing identity.
- **QRBlock**: An existing batch record (table `qr_blocks`) representing a request to generate a set of QR codes for a QRProduct. Will gain `task_id`, `status`, and `download_url` fields.
- **ProductItem**: An existing individual QR code record (table `product_items`) that will gain `qr_active`, `scan_count`, `last_scanned_at`, and `secret_code` fields for signature-based verification.
- **KeyService**: A new service component responsible for generating ECDSA key pairs, encrypting private keys with Fernet, and decrypting private keys for signing.
- **BrandService**: A new service component responsible for creating, listing, retrieving, and updating Brands.
- **BlockService**: The enhanced block generation logic within `QRProductService` that dispatches background QR generation and manages block lifecycle.
- **VerificationService**: The enhanced verification logic that performs ECDSA signature verification on scanned QR codes, replacing the current scan-count-only approach.
- **CreditService**: The existing credit checking logic (monthly `QRCreditUsage` tracking) that will be enhanced with a `QRCreditBalance` table and `QRCreditLedger` audit log.
- **QRCreditBalance**: A new record tracking total, used, and remaining QR generation credits for an Organization.
- **QRCreditLedger**: A new audit log recording every credit change event.
- **ECDSA**: Elliptic Curve Digital Signature Algorithm, used for signing and verifying QR code messages.
- **Fernet**: A symmetric encryption scheme from the `cryptography` library, used to encrypt private keys at rest.
- **GTIN**: Global Trade Item Number, a product identifier embedded in QR URLs.

## Requirements

### Requirement 1: Brand Creation with Key Pair Generation

**User Story:** As a user with `brand.create` permission, I want to create a Brand with an automatically generated ECDSA key pair, so that the Brand can digitally sign QR codes for its products.

#### Acceptance Criteria

1. WHEN a user with `brand.create` permission sends a POST request to `/api/v1/brands` with a valid name and short_code, THE BrandService SHALL create a new Brand record with an auto-generated ECDSA P-256 key pair.
2. THE KeyService SHALL generate key pairs using the ECDSA algorithm with the NIST P-256 (SECP256R1) curve via the `cryptography` library.
3. THE KeyService SHALL encrypt the private key using Fernet symmetric encryption with the `BRAND_KEY_ENCRYPTION_SECRET` environment variable before storing the private key in the database.
4. THE KeyService SHALL store the public key as an uncompressed X9.62 hex-encoded string in the Brand record.
5. THE BrandService SHALL generate the key pair synchronously during Brand creation within the same database transaction.
6. THE BrandService SHALL associate the new Brand with the requesting user's `organization_id` (extracted from the JWT via `CurrentUser`).
7. IF a user without `brand.create` permission sends a POST request to `/api/v1/brands`, THEN the system SHALL reject the request with a 403 status code.

### Requirement 2: Brand Retrieval and Listing

**User Story:** As an authenticated user with `brand.read` permission, I want to list and view Brands in my Organization, so that I can see which Brands exist and their public keys.

#### Acceptance Criteria

1. WHEN an authenticated user sends a GET request to `/api/v1/brands`, THE BrandService SHALL return a paginated list of Brands filtered by the user's `organization_id`.
2. WHEN an authenticated user sends a GET request to `/api/v1/brands/{id}`, THE BrandService SHALL return the Brand detail for the specified Brand within the user's organization.
3. THE BrandService SHALL include the `public_key` field in all Brand response payloads.
4. THE BrandService SHALL exclude the `private_key_encrypted` field from all Brand response payloads.
5. IF an authenticated user requests a Brand that does not exist or belongs to a different organization, THEN THE BrandService SHALL return a 404 status code.

### Requirement 3: Brand Update Restrictions

**User Story:** As a user with `brand.update` permission, I want to update a Brand's name or short_code, so that I can correct Brand metadata without affecting the cryptographic keys.

#### Acceptance Criteria

1. WHEN a user with `brand.update` permission sends a PATCH request to `/api/v1/brands/{id}` with name or short_code fields, THE BrandService SHALL update only the provided fields.
2. THE BrandService SHALL reject any PATCH request that includes `public_key` or `private_key_encrypted` fields, returning a 422 status code.
3. IF a user without `brand.update` permission sends a PATCH request to `/api/v1/brands/{id}`, THEN the system SHALL reject the request with a 403 status code.
4. THE BrandService SHALL provide no DELETE endpoint for Brands, ensuring key pairs persist indefinitely.

### Requirement 4: QRProduct Linking to Brands

**User Story:** As a user with `qr_product.create` permission, I want to link a QRProduct to a Brand, so that the Product uses the Brand's key pair for QR signing.

#### Acceptance Criteria

1. THE existing `QRProduct` model SHALL gain an optional `brand_id` foreign key column referencing the `brands` table.
2. WHEN creating a QRProduct with a `brand_id`, THE QRProductService SHALL validate that the specified `brand_id` belongs to the user's organization before creating the Product.
3. THE QRProductService SHALL treat `brand_id` as immutable after QRProduct creation; PATCH requests that include `brand_id` SHALL be rejected with a 422 status code.
4. WHEN listing QRProducts, the response SHALL include the `brand_id` field.
5. QRProducts created without a `brand_id` SHALL continue to work as before (no ECDSA signing).

### Requirement 5: Enhanced QR Block Creation

**User Story:** As a user with `qr_product.create` permission, I want to create a QR Block for a Product that has a Brand, so that a batch of digitally signed QR codes is generated.

#### Acceptance Criteria

1. THE existing `QRBlock` model SHALL gain `status` (replacing `task_status`), `task_id`, and `download_url` fields.
2. WHEN a block is created for a QRProduct that has a `brand_id`, THE block generation SHALL sign each ProductItem using the Brand's ECDSA private key.
3. THE BlockService SHALL validate that `quantity` is greater than 0 and less than or equal to 10,000.
4. THE BlockService SHALL validate that `qr_type` is one of: D (Dynamic), S (Static), B (Dual), O (OneTime), SC (SecureCode).
5. THE block generation SHALL update the Block status through the lifecycle: `pending` → `in_progress` → `completed` | `failed`.
6. THE BlockService SHALL return a 201 response containing the `block_id`, `status`, and timestamps.
7. THE BlockService SHALL provide no UPDATE or DELETE endpoints for Blocks; Blocks are immutable once created.

### Requirement 6: QR Credit Validation

**User Story:** As a user with `qr_product.create` permission, I want the system to check my Organization's QR credit balance before creating a Block, so that I cannot generate more QR codes than my quota allows.

#### Acceptance Criteria

1. WHEN a Block creation request is received, THE CreditService SHALL check that the Organization's `balance_credits` in QRCreditBalance is greater than or equal to the requested `quantity`.
2. IF the Organization's `balance_credits` is less than the requested `quantity`, THEN THE CreditService SHALL reject the Block creation with a 422 status code and a message indicating insufficient credits.
3. THE block generation SHALL deduct credits from QRCreditBalance atomically only after the Block generation completes successfully.
4. IF the block generation fails, THEN credits SHALL remain unchanged.
5. THE CreditService SHALL write a record to QRCreditLedger for every credit deduction, capturing the block_id, quantity deducted, and resulting balance.

### Requirement 7: QR Block Generation with Digital Signing

**User Story:** As a user with `qr_product.create` permission, I want QR codes to be digitally signed using the Brand's ECDSA key pair, so that each QR code can be cryptographically verified.

#### Acceptance Criteria

1. THE block generation SHALL generate or assign a serial number for each item in the Block according to the configured `serial_number_type` (R6DAN, R4DAN, S8DN, or S10DN).
2. THE block generation SHALL create a timestamp in milliseconds since epoch for each item.
3. THE block generation SHALL build a signing message in the format `{serial_number}~{timestamp}` and sign the message using the Brand's decrypted ECDSA P-256 private key with SHA-256 hashing.
4. THE block generation SHALL construct a long URL in the format: `https://{org_short_code}.{domain}/g/{gtin}/s/{serial_number}/{timestamp}?c={base64_signature}`.
5. THE block generation SHALL create a ProductItem record for each generated item, storing the serial_number, block_id, product_id, and organization_id.
6. THE block generation SHALL enforce uniqueness on the `serial_number` field across all ProductItem records.
7. THE block generation SHALL generate an Excel file containing all QR data rows and upload the Excel file to Google Cloud Storage.
8. WHEN all items are generated successfully, THE block generation SHALL update the Block status to "completed" and set the `download_url` and `completed_at` fields.
9. IF an error occurs during generation, THEN THE block generation SHALL update the Block status to "failed".
10. WHILE the Block status is "pending" or "in_progress", THE BlockService SHALL return the current status when queried via GET.

### Requirement 8: QR Type-Specific Behavior

**User Story:** As a user with `qr_product.create` permission, I want different QR types to behave according to their specifications, so that each type serves its intended use case.

#### Acceptance Criteria

1. WHEN `qr_type` is "D" (Dynamic), THE block generation SHALL generate a unique URL per ProductItem with standard verification.
2. WHEN `qr_type` is "S" (Static), THE block generation SHALL use the same serial number for all items in the batch, varying only the timestamp.
3. WHEN `qr_type` is "B" (Dual), THE block generation SHALL generate two QR codes per ProductItem (covert and overt) with separate URLs.
4. WHEN `qr_type` is "O" (OneTime), THE VerificationService SHALL deactivate the ProductItem after the first successful verification.
5. WHEN `qr_type` is "SC" (SecureCode), THE block generation SHALL generate a 12-character secret code for each ProductItem and store the secret code in the `secret_code` field.

### Requirement 9: Scan Verification (Product Authentication)

**User Story:** As a consumer scanning a QR code, I want the system to verify the digital signature, so that I can confirm the product is authentic.

#### Acceptance Criteria

1. WHEN a POST request is sent to `/api/v1/qr-products/authenticate` with `serial_number`, `nonce` (timestamp), and `cipher` (base64 signature), THE VerificationService SHALL look up the ProductItem by `serial_number`.
2. IF no ProductItem exists for the given `serial_number`, THEN THE VerificationService SHALL return a 400 status code with the message "Serial number not found".
3. WHILE the QRProduct's `activation_method` is "post", THE VerificationService SHALL verify that the ProductItem's `qr_active` field is true before proceeding with signature verification.
4. IF the ProductItem's `qr_active` is false and the QRProduct's `activation_method` is "post", THEN THE VerificationService SHALL return a 400 status code indicating the product has not been activated.
5. THE VerificationService SHALL reconstruct the message as `{serial_number}~{nonce}`, decode the base64 cipher to raw signature bytes, and verify the signature using the Brand's public key with ECDSA P-256 and SHA-256.
6. WHEN the signature is valid, THE VerificationService SHALL return a 200 response with `"message": "Authentic Product"`, `"authentic": true`, and product information including product_name, brand_name, gtin, and serial_number.
7. IF the signature verification fails, THEN THE VerificationService SHALL return a 400 status code with `"message": "Authentication Failed"` and `"authentic": false`.
8. WHEN a successful verification occurs, THE VerificationService SHALL increment the ProductItem's `scan_count` by 1 and update `last_scanned_at` to the current timestamp.
9. THE `/api/v1/qr-products/authenticate` endpoint SHALL be publicly accessible without authentication.
10. FOR QRProducts without a `brand_id`, THE existing scan-count-based validation logic SHALL continue to work via the current `/api/v1/qr-products/validate` endpoint.

### Requirement 10: Block and ProductItem Retrieval

**User Story:** As an authenticated user, I want to list Blocks and their ProductItems, so that I can track QR generation status and view generated items.

#### Acceptance Criteria

1. WHEN an authenticated user sends a GET request to `/api/v1/qr-products/{product_id}/blocks`, THE service SHALL return a paginated list of Blocks filtered by the user's `organization_id`.
2. THE service SHALL support optional query parameters `status` for filtering the Block list.
3. WHEN an authenticated user sends a GET request to `/api/v1/qr-products/blocks/{block_id}`, THE service SHALL return the Block detail including current status, task_id, download_url, and timestamps.
4. WHEN an authenticated user sends a GET request to `/api/v1/qr-products/blocks/{block_id}/items`, THE service SHALL return a paginated list of ProductItems belonging to the specified Block within the user's organization.

### Requirement 11: Multi-Tenancy Enforcement

**User Story:** As a platform operator, I want all data to be isolated per Organization, so that no tenant can access another tenant's data.

#### Acceptance Criteria

1. THE BrandService, QRProductService, and VerificationService SHALL include an `organization_id` filter in every database query.
2. THE Brand model SHALL include an `organization_id` column with a non-null constraint and an index, following the same pattern as existing models (QRProduct, QRBlock, ProductItem).
3. THE system SHALL resolve `organization_id` from the authenticated user's JWT token via the existing `CurrentUser` dependency.

### Requirement 12: Private Key Security

**User Story:** As a platform operator, I want private keys to be protected at rest and in transit, so that the signing capability cannot be compromised.

#### Acceptance Criteria

1. THE KeyService SHALL encrypt all private keys using Fernet symmetric encryption before persisting the private keys to the database.
2. THE KeyService SHALL derive the Fernet encryption key from the `BRAND_KEY_ENCRYPTION_SECRET` environment variable, added to `core-service/app/config.py` Settings.
3. THE BrandService SHALL exclude the `private_key_encrypted` field from all API response schemas.
4. THE KeyService SHALL decrypt private keys only within the block generation and VerificationService, and only in memory for the duration of the signing or verification operation.
5. THE system SHALL store no private keys in plaintext in the database or in application logs.
