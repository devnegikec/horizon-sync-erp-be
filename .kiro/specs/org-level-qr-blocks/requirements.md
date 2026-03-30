# Requirements Document

## Introduction

The `core-service` currently exposes `GET /api/v1/qr-products/{product_id}/blocks` to list QR blocks scoped to a single product. This feature adds a complementary org-level endpoint — `GET /api/v1/qr-products/blocks` — that returns **all** QR blocks across every product belonging to the authenticated user's organization. The endpoint supports pagination, optional filtering by status and product_id, and enriches each block with its parent product's name for display convenience. All data is strictly scoped to the organization derived from the JWT; no cross-org data is ever exposed.

## Glossary

- **Endpoint**: The new `GET /api/v1/qr-products/blocks` HTTP route added to `core-service`.
- **QRBlock**: A batch of QR codes generated for a QRProduct, represented by the `qr_blocks` database table. Fields include `id`, `organization_id`, `product_id`, `batch`, `quantity`, `sr_number_type`, `status`, `task_status`, `task_id`, `qr_image`, `manufacture_date`, `expiry_date`, `gcs_url`, `download_url`, `completed_at`, `created_at`, `updated_at`, `deleted_at`.
- **QRProduct**: A product record in the `qr_products` table, identified by `id` and `name`.
- **Organization**: The tenant owning the data, identified by `organization_id` extracted from the authenticated user's JWT.
- **CurrentUser**: The authenticated principal injected by the `require_permission()` FastAPI dependency; provides `organization_id` and `id`.
- **Soft-delete**: A record whose `deleted_at` column is non-null is considered deleted and must be excluded from all query results.
- **Pagination**: The standard response envelope used across `core-service`: `{ page, page_size, total_items, total_pages, has_next, has_prev }`.
- **OrgBlocksRepository**: The new repository method (or extension of `QRBlockRepository`) responsible for querying blocks across all products within an organization.
- **OrgBlocksService**: The new service method responsible for applying filters, computing pagination metadata, and enriching blocks with `product_name`.
- **OrgBlockListItem**: The response schema for a single block in the org-level list, extending `QRBlockResponse` with a `product_name` field.

---

## Requirements

### Requirement 1: Org-Level Block Listing Endpoint

**User Story:** As an authenticated API consumer with the `qr_product.read` permission, I want to retrieve all QR blocks across all products in my organization, so that I can display a unified block history without needing to query each product individually.

#### Acceptance Criteria

1. THE Endpoint SHALL accept `GET` requests at the path `/api/v1/qr-products/blocks`.
2. WHEN a request is received without a valid JWT bearing the `qr_product.read` permission, THE Endpoint SHALL return HTTP 403.
3. WHEN a valid request is received, THE Endpoint SHALL return only QRBlocks whose `organization_id` matches the `organization_id` from the authenticated user's JWT.
4. THE Endpoint SHALL accept optional query parameters `page` (integer ≥ 1, default 1) and `page_size` (integer 1–100, default 20).
5. THE Endpoint SHALL return results ordered by `created_at` descending (newest first).
6. THE Endpoint SHALL exclude any QRBlock whose `deleted_at` is non-null.
7. THE Endpoint SHALL include a `product_name` field on each returned block, populated from the associated QRProduct's `name` column.

---

### Requirement 2: Status Filter

**User Story:** As an authenticated API consumer, I want to filter the org-level block list by status, so that I can quickly find blocks in a specific lifecycle state (e.g., only completed blocks ready for download).

#### Acceptance Criteria

1. THE Endpoint SHALL accept an optional `status` query parameter with allowed values: `pending`, `in_progress`, `completed`, `failed`.
2. WHEN the `status` query parameter is provided, THE Endpoint SHALL return only QRBlocks whose `status` column equals the supplied value.
3. WHEN the `status` query parameter is omitted, THE Endpoint SHALL return QRBlocks of all statuses.
4. IF an unrecognized `status` value is supplied, THEN THE Endpoint SHALL return HTTP 422 with a descriptive validation error.

---

### Requirement 3: Product Filter

**User Story:** As an authenticated API consumer, I want to optionally narrow the org-level block list to a specific product, so that I can replicate the per-product view without requiring the product ID in the URL path.

#### Acceptance Criteria

1. THE Endpoint SHALL accept an optional `product_id` query parameter (UUID format).
2. WHEN the `product_id` query parameter is provided, THE Endpoint SHALL return only QRBlocks whose `product_id` column equals the supplied value.
3. WHEN the `product_id` query parameter is omitted, THE Endpoint SHALL return QRBlocks across all products in the organization.
4. IF a `product_id` is supplied that does not belong to the authenticated user's organization, THEN THE Endpoint SHALL return an empty result set (not HTTP 404), preserving org isolation.

---

### Requirement 4: Pagination Response

**User Story:** As an authenticated API consumer, I want accurate pagination metadata in the response, so that I can implement correct page navigation in the UI.

#### Acceptance Criteria

1. THE Endpoint SHALL return a response body containing a `blocks` array and a `pagination` object.
2. THE Endpoint SHALL set `pagination.total_items` to the total count of QRBlocks matching the applied filters (status, product_id, organization_id, non-deleted).
3. THE Endpoint SHALL set `pagination.total_pages` to `ceil(total_items / page_size)`, with a minimum value of 1.
4. THE Endpoint SHALL set `pagination.has_next` to `true` if and only if `page < total_pages`.
5. THE Endpoint SHALL set `pagination.has_prev` to `true` if and only if `page > 1`.
6. WHEN `page` exceeds `total_pages`, THE Endpoint SHALL return an empty `blocks` array with accurate pagination metadata reflecting the actual total.

---

### Requirement 5: Org Isolation Invariant

**User Story:** As a platform operator, I want every query to be strictly scoped to the authenticated organization, so that no tenant can ever access another tenant's QR block data.

#### Acceptance Criteria

1. THE OrgBlocksRepository SHALL apply `organization_id = <current_user.organization_id>` as a mandatory, non-overridable filter on every query.
2. WHEN a `product_id` filter is supplied, THE OrgBlocksRepository SHALL apply both `product_id = <supplied_value>` AND `organization_id = <current_user.organization_id>` — never one without the other.
3. FOR ALL valid requests, THE Endpoint SHALL return zero QRBlocks whose `organization_id` differs from the authenticated user's `organization_id`.

---

### Requirement 6: Soft-Delete Exclusion Invariant

**User Story:** As a platform operator, I want soft-deleted blocks to be invisible to all callers, so that deleted data is never surfaced through the API.

#### Acceptance Criteria

1. THE OrgBlocksRepository SHALL apply `deleted_at IS NULL` as a mandatory filter on every query.
2. FOR ALL valid requests, THE Endpoint SHALL return zero QRBlocks whose `deleted_at` is non-null.

---

### Requirement 7: Response Schema

**User Story:** As a frontend developer, I want a well-defined response schema that includes all block fields plus `product_name`, so that I can render the org-level block list without additional API calls.

#### Acceptance Criteria

1. THE Endpoint SHALL return each block with the following fields: `id`, `organization_id`, `product_id`, `product_name`, `batch`, `quantity`, `sr_number_type`, `status`, `task_status`, `task_id`, `qr_image`, `manufacture_date`, `expiry_date`, `gcs_url`, `download_url`, `completed_at`, `created_at`.
2. THE Endpoint SHALL populate `product_name` from the associated QRProduct's `name` field via a JOIN or eager-load — not a separate per-block API call.
3. WHEN a QRProduct associated with a block has been soft-deleted, THE Endpoint SHALL still populate `product_name` from the product record (the block itself is not deleted).
