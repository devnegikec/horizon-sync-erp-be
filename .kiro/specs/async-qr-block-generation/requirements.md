# Requirements Document: Async QR Block Generation with Celery & Redis

## Introduction

This document defines the requirements for migrating QR block generation from synchronous (blocking HTTP requests) to asynchronous background processing using Celery with Redis as the message broker. This enhancement addresses timeout issues with large batch generation, enables progress tracking, and improves system scalability.

## Glossary

- **Celery**: Distributed task queue system for asynchronous job processing
- **Redis**: In-memory data store used as Celery's message broker and result backend
- **Task**: A unit of work executed asynchronously by a Celery worker
- **Worker**: A Celery process that consumes tasks from the queue
- **Broker**: Message queue system (Redis) that holds tasks waiting to be executed
- **Result Backend**: Storage system (Redis) that stores task results and status
- **Task ID**: Unique identifier for a Celery task (UUID format)
- **Task State**: Current status of a task (PENDING, STARTED, SUCCESS, FAILURE, RETRY)
- **QRBlock**: Batch record representing a QR code generation request
- **Block Status**: Application-level status (pending, in_progress, completed, failed)

## Background

### Current Implementation (Synchronous)

The existing implementation in `core-service/app/services/qr_product_service.py` generates QR blocks synchronously:

```python
def generate_block(self, product_id, data, organization_id, user_id) -> QRBlock:
    # 1. Create block with status="pending"
    block = self.block_repo.create(block_dict)

    # 2. Set status="in_progress"
    block.status = "in_progress"
    self.db.commit()

    # 3. Generate all items (BLOCKS HTTP REQUEST)
    self._generate_product_items(block, product, organization_id, user_id)

    # 4. Mark completed
    block.status = "completed"
    self.db.commit()
```

**Problems:**

- HTTP request blocks for entire generation (can take minutes for 10,000 QR codes)
- No progress tracking during generation
- Risk of timeout for large batches
- Cannot scale horizontally (all generation in web process)
- Frontend has no way to show progress

### Target Implementation (Async)

```python
def generate_block(self, product_id, data, organization_id, user_id) -> QRBlock:
    # 1. Create block with status="pending"
    block = self.block_repo.create(block_dict)

    # 2. Dispatch Celery task (returns immediately)
    task = generate_qr_block_task.delay(block.id, organization_id, user_id)

    # 3. Store task_id
    block.task_id = task.id
    block.status = "queued"
    self.db.commit()

    # 4. Return immediately
    return block
```

**Benefits:**

- HTTP request returns in <100ms
- Frontend can poll for status updates
- Progress tracking (e.g., "Generated 5000/10000 items")
- Horizontal scaling (multiple workers)
- Retry logic for transient failures

## Requirements

### Requirement 1: Celery Infrastructure Setup

**User Story:** As a platform operator, I want Celery configured with Redis, so that background tasks can be processed reliably.

#### Acceptance Criteria

1. THE system SHALL use Redis as both the message broker and result backend for Celery.
2. THE Celery app SHALL be configured in `core-service/app/celery_app.py` with:
   - Broker URL from `REDIS_URL` environment variable
   - Result backend URL from `REDIS_URL` environment variable
   - Task serializer set to `json`
   - Result serializer set to `json`
   - Accept content types: `['json']`
   - Timezone set to `UTC`
   - Enable UTC timestamps
3. THE Celery app SHALL autodiscover tasks from `core-service/app/tasks/` directory.
4. THE system SHALL provide a Celery worker startup command: `celery -A app.celery_app worker --loglevel=info`.
5. THE system SHALL provide a Celery beat scheduler startup command (for future scheduled tasks): `celery -A app.celery_app beat --loglevel=info`.
6. THE `docker-compose.yml` SHALL include:
   - Redis service (port 6379)
   - Celery worker service
   - Celery beat service (optional)
7. THE system SHALL add `celery[redis]` and `redis` to `requirements.txt`.

### Requirement 2: Async Block Creation Endpoint

**User Story:** As a user with `qr_product.create` permission, I want block creation to return immediately with a task ID, so that I don't have to wait for generation to complete.

#### Acceptance Criteria

1. WHEN a user sends POST `/api/v1/qr-products/{product_id}/blocks`, THE endpoint SHALL:
   - Validate inputs (quantity, qr_type, etc.)
   - Check credit balance via CreditService
   - Create QRBlock record with `status="queued"` and `task_status="pending"`
   - Dispatch `generate_qr_block_task.delay(block_id, organization_id, user_id)`
   - Store the Celery `task.id` in `QRBlock.task_id`
   - Return 202 Accepted with block details including `task_id`
2. THE endpoint SHALL return within 200ms regardless of block quantity.
3. THE response SHALL include:
   ```json
   {
     "id": "block-uuid",
     "task_id": "celery-task-uuid",
     "status": "queued",
     "quantity": 5000,
     "created_at": "2025-01-15T10:00:00Z"
   }
   ```
4. IF credit validation fails, THE endpoint SHALL return 422 without creating a block or dispatching a task.

### Requirement 3: Background QR Block Generation Task

**User Story:** As a Celery worker, I want to generate QR blocks in the background, so that HTTP requests don't block.

#### Acceptance Criteria

1. THE `generate_qr_block_task` SHALL be defined in `core-service/app/tasks/qr_generation.py` with signature:
   ```python
   @celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
   def generate_qr_block_task(self, block_id: str, organization_id: str, user_id: str):
   ```
2. THE task SHALL:
   - Update block status to `"in_progress"` and `task_status="started"`
   - Load QRProduct and Brand (if applicable)
   - Decrypt Brand private key (if signing required)
   - Generate serial numbers for all items
   - Sign each item (if Brand linked)
   - Create ProductItem records in batches of 1000
   - Generate Excel file
   - Upload Excel to GCS
   - Update block status to `"completed"`, set `download_url` and `completed_at`
   - Deduct credits via CreditService
3. THE task SHALL update progress metadata every 1000 items:
   ```python
   self.update_state(
       state='PROGRESS',
       meta={'current': 5000, 'total': 10000, 'status': 'Generating items...'}
   )
   ```
4. IF any step fails, THE task SHALL:
   - Retry up to 3 times with 60-second delay
   - After max retries, update block status to `"failed"`
   - Store error message in `QRBlock.error_message` field (NEW)
   - NOT deduct credits
5. THE task SHALL use a new database session (not the HTTP request session).
6. THE task SHALL commit after each batch of 1000 items to avoid long-running transactions.

### Requirement 4: Task Status Polling Endpoint

**User Story:** As a frontend developer, I want to poll for block generation status, so that I can show progress to users.

#### Acceptance Criteria

1. THE system SHALL provide GET `/api/v1/qr-products/blocks/{block_id}/status` endpoint.
2. THE endpoint SHALL return:
   ```json
   {
     "block_id": "uuid",
     "status": "in_progress",
     "task_id": "celery-task-uuid",
     "task_state": "PROGRESS",
     "progress": {
       "current": 5000,
       "total": 10000,
       "percent": 50,
       "status": "Generating items..."
     },
     "download_url": null,
     "completed_at": null,
     "error_message": null
   }
   ```
3. WHEN block status is `"completed"`, THE response SHALL include `download_url` and `completed_at`.
4. WHEN block status is `"failed"`, THE response SHALL include `error_message`.
5. THE endpoint SHALL query Celery task state via `AsyncResult(task_id).state` and merge with QRBlock status.
6. THE endpoint SHALL be accessible with `qr_product.read` permission.

### Requirement 5: Enhanced QRBlock Model

**User Story:** As a developer, I want QRBlock to store task metadata, so that I can track generation progress and errors.

#### Acceptance Criteria

1. THE `QRBlock` model SHALL add the following fields:
   - `task_id: str | None` — Celery task UUID (already exists)
   - `task_status: str | None` — Celery task state (pending, started, progress, success, failure)
   - `error_message: Text | None` — Error details if generation fails
   - `progress_current: int | None` — Current item count during generation
   - `progress_total: int | None` — Total item count
2. THE `status` field SHALL use values: `queued`, `in_progress`, `completed`, `failed`.
3. THE Alembic migration SHALL add these fields with nullable=True for backward compatibility.

### Requirement 6: Task Retry and Error Handling

**User Story:** As a platform operator, I want tasks to retry on transient failures, so that temporary issues don't cause permanent failures.

#### Acceptance Criteria

1. THE `generate_qr_block_task` SHALL retry on:
   - Database connection errors (sqlalchemy.exc.OperationalError)
   - GCS upload errors (google.cloud.exceptions.GoogleCloudError)
   - Redis connection errors (redis.exceptions.ConnectionError)
2. THE task SHALL NOT retry on:
   - Validation errors (insufficient credits, invalid data)
   - Business logic errors (duplicate serial numbers after 3 retries)
3. THE task SHALL use exponential backoff: 60s, 120s, 240s.
4. THE task SHALL log all retry attempts with context (block_id, attempt number, error).
5. WHEN max retries are exhausted, THE task SHALL:
   - Update block status to `"failed"`
   - Store error message in `QRBlock.error_message`
   - Send alert to monitoring system (optional)

### Requirement 7: Batch Processing for Performance

**User Story:** As a Celery worker, I want to process items in batches, so that large blocks don't cause memory issues or long transactions.

#### Acceptance Criteria

1. THE task SHALL generate ProductItem records in batches of 1000.
2. THE task SHALL commit after each batch to avoid long-running transactions.
3. THE task SHALL update progress metadata after each batch.
4. THE task SHALL use bulk insert for ProductItem creation:
   ```python
   db.bulk_insert_mappings(ProductItem, item_dicts)
   ```
5. IF a batch fails, THE task SHALL retry only that batch (not the entire block).

### Requirement 8: Task Cancellation (Optional)

**User Story:** As a user, I want to cancel a queued or in-progress block generation, so that I can stop unwanted tasks.

#### Acceptance Criteria

1. THE system SHALL provide POST `/api/v1/qr-products/blocks/{block_id}/cancel` endpoint.
2. THE endpoint SHALL:
   - Revoke the Celery task via `celery_app.control.revoke(task_id, terminate=True)`
   - Update block status to `"cancelled"`
   - NOT deduct credits
3. THE endpoint SHALL only allow cancellation if block status is `"queued"` or `"in_progress"`.
4. THE endpoint SHALL require `qr_product.delete` permission.

### Requirement 9: Monitoring and Observability

**User Story:** As a platform operator, I want to monitor task execution, so that I can identify bottlenecks and failures.

#### Acceptance Criteria

1. THE system SHALL log task start, progress, completion, and failure events.
2. THE system SHALL expose Celery metrics via Flower (optional):
   - Task success/failure rates
   - Task execution time
   - Worker status
3. THE system SHALL provide a health check endpoint for Celery workers:
   - GET `/api/v1/health/celery` returns 200 if workers are active, 503 otherwise.

### Requirement 10: Backward Compatibility

**User Story:** As a developer, I want existing synchronous block generation to continue working, so that migration is gradual.

#### Acceptance Criteria

1. THE system SHALL support a feature flag `ENABLE_ASYNC_BLOCK_GENERATION` (default: True).
2. WHEN the flag is False, THE endpoint SHALL use the existing synchronous generation.
3. WHEN the flag is True, THE endpoint SHALL use async Celery tasks.
4. THE system SHALL provide a migration path for existing blocks without `task_id`.

### Requirement 11: Testing Requirements

**User Story:** As a developer, I want comprehensive tests for async tasks, so that I can ensure reliability.

#### Acceptance Criteria

1. THE system SHALL provide unit tests for:
   - Task dispatch and immediate return
   - Task execution with mocked dependencies
   - Task retry logic
   - Task failure handling
2. THE system SHALL provide integration tests for:
   - End-to-end block generation via Celery
   - Status polling during generation
   - Credit deduction after successful generation
3. THE system SHALL use `celery.contrib.testing.worker` for testing tasks.

## Non-Functional Requirements

### Performance

- Block creation endpoint SHALL return within 200ms
- Task SHALL process 1000 items per second (signing + DB insert)
- Status polling endpoint SHALL return within 50ms

### Scalability

- System SHALL support multiple Celery workers (horizontal scaling)
- System SHALL handle 100 concurrent block generation tasks

### Reliability

- Task SHALL have 99.9% success rate (excluding validation errors)
- Failed tasks SHALL be retried automatically
- System SHALL not lose tasks (Redis persistence enabled)

### Security

- Task SHALL validate organization_id to prevent cross-tenant access
- Task SHALL not log sensitive data (private keys, signatures)

## Dependencies

- `celery[redis]>=5.3.0`
- `redis>=5.0.0`
- Existing: `cryptography`, `sqlalchemy`, `google-cloud-storage`

## Migration Strategy

1. **Phase 1**: Add Celery infrastructure (no behavior change)
2. **Phase 2**: Implement async task (feature flag OFF)
3. **Phase 3**: Enable feature flag for new blocks
4. **Phase 4**: Migrate existing in-progress blocks (if any)
5. **Phase 5**: Remove synchronous code path

## Success Metrics

- 95% of block creation requests return within 200ms
- 0 timeout errors for large batches (10,000 items)
- Task failure rate <1%
- Average task execution time: <30 seconds for 5000 items
