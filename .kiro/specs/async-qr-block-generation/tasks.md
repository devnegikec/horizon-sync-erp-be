# Implementation Tasks: Async QR Block Generation with Celery & Redis

## Task Breakdown

### 1. Infrastructure Setup

#### 1.1 Redis Configuration

- [x] Add Redis service to `docker-compose.yml`
  - Use `redis:7-alpine` image
  - Configure port 6379
  - Add volume for data persistence
  - Add health check command
  - Enable AOF persistence with `--appendonly yes`

#### 1.2 Celery Dependencies

- [x] Add `celery[redis]>=5.3.0` to `requirements.txt`
- [x] Add `redis>=5.0.0` to `requirements.txt`
- [x] Add `flower>=2.0.0` to `requirements.txt` (monitoring)

#### 1.3 Celery Application Setup

- [x] Create `core-service/app/celery_app.py`
  - Configure broker URL from `REDIS_URL` env var
  - Configure result backend URL from `REDIS_URL` env var
  - Set task serializer to `json`
  - Set result serializer to `json`
  - Configure timezone to `UTC`
  - Enable task tracking with `task_track_started=True`
  - Set task time limits (3600s hard, 3300s soft)
  - Configure worker settings (prefetch=1, max_tasks_per_child=50)
  - Set result expiry to 24 hours
  - Enable late acks and reject on worker lost
  - Add autodiscover for `app.tasks` module

#### 1.4 Configuration Settings

- [x] Add to `core-service/app/config.py`:
  - `redis_url: str` (default: "redis://localhost:6379/0")
  - `enable_async_block_generation: bool` (default: True)
  - `celery_task_max_retries: int` (default: 3)
  - `celery_task_retry_delay: int` (default: 60)
  - `celery_batch_size: int` (default: 1000)

#### 1.5 Docker Services

- [x] Add `celery-worker` service to `docker-compose.yml`
  - Command: `celery -A app.celery_app worker --loglevel=info --concurrency=4`
  - Depends on: db, redis
  - Mount volumes for code and GCS credentials
  - Pass required environment variables
- [x] Add `celery-beat` service to `docker-compose.yml`
  - Command: `celery -A app.celery_app beat --loglevel=info`
  - Depends on: db, redis
- [x] Add `flower` service to `docker-compose.yml` (optional monitoring)
  - Command: `celery -A app.celery_app flower --port=5555`
  - Expose port 5555
  - Depends on: redis, celery-worker

---

### 2. Database Schema Changes

#### 2.1 Create Alembic Migration

- [x] Generate migration: `alembic revision -m "add_async_task_fields_to_qr_blocks"`
- [x] Add columns to `qr_blocks` table:
  - `task_status VARCHAR(20)` (nullable)
  - `error_message TEXT` (nullable)
  - `progress_current INTEGER` (nullable)
  - `progress_total INTEGER` (nullable)
- [x] Add index on `task_id` column
- [x] Backfill existing blocks:
  - Set `task_status='success'` where `status='completed'`
  - Set `task_status='failure'` where `status='failed'`

#### 2.2 Update QRBlock Model

- [x] Add fields to `core-service/app/models/qr_block.py`:
  - `task_status: str | None`
  - `error_message: str | None`
  - `progress_current: int | None`
  - `progress_total: int | None`
- [x] Add `@property` method `progress_percent` that calculates percentage
- [x] Update `__repr__` to include task_status

#### 2.3 Run Migration

- [ ] Test migration on local database
- [ ] Test rollback
- [ ] Document migration in changelog

---

### 3. Async Endpoint Implementation

#### 3.1 Update QRProductService

- [ ] Create `create_block_async()` method in `core-service/app/services/qr_product_service.py`:
  - Validate product exists and belongs to org
  - Check credit balance via `CreditService.check_balance()`
  - Create block with `status="queued"`, `task_status="pending"`
  - Set `progress_total` to quantity, `progress_current` to 0
  - Import and dispatch `generate_qr_block_task.delay()`
  - Store returned `task.id` in `block.task_id`
  - Commit and return block
  - Add logging for task dispatch

#### 3.2 Update Block Creation Endpoint

- [ ] Modify `POST /api/v1/qr-products/{product_id}/blocks` in `core-service/app/api/v1/endpoints/qr_products.py`:
  - Change status code to `202 Accepted`
  - Add feature flag check for `settings.enable_async_block_generation`
  - If True: call `service.create_block_async()`
  - If False: call existing `service.generate_block()` (backward compatibility)
  - Update response model to include `task_id`

#### 3.3 Update Response Schema

- [ ] Modify `QRBlockResponse` in `core-service/app/schemas/qr_product.py`:
  - Add `task_id: str | None`
  - Add `task_status: str | None`
  - Add `error_message: str | None`
  - Add `progress_current: int | None`
  - Add `progress_total: int | None`

---

### 4. Background Task Implementation

#### 4.1 Create Task Module

- [x] Create `core-service/app/tasks/__init__.py`
- [x] Create `core-service/app/tasks/qr_generation.py`

#### 4.2 Implement DatabaseTask Base Class

- [ ] Create `DatabaseTask` class inheriting from `celery.Task`:
  - Add `_db` property for session management
  - Implement `db` property that creates `SessionLocal()` if needed
  - Implement `after_return()` to close session

#### 4.3 Implement Main Generation Task

- [ ] Create `generate_qr_block_task` in `core-service/app/tasks/qr_generation.py`:
  - Decorate with `@celery_app.task(bind=True, base=DatabaseTask)`
  - Set `max_retries=3`, `default_retry_delay=60`
  - Configure `autoretry_for` tuple (OperationalError, ConnectionError)
  - Enable `retry_backoff=True`, `retry_backoff_max=600`, `retry_jitter=True`
  - Accept parameters: `block_id: str`, `organization_id: str`, `user_id: str`

#### 4.4 Task Implementation Steps

- [ ] Load block from database using `QRBlockRepository`
- [ ] Validate block exists and belongs to org
- [ ] Update block status to `"in_progress"`, `task_status="started"`
- [ ] Load product and brand (if applicable)
- [ ] Decrypt brand private key if needed
- [ ] Generate items in batches:
  - Loop from 0 to quantity in steps of `settings.celery_batch_size`
  - Call `_generate_product_items_batch()` for each batch
  - Update `block.progress_current` after each batch
  - Commit after each batch
  - Call `self.update_state(state='PROGRESS', meta={...})` with progress info
  - Log batch completion
- [ ] Generate Excel file using `_build_excel_for_block()`
- [ ] Upload Excel to GCS using `storage_service.upload_file()`
- [ ] Get signed download URL
- [ ] Update block: `status="completed"`, `task_status="success"`, set `download_url` and `completed_at`
- [ ] Deduct credits via `CreditService.deduct_credits()`
- [ ] Return success dict with block_id and items_generated

#### 4.5 Error Handling

- [ ] Wrap entire task in try-except
- [ ] On exception:
  - Log exception with context
  - Update block status to `"failed"`, `task_status="failure"`
  - Store error message in `block.error_message` (truncate to 1000 chars)
  - Commit changes
  - If retries remaining: call `self.retry(exc=e)`
  - Otherwise: re-raise exception
- [ ] Add nested try-except for status update to handle update failures

#### 4.6 Batch Generation Helper

- [ ] Create `_generate_product_items_batch()` method in `QRProductService`:
  - Accept: block, product, brand, private_key, org_id, user_id, start_index, count
  - Generate serial numbers for batch
  - Handle Static QR (same serial for all)
  - Handle SecureCode (generate 12-char secret)
  - Handle OneTime (set qr_active based on activation_method)
  - Sign items if brand is linked
  - Handle Dual QR (generate second URL in extra_data)
  - Build list of item dicts
  - Call `self.item_repo.bulk_create(items)`

---

### 5. Status Polling Endpoint

#### 5.1 Create Status Endpoint

- [ ] Add `GET /api/v1/qr-products/blocks/{block_id}/status` to `core-service/app/api/v1/endpoints/qr_products.py`:
  - Require `qr_product.read` permission
  - Load block from database
  - If `block.task_id` exists:
    - Create `AsyncResult(block.task_id, app=celery_app)`
    - Get `task_result.state`
    - If state is `'PROGRESS'`: get `task_result.info` dict
  - Build and return `QRBlockStatusResponse`

#### 5.2 Create Response Schemas

- [ ] Create `ProgressInfo` schema in `core-service/app/schemas/qr_product.py`:
  - `current: int`
  - `total: int`
  - `percent: int`
  - `status: str`
- [ ] Create `QRBlockStatusResponse` schema:
  - `block_id: UUID`
  - `status: str`
  - `task_id: str | None`
  - `task_state: str | None`
  - `progress: ProgressInfo | None`
  - `download_url: str | None`
  - `completed_at: datetime | None`
  - `error_message: str | None`

---

### 6. Health Check and Monitoring

#### 6.1 Celery Health Check

- [ ] Create `GET /api/v1/health/celery` endpoint in `core-service/app/api/v1/endpoints/health.py`:
  - Use `celery_app.control.inspect()`
  - Get `inspect.active()` to check for active workers
  - If no workers: return 503 with error message
  - If workers exist: return 200 with worker list and count
  - Wrap in try-except for connection errors

#### 6.2 Logging Configuration

- [ ] Add Celery-specific logging configuration
- [ ] Log task start with block_id, task_id, quantity, org_id
- [ ] Log batch completion with progress
- [ ] Log task completion with duration
- [ ] Log task failures with full context and stack trace

---

### 7. Testing

#### 7.1 Unit Tests for Task

- [ ] Create `tests/tasks/test_qr_generation.py`
- [ ] Test task dispatch returns task_id
- [ ] Test task execution with mocked dependencies:
  - Mock database session
  - Mock QRProductService methods
  - Mock storage_service
  - Mock CreditService
- [ ] Test task retry logic:
  - Mock OperationalError and verify retry
  - Mock ConnectionError and verify retry
  - Verify max retries respected
- [ ] Test task failure handling:
  - Verify block status updated to "failed"
  - Verify error_message stored
  - Verify credits NOT deducted

#### 7.2 Unit Tests for Service

- [ ] Create `tests/services/test_qr_product_service_async.py`
- [ ] Test `create_block_async()`:
  - Verify block created with correct status
  - Verify task dispatched
  - Verify task_id stored
  - Verify credits checked but not deducted
- [ ] Test `_generate_product_items_batch()`:
  - Test with different QR types (D, S, B, O, SC)
  - Test with and without brand signing
  - Test serial number generation
  - Verify bulk insert called

#### 7.3 Integration Tests

- [ ] Create `tests/integration/test_async_block_generation.py`
- [ ] Test end-to-end flow:
  - Create block via API
  - Verify 202 response with task_id
  - Wait for task completion (use `celery.contrib.testing.worker`)
  - Poll status endpoint
  - Verify block status becomes "completed"
  - Verify download_url is set
  - Verify credits deducted
  - Verify ProductItems created
- [ ] Test failure scenarios:
  - Insufficient credits
  - Invalid product_id
  - GCS upload failure (mock)
- [ ] Test concurrent block generation:
  - Create multiple blocks simultaneously
  - Verify all complete successfully

#### 7.4 Load Tests

- [ ] Create `tests/load/test_block_generation_load.py`
- [ ] Test 100 concurrent block creations
- [ ] Test large batch (10,000 items)
- [ ] Measure task execution time
- [ ] Measure API response time
- [ ] Verify no memory leaks

---

### 8. Documentation

#### 8.1 API Documentation

- [ ] Update OpenAPI schema with new endpoints
- [ ] Document 202 response for block creation
- [ ] Document status polling endpoint
- [ ] Add examples for async workflow
- [ ] Document task states and transitions

#### 8.2 Deployment Guide

- [ ] Document Redis setup requirements
- [ ] Document Celery worker deployment
- [ ] Document environment variables
- [ ] Document monitoring with Flower
- [ ] Document scaling guidelines (worker count, concurrency)

#### 8.3 Migration Guide

- [ ] Document feature flag usage
- [ ] Document rollback procedure
- [ ] Document database migration steps
- [ ] Document testing checklist for production

---

### 9. Deployment and Rollout

#### 9.1 Staging Deployment

- [ ] Deploy Redis to staging
- [ ] Deploy Celery workers to staging
- [ ] Run database migration
- [ ] Deploy updated API code
- [ ] Verify health checks pass
- [ ] Test end-to-end flow in staging

#### 9.2 Production Rollout (Phased)

- [ ] **Phase 1**: Deploy with feature flag OFF
  - Deploy all infrastructure
  - Verify workers are running
  - Monitor for 24 hours
- [ ] **Phase 2**: Enable for 10% of requests
  - Set feature flag to True for 10% of orgs
  - Monitor metrics (success rate, execution time)
  - Monitor error logs
  - Run for 48 hours
- [ ] **Phase 3**: Increase to 50%
  - Increase feature flag to 50% of orgs
  - Monitor for 48 hours
- [ ] **Phase 4**: Enable for 100%
  - Enable feature flag for all orgs
  - Monitor for 1 week
- [ ] **Phase 5**: Remove synchronous code
  - Remove old `generate_block()` method
  - Remove feature flag
  - Update documentation

#### 9.3 Monitoring Setup

- [ ] Set up Flower dashboard
- [ ] Configure alerts for:
  - No active workers
  - High task failure rate (>5%)
  - Long task execution time (>5 minutes for 5000 items)
  - High queue depth (>100 tasks)
- [ ] Set up log aggregation for Celery logs
- [ ] Create dashboard for key metrics

---

### 10. Optional Enhancements

#### 10.1 Task Cancellation

- [ ] Create `POST /api/v1/qr-products/blocks/{block_id}/cancel` endpoint
- [ ] Implement cancellation logic:
  - Verify block status is "queued" or "in_progress"
  - Call `celery_app.control.revoke(task_id, terminate=True)`
  - Update block status to "cancelled"
  - Do NOT deduct credits
- [ ] Require `qr_product.delete` permission
- [ ] Add tests for cancellation

#### 10.2 Progress Webhooks

- [ ] Add webhook URL field to QRBlock
- [ ] Send webhook on status changes:
  - Task started
  - Progress updates (every 25%)
  - Task completed
  - Task failed
- [ ] Implement retry logic for webhook delivery

#### 10.3 Task Priority

- [ ] Add priority field to QRBlock
- [ ] Configure Celery routing for priority queues
- [ ] High priority tasks go to dedicated queue
- [ ] Update task dispatch to use priority

---

## Task Dependencies

```
1. Infrastructure Setup (1.1-1.5)
   └─▶ 2. Database Schema Changes (2.1-2.3)
       └─▶ 3. Async Endpoint Implementation (3.1-3.3)
           └─▶ 4. Background Task Implementation (4.1-4.6)
               ├─▶ 5. Status Polling Endpoint (5.1-5.2)
               ├─▶ 6. Health Check and Monitoring (6.1-6.2)
               └─▶ 7. Testing (7.1-7.4)
                   └─▶ 8. Documentation (8.1-8.3)
                       └─▶ 9. Deployment and Rollout (9.1-9.3)
                           └─▶ 10. Optional Enhancements (10.1-10.3)
```

## Estimated Timeline

| Phase                        | Duration    | Dependencies |
| ---------------------------- | ----------- | ------------ |
| 1. Infrastructure Setup      | 2 days      | None         |
| 2. Database Schema Changes   | 1 day       | Phase 1      |
| 3. Async Endpoint            | 2 days      | Phase 2      |
| 4. Background Task           | 3 days      | Phase 3      |
| 5. Status Polling            | 1 day       | Phase 4      |
| 6. Health Check & Monitoring | 1 day       | Phase 4      |
| 7. Testing                   | 3 days      | Phase 4-6    |
| 8. Documentation             | 2 days      | Phase 7      |
| 9. Deployment & Rollout      | 5 days      | Phase 8      |
| 10. Optional Enhancements    | 3 days      | Phase 9      |
| **Total**                    | **23 days** |              |

## Success Criteria

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Load tests show <200ms API response time
- [ ] Task execution time <30s for 5000 items
- [ ] Task failure rate <1%
- [ ] Zero timeout errors for large batches
- [ ] Celery workers auto-restart on failure
- [ ] Monitoring dashboard shows all metrics
- [ ] Documentation complete and reviewed
- [ ] Production rollout successful with no incidents
