# Implementation Plan: org-level-qr-blocks

## Overview

Add `GET /api/v1/qr-products/blocks` to `core-service` — an org-scoped endpoint listing all QR blocks across all products for the authenticated user's organization. Implementation is purely additive across four existing files: repository, service, schemas, and endpoint.

## Tasks

- [x] 1. Add `QRBlockRepository.list_by_org` to the repository
  - Add `list_by_org` method to `QRBlockRepository` in `core-service/app/repositories/qr_product_repository.py`
  - Use `outerjoin(QRProduct, QRBlock.product_id == QRProduct.id)` to retrieve `QRProduct.name` alongside each block
  - Apply mandatory filters: `QRBlock.organization_id == organization_id` and `QRBlock.deleted_at.is_(None)`
  - Apply optional filters: `QRBlock.status == status` when provided, `QRBlock.product_id == product_id` when provided
  - Order by `QRBlock.created_at.desc()`
  - Return `tuple[list[tuple[QRBlock, str | None]], int]` — rows and total filtered count (use `.count()` before pagination)
  - _Requirements: 1.3, 1.5, 1.6, 2.2, 3.2, 5.1, 5.2, 6.1_

  - [ ]\* 1.1 Write property test for `list_by_org` org isolation
    - **Property 1: Org Isolation**
    - **Validates: Requirements 1.3, 5.1, 5.2, 5.3**
    - Tag: `# Feature: org-level-qr-blocks, Property 1: org isolation`

  - [ ]\* 1.2 Write property test for `list_by_org` soft-delete exclusion
    - **Property 5: Soft-Delete Exclusion**
    - **Validates: Requirements 1.6, 6.1, 6.2**
    - Tag: `# Feature: org-level-qr-blocks, Property 5: soft-delete exclusion`

  - [ ]\* 1.3 Write property test for `list_by_org` result ordering
    - **Property 7: Result Ordering**
    - **Validates: Requirements 1.5**
    - Tag: `# Feature: org-level-qr-blocks, Property 7: result ordering`

- [x] 2. Add `QRProductService.list_blocks_by_org` to the service
  - Add `list_blocks_by_org` method to `QRProductService` in `core-service/app/services/qr_product_service.py`
  - Call `self.block_repo.list_by_org(organization_id, page, page_size, status, product_id)`
  - Build standard pagination dict: `{ page, page_size, total_items, total_pages, has_next, has_prev }` — use `max(1, ceil)` for `total_pages`
  - Convert each `(QRBlock, product_name)` tuple into a flat dict by merging `block.__dict__` with `{"product_name": product_name}`; strip SQLAlchemy `_sa_instance_state` key
  - Return `tuple[list[dict], dict]`
  - _Requirements: 1.7, 4.2, 4.3, 4.4, 4.5, 7.2, 7.3_

  - [ ]\* 2.1 Write property test for pagination accuracy
    - **Property 4: Pagination Accuracy**
    - **Validates: Requirements 4.2, 4.3, 4.4, 4.5**
    - Tag: `# Feature: org-level-qr-blocks, Property 4: pagination accuracy`

  - [ ]\* 2.2 Write property test for product name enrichment
    - **Property 6: Product Name Enrichment**
    - **Validates: Requirements 1.7, 7.2, 7.3**
    - Tag: `# Feature: org-level-qr-blocks, Property 6: product name enrichment`

- [x] 3. Add `OrgBlockListItem` and `OrgBlockListResponse` schemas
  - Add both classes to `core-service/app/schemas/qr_product.py`
  - `OrgBlockListItem` fields: `id`, `organization_id`, `product_id`, `product_name: str | None`, `batch`, `quantity`, `serial_prefix: str | None`, `sr_number_type: str | None`, `status: str | None`, `task_status: str | None`, `task_id: str | None`, `qr_image: bool`, `manufacture_date: date | None`, `expiry_date: date | None`, `gcs_url: str | None`, `download_url: str | None`, `completed_at: datetime | None`, `created_at: datetime`
  - Set `model_config = {"from_attributes": True}` on `OrgBlockListItem`
  - `OrgBlockListResponse` fields: `blocks: list[OrgBlockListItem]`, `pagination: dict[str, Any]`
  - _Requirements: 7.1_

  - [ ]\* 3.1 Write property test for response schema completeness
    - **Property 8: Response Schema Completeness**
    - **Validates: Requirements 7.1**
    - Tag: `# Feature: org-level-qr-blocks, Property 8: response schema completeness`

- [x] 4. Add `list_org_qr_blocks` endpoint
  - Add the endpoint to `core-service/app/api/v1/endpoints/qr_products.py`
  - Register at `@router.get("/blocks", ...)` — this route MUST be placed in the file BEFORE the `/{product_id}/blocks` route to prevent FastAPI from capturing the literal string `"blocks"` as a UUID `product_id`
  - Import `OrgBlockListItem` and `OrgBlockListResponse` from schemas
  - Query params: `page: int = Query(1, ge=1)`, `page_size: int = Query(20, ge=1, le=100)`, `status: Literal["pending", "in_progress", "completed", "failed"] | None = Query(None)`, `product_id: UUID | None = Query(None)`
  - Use `require_permission("qr_product.read")` dependency; extract `organization_id` from `current_user.organization_id` only — never from query params
  - Call `svc.list_blocks_by_org(...)` and return `OrgBlockListResponse`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.1, 2.3, 2.4, 3.1, 3.3, 3.4, 4.1, 4.6_

  - [ ]\* 4.1 Write property test for status filter correctness
    - **Property 2: Status Filter Correctness**
    - **Validates: Requirements 2.2**
    - Tag: `# Feature: org-level-qr-blocks, Property 2: status filter correctness`

  - [ ]\* 4.2 Write property test for product filter correctness
    - **Property 3: Product Filter Correctness**
    - **Validates: Requirements 3.2**
    - Tag: `# Feature: org-level-qr-blocks, Property 3: product filter correctness`

- [x] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Write unit tests
  - Create or extend the test file for the qr_products module
  - [x] 6.1 Test `list_by_org` returns only blocks for the given `organization_id`
    - _Requirements: 1.3, 5.1_
  - [x] 6.2 Test `list_by_org` excludes blocks where `deleted_at IS NOT NULL`
    - _Requirements: 1.6, 6.1_
  - [x] 6.3 Test `list_by_org` with `status="completed"` returns only completed blocks
    - _Requirements: 2.2_
  - [x] 6.4 Test `list_by_org` with a `product_id` from a different org returns empty list
    - _Requirements: 3.4, 5.2_
  - [x] 6.5 Test `list_blocks_by_org` builds correct pagination dict when `total_items=0` (`total_pages` must be 1)
    - _Requirements: 4.3_
  - [x] 6.6 Test `OrgBlockListItem` serializes `product_name=None` when product is soft-deleted
    - _Requirements: 7.3_
  - [ ]\* 6.7 Test endpoint returns HTTP 422 for `status="invalid_value"`
    - _Requirements: 2.4_
  - [ ]\* 6.8 Test endpoint returns HTTP 403 when `qr_product.read` permission is missing
    - _Requirements: 1.2_

- [ ] 7. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Sub-tasks marked with `*` are optional and can be skipped for a faster MVP
- Route ordering is critical: `/blocks` must appear before `/{product_id}/blocks` in the router file
- The `outerjoin` (not inner join) ensures blocks whose parent product is soft-deleted still appear, with `product_name=None`
- No migrations are needed — this is a read-only query extension
- Property tests use `hypothesis` with `hypothesis.strategies`; each test should run a minimum of 100 iterations
