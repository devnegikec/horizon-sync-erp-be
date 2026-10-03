# QSeal QR Signing and Product Authentication

## Purpose

QSeal uses asymmetric cryptography to prove that a QR code was issued by the
brand recorded in Horizon Sync. Each brand has its own ECDSA P-256 key pair.
The private key signs QR payloads, while the public key verifies those
signatures when a customer scans a QR code.

This document describes the current implementation, including key storage,
QR generation, public verification, tenant isolation, QR-type behavior, secret
management, and operational considerations.

## Key hierarchy

There are two different kinds of keys:

1. One ECDSA P-256 key pair per Brand.
2. One application-level Fernet encryption secret for the current deployment.

```text
BRAND_KEY_ENCRYPTION_SECRET (application master encryption key)
        |
        +-- decrypts Organization A / Brand 1 private key
        +-- decrypts Organization A / Brand 2 private key
        +-- decrypts Organization B / Brand 1 private key
        `-- decrypts Organization C / Brand 1 private key

Each decrypted Brand private key signs only that Brand's QR codes.
Each Brand public key verifies signatures created by its matching private key.
```

The application master key does not sign QR codes. It only protects Brand
private keys while they are stored in PostgreSQL.

## Brand key creation and storage

When a Brand is created, `BrandService` asks `KeyService` to generate a new
ECDSA P-256 key pair.

The `brands` table stores:

| Column | Contents | Sensitivity |
| --- | --- | --- |
| `public_key` | Uncompressed X9.62 ECDSA public key encoded as hexadecimal | Public |
| `private_key_encrypted` | Fernet-encrypted private-key scalar | Confidential |
| `organization_id` | Tenant that owns the Brand | Security boundary |

`KeyService` encrypts the private-key scalar using
`BRAND_KEY_ENCRYPTION_SECRET` before the Brand record is written. The plaintext
private key is not stored in the database.

Every Brand receives a unique ECDSA key pair. In the current implementation,
all organizations use the same application-level encryption secret to protect
their individual Brand private keys.

## Why the application encryption secret is required

Encrypting the Brand private key protects against a database-only compromise.
An attacker who copies the `brands` table receives encrypted private keys but
cannot use them to generate authentic signatures without also obtaining
`BRAND_KEY_ENCRYPTION_SECRET`.

The secret must:

- remain outside source control and the database;
- be identical in core-service and the Celery QR worker;
- remain stable for the lifetime of keys encrypted with it;
- be stored in `core-service/.env` for local development;
- be injected from AWS Secrets Manager in production.

If this secret is lost, existing Brand private keys cannot be decrypted. If it
is changed without re-encrypting existing keys, QR generation for those Brands
will fail. If it is compromised together with the database, all Brand private
keys protected by it may be exposed.

## QR generation and signing

For each Product Item, block generation performs the following steps:

1. Resolve the Product and its Brand within the current organization.
2. Read the Brand's `private_key_encrypted` value.
3. Decrypt the Brand private key using `BRAND_KEY_ENCRYPTION_SECRET`.
4. Generate or allocate a globally unique Product Item serial number.
5. Generate the current Unix timestamp in milliseconds.
6. Build the signing message:

   ```text
   {serial_number}~{timestamp_ms}
   ```

7. Sign the message using ECDSA P-256 with SHA-256.
8. Base64-encode the DER signature.
9. Percent-encode the signature when inserting it into the URL.
10. Build the long verification URL:

   ```text
   https://horizon.ciphercode.ai/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}
   ```

11. Optionally send the long URL to the configured short-URL provider.
12. Save the Product Item and write the URL to the generated QR workbook.

The signature query parameter must be percent-encoded. A raw Base64 `+`
character can otherwise be decoded as a space by URL query parsers and cause a
valid signature to fail. The verification request also repairs this legacy
encoding issue for QR codes generated before percent-encoding was introduced.

### What is cryptographically signed

The current signed message contains the serial number and timestamp:

```text
serial_number~timestamp
```

GTIN is present in the URL but is not currently part of the signed message.
During verification, GTIN is independently checked against the Product or SKU
associated with the resolved Product Item.

## Public verification API

The public landing page sends a request to:

```http
POST /api/v1/public/qr/verify
```

Conceptual request body:

```json
{
  "gtin": "3737743747272",
  "serial_number": "PH-00000300",
  "timestamp": "1785891120948",
  "signature": "MEQC...",
  "qr_channel": "overt",
  "secure_code": null
}
```

`qr_channel` is used for Dual QR codes. `secure_code` is supplied only when a
Secure Code challenge requires it.

## Authentication verification flow

The verification service applies these checks in order:

```text
QR request
   |
   v
Resolve Product Item by globally unique serial number
   |
   v
Lock and reload the item within its resolved organization
   |
   v
Validate Item -> Product -> Brand organization ownership
   |
   v
Validate Product and Brand are active and not deleted
   |
   v
Validate URL GTIN against the item's SKU/Product GTIN
   |
   v
Rebuild "serial_number~timestamp"
   |
   v
Verify ECDSA signature using the Brand public key
   |
   v
Apply QR type, challenge, and activation rules
   |
   v
Return the public verification result and Product presentation data
```

### 1. Serial lookup

The Product Item is resolved using its serial number. Active Product Item
serials are globally unique, which makes the serial sufficient to identify the
item and its organization without trusting tenant information from the public
request.

### 2. Tenant and ownership validation

After resolving the organization, the service verifies that:

- Product Item, Product, and Brand belong to the same organization;
- the linked SKU belongs to that organization when present;
- the linked QR Block belongs to that organization when present;
- the Product is active and not soft-deleted;
- the Brand is not soft-deleted.

The public caller cannot provide or override `organization_id`.

### 3. GTIN validation

The URL GTIN must equal either:

- the linked SKU's GTIN; or
- the Product's legacy GTIN.

If it matches neither, verification returns the generic invalid result.

### 4. Signature verification

The service reconstructs the original message:

```text
{serial_number}~{timestamp}
```

It then verifies the submitted Base64 signature with the Brand's ECDSA public
key using SHA-256. Verification succeeds only when the serial, timestamp,
signature, and Brand key correspond.

The application encryption secret is not required for public signature
verification. It is required only when decrypting the Brand private key for
signing.

### 5. Generic failure response

Missing items, tenant mismatches, GTIN mismatches, missing public keys, and bad
signatures return a generic authentication failure. Avoiding detailed public
failure reasons reduces information disclosure and serial-number enumeration.

## QR-type behavior

Cryptographic validation happens before the QR-specific rules below.

### Dynamic QR

- An active and correctly signed Product Item returns `authentic`.
- A genuine but inactive item returns `not_activated`.
- Dynamic verification does not consume or deactivate the QR.

### Dual QR

- Scanning the overt QR returns `verification_required` and asks the user to
  scan the protected/covert QR.
- The protected QR proceeds through full authentication.

### Secure Code

- A valid QR without a submitted protected code returns
  `verification_required`.
- The submitted code is normalized and compared using a constant-time
  comparison.
- A correct code completes authentication; an incorrect code returns
  `invalid`.

### One-Time QR

- The first valid scan returns `authentic`.
- The same transaction marks the Product Item inactive and verified.
- Later valid scans return `already_used`.
- A database row lock prevents concurrent scans from consuming the same QR
  more than once.

## Activation method

Block generation initializes Product Items according to the Product's
activation method:

- `pre`: generated Product Items start activated.
- `post`: generated Product Items start deactivated and return
  `not_activated` until an activation workflow activates them.

Activation status is a business rule in addition to cryptographic validity. A
QR can be genuine and correctly signed while its Product Item is not yet
activated.

## Public response and landing page

After successful cryptographic and business-rule validation, the endpoint can
return:

- verification status and customer-facing message;
- Product, Brand, SKU, GTIN, and serial information;
- logo, Product image, and banner URLs;
- contact email, phone number, and official website;
- any required Dual or Secure Code challenge.

The public page uses these values to render the Brand identity, authentication
status, Product details, and official support information.

Scan analytics and scan-event capture are intentionally outside the current
verification phase and are not performed by this endpoint yet.

## Secret configuration

Generate a valid Fernet key once for a new environment:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Local configuration, never committed:

```dotenv
BRAND_KEY_ENCRYPTION_SECRET=<fernet-key>
```

Only an empty placeholder belongs in `.env.example`:

```dotenv
BRAND_KEY_ENCRYPTION_SECRET=
```

Never store the real value in:

- `config.py` defaults;
- `docker-compose.yml` defaults;
- `.env.example`;
- migration files;
- tests or fixtures;
- logs;
- frontend code;
- QR workbooks or URLs.

## Secret rotation

The current encrypted Brand records do not carry an encryption-key version.
Therefore, replacing the master secret directly makes existing
`private_key_encrypted` values unreadable.

A safe rotation requires:

1. Retain access to the old secret.
2. Decrypt every Brand private key using the old secret.
3. Encrypt each private key using the new secret.
4. Update all Brand rows transactionally or through a resumable migration.
5. Deploy the new secret to both core-service and the Celery worker.
6. Verify QR generation before retiring the old secret.
7. Record an auditable rotation event without logging either secret.

Back up the secret using an approved secret-management system. Do not back it
up in the repository.

## Recommended production evolution

The current single application-level Fernet key is workable for an initial
deployment but has an application-wide blast radius. A stronger enterprise
design uses AWS KMS envelope encryption:

1. Generate a data-encryption key for a Brand or organization.
2. Encrypt the Brand private key using the plaintext data key.
3. Store only the KMS-encrypted data key beside the encrypted private key.
4. Ask KMS to decrypt the data key when signing is required.
5. Restrict KMS access using the ECS task role.
6. Use CloudTrail to audit decrypt operations.

This removes a permanent plaintext master key from application configuration
and improves isolation, auditability, and rotation.

## Operational checklist

- [ ] Every Brand has a unique ECDSA key pair.
- [ ] Brand private keys are encrypted in the database.
- [ ] The real encryption secret is absent from Git history.
- [ ] Core-service and the QR worker use the same secret.
- [ ] Production obtains the secret from AWS Secrets Manager.
- [ ] S3, database, and service logs never contain plaintext private keys.
- [ ] QR signatures are percent-encoded in URLs.
- [ ] Product Item serial numbers remain globally unique.
- [ ] Ownership checks remain organization-scoped.
- [ ] One-Time QR verification retains its row lock and atomic update.
- [ ] Secret rotation is tested before changing the production value.

## Relevant implementation files

- `app/models/brand.py`
- `app/services/key_service.py`
- `app/services/brand_service.py`
- `app/utils/serial_generators.py`
- `app/services/qr_product_service.py`
- `app/repositories/qr_verification_repository.py`
- `app/services/qr_verification_service.py`
- `app/api/v1/endpoints/public_qr.py`
- `app/schemas/qr_verification.py`
