# Design Document: Async QR Block Generation with Celery & Redis

## Overview

This design document describes the technical architecture for migrating QR block generation from synchronous (blocking) to asynchronous (non-blocking) processing using Celery with Redis. The solution enables immediate API responses, progress tracking, horizontal scaling, and improved reliability through retry mechanisms.

## Architecture

### High-Level Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Frontend  │────────▶│  FastAPI     │────────▶│   Redis     │
│             │  POST   │  Web Server  │  Enqueue│  (Broker)   │
│             │  /blocks│              │  Task   │             │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │                         │
      │ Poll Status            │ Store Block             │
      │                        ▼                         ▼
      │                  ┌──────────────┐         ┌─────────────┐
      └─────────────────▶│  PostgreSQL  │◀────────│   Celery    │
                         │   Database   │  Update │   Worker    │
                         └──────────────┘  Status └─────────────┘
                                                         │
                                                         │ Upload
                                                         ▼
                                                   ┌─────────────┐
                                                   │     GCS     │
                                                   │   Storage   │
                                                   └─────────────┘
```

### Component Responsibilities

| Component          | Responsibility                                                        |
| ------------------ | --------------------------------------------------------------------- |
| FastAPI Web Server | Validate requests, create block records, dispatch tasks, serve status |
| Redis              | Message broker for task queue, result backend for task state          |
| Celery Worker      | Execute background tasks, generate QR codes, upload to GCS            |
| PostgreSQL         | Store block metadata, product items, task status                      |
| GCS                | Store generated Excel files                                           |

## Detailed Design

### 1. Celery Configuration

**File**: `core-service/app/celery_app.py`

```python
from celery import Celery
from app.config import settings

celery_app = Celery(
    "qr_generation",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks
    result_expires=86400,  # Results expire after 24 hours
    task_acks_late=True,  # Acknowledge task after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
)

# Autodiscover tasks
celery_app.autodiscover_tasks(["app.tasks"])
```

**Configuration Settings** (`core-service/app/config.py`):

```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Redis/Celery
    redis_url: str = "redis://localhost:6379/0"
    enable_async_block_generation: bool = True

    # Task settings
    celery_task_max_retries: int = 3
    celery_task_retry_delay: int = 60
    celery_batch_size: int = 1000
```

### 2. Database Schema Changes

**Migration**: `alembic/versions/XXX_add_async_task_fields.py`

```python
def upgrade():
    # Add task tracking fields to qr_blocks
    op.add_column('qr_blocks', sa.Column('task_status', sa.String(20), nullable=True))
    op.add_column('qr_blocks', sa.Column('error_message', sa.Text, nullable=True))
    op.add_column('qr_blocks', sa.Column('progress_current', sa.Integer, nullable=True))
    op.add_column('qr_blocks', sa.Column('progress_total', sa.Integer, nullable=True))

    # Update existing blocks
    op.execute("UPDATE qr_blocks SET task_status = 'success' WHERE status = 'completed'")
    op.execute("UPDATE qr_blocks SET task_status = 'failure' WHERE status = 'failed'")
```

**Model Updates** (`core-service/app/models/qr_block.py`):

```python
class QRBlock(Base):
    __tablename__ = "qr_blocks"

    # ... existing fields ...

    # Task tracking
    task_id = Column(String(255), nullable=True, index=True)
    task_status = Column(String(20), nullable=True)  # pending, started, progress, success, failure
    error_message = Column(Text, nullable=True)
    progress_current = Column(Integer, nullable=True)
    progress_total = Column(Integer, nullable=True)

    @property
    def progress_percent(self) -> int | None:
        if self.progress_total and self.progress_current:
            return int((self.progress_current / self.progress_total) * 100)
        return None
```

### 3. Async Block Creation Endpoint

**File**: `core-service/app/api/v1/endpoints/qr_products.py`

```python
@router.post(
    "/{product_id}/blocks",
    response_model=QRBlockResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_qr_block(
    product_id: UUID,
    data: QRBlockCreate,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("qr_product.create")),
):
    """
    Create a QR block and dispatch background generation task.
    Returns immediately with task_id for status polling.
    """
    service = QRProductService(db)

    if settings.enable_async_block_generation:
        # Async path
        block = service.create_block_async(
            product_id=product_id,
            data=data,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
    else:
        # Synchronous fallback
        block = service.generate_block(
            product_id=product_id,
            data=data,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )

    return block
```

**Service Method** (`core-service/app/services/qr_product_service.py`):

```python
def create_block_async(
    self,
    product_id: UUID,
    data: QRBlockCreate,
    organization_id: UUID,
    user_id: UUID,
) -> QRBlock:
    """Create block and dispatch async generation task."""
    from app.tasks.qr_generation import generate_qr_block_task

    # 1. Validate product
    product = self.get_product(product_id, organization_id)

    # 2. Check credits
    self.credit_service.check_balance(organization_id, data.quantity)

    # 3. Create block record
    block_dict = {k: v for k, v in data.model_dump().items() if k != "qr_type"}
    block_dict["product_id"] = product_id
    block_dict["organization_id"] = organization_id
    block_dict["created_by"] = user_id
    block_dict["updated_by"] = user_id
    block_dict["status"] = "queued"
    block_dict["task_status"] = "pending"
    block_dict["progress_total"] = data.quantity
    block_dict["progress_current"] = 0

    block = self.block_repo.create(block_dict)

    # 4. Dispatch Celery task
    task = generate_qr_block_task.delay(
        block_id=str(block.id),
        organization_id=str(organization_id),
        user_id=str(user_id),
    )

    # 5. Store task_id
    block.task_id = task.id
    self.db.commit()

    logger.info(
        "QR block queued: block_id=%s task_id=%s qty=%d org=%s",
        block.id,
        task.id,
        data.quantity,
        organization_id,
    )

    return block
```

### 4. Background Task Implementation

**File**: `core-service/app/tasks/qr_generation.py`

```python
from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy.orm import Session
from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.qr_product_service import QRProductService
from app.repositories.qr_product_repository import QRBlockRepository
from uuid import UUID

logger = get_task_logger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""

    _db: Session | None = None

    @property
    def db(self) -> Session:
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(
        sqlalchemy.exc.OperationalError,
        redis.exceptions.ConnectionError,
    ),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def generate_qr_block_task(
    self,
    block_id: str,
    organization_id: str,
    user_id: str,
):
    """
    Background task to generate QR block.

    Args:
        block_id: UUID of the QRBlock
        organization_id: UUID of the organization
        user_id: UUID of the user who created the block
    """
    logger.info(f"Starting QR block generation: block_id={block_id}")

    db = self.db
    block_repo = QRBlockRepository(db)

    try:
        # Load block
        block = block_repo.get_by_id(UUID(block_id), UUID(organization_id))
        if not block:
            raise ValueError(f"Block not found: {block_id}")

        # Update status
        block.status = "in_progress"
        block.task_status = "started"
        db.commit()

        # Generate items in batches
        service = QRProductService(db)
        product = service.get_product(block.product_id, UUID(organization_id))

        # Decrypt brand key if needed
        brand = None
        private_key = None
        if product.brand_id and service.key_service:
            from app.repositories.brand_repository import BrandRepository
            brand_repo = BrandRepository(db)
            brand = brand_repo.get_by_id(product.brand_id, UUID(organization_id))
            if brand and brand.private_key_encrypted:
                private_key = service.key_service.decrypt_private_key(
                    brand.private_key_encrypted
                )

        # Generate items in batches
        batch_size = settings.celery_batch_size
        total_items = block.quantity

        for batch_start in range(0, total_items, batch_size):
            batch_end = min(batch_start + batch_size, total_items)
            batch_count = batch_end - batch_start

            # Generate batch
            service._generate_product_items_batch(
                block=block,
                product=product,
                brand=brand,
                private_key=private_key,
                organization_id=UUID(organization_id),
                user_id=UUID(user_id),
                start_index=batch_start,
                count=batch_count,
            )

            # Update progress
            block.progress_current = batch_end
            db.commit()

            # Update Celery task state
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': batch_end,
                    'total': total_items,
                    'percent': int((batch_end / total_items) * 100),
                    'status': f'Generated {batch_end}/{total_items} items',
                }
            )

            logger.info(f"Batch complete: {batch_end}/{total_items} items")

        # Generate Excel file
        logger.info("Generating Excel file...")
        excel_bytes, filename = service._build_excel_for_block(block.id, UUID(organization_id))

        # Upload to GCS
        logger.info("Uploading to GCS...")
        from app.services import storage_service
        gcs_path = f"qr-blocks/{organization_id}/{block.id}/{filename}"
        storage_service.upload_file(gcs_path, excel_bytes, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Get signed URL
        download_url = storage_service.get_signed_url(gcs_path, expiry_minutes=60)

        # Mark completed
        block.status = "completed"
        block.task_status = "success"
        block.download_url = download_url
        block.completed_at = datetime.now(UTC)
        db.commit()

        # Deduct credits
        from app.services.credit_service import CreditService
        credit_service = CreditService(db)
        credit_service.deduct_credits(UUID(organization_id), block.id, block.quantity)

        logger.info(f"QR block generation complete: block_id={block_id}")

        return {
            'block_id': block_id,
            'status': 'completed',
            'items_generated': total_items,
        }

    except Exception as e:
        logger.exception(f"QR block generation failed: block_id={block_id}")

        # Update block status
        try:
            block = block_repo.get_by_id(UUID(block_id), UUID(organization_id))
            if block:
                block.status = "failed"
                block.task_status = "failure"
                block.error_message = str(e)[:1000]  # Truncate to 1000 chars
                db.commit()
        except Exception as update_error:
            logger.exception(f"Failed to update block status: {update_error}")

        # Retry if retries remaining
        if self.request.retries < self.max_retries:
            raise self.retry(exc=e)

        raise
```

**Batch Generation Helper** (`core-service/app/services/qr_product_service.py`):

```python
def _generate_product_items_batch(
    self,
    block: QRBlock,
    product: QRProduct,
    brand: Brand | None,
    private_key: Any | None,
    organization_id: UUID,
    user_id: UUID,
    start_index: int,
    count: int,
) -> None:
    """Generate a batch of ProductItems."""
    now = datetime.now(UTC)
    qr_type = (product.qr_type or "D").upper()
    sr_number_type = block.sr_number_type or product.sr_number_type
    prefix = block.serial_prefix or ""

    serial_gen = self._get_serial_generator(sr_number_type)

    # For Static QR: use same serial for all items
    static_serial = None
    if qr_type == "S" and start_index == 0:
        static_serial = f"{prefix}{serial_gen()}"

    items: list[dict] = []

    for i in range(count):
        serial = static_serial if static_serial else f"{prefix}{serial_gen()}"

        item_dict: dict = {
            "id": uuid.uuid4(),
            "organization_id": organization_id,
            "product_id": block.product_id,
            "block_id": block.id,
            "serial_number": serial,
            "created_by": user_id,
            "updated_by": user_id,
            "created_at": now,
            "updated_at": now,
        }

        # SecureCode: generate 12-char secret
        if qr_type == "SC":
            item_dict["secrete_code"] = self._generate_secret_code()

        # OneTime: set qr_active based on activation_method
        if qr_type == "O":
            item_dict["qr_active"] = product.activation_method == "pre"

        # Sign if brand is linked
        if private_key is not None:
            sig, ts = sign_qr_item(self.key_service, private_key, serial)
            url = build_qr_url(
                brand.short_code if brand else "",
                settings.qr_domain,
                product.gtin or "",
                serial,
                ts,
                sig,
            )
            item_dict["token_id"] = url

            # Dual QR: generate second URL
            if qr_type == "B":
                sig2, ts2 = sign_qr_item(self.key_service, private_key, serial)
                covert_url = build_qr_url(
                    brand.short_code if brand else "",
                    settings.qr_domain,
                    product.gtin or "",
                    serial,
                    ts2,
                    sig2,
                )
                item_dict.setdefault("extra_data", {})
                item_dict["extra_data"]["covert_url"] = covert_url

        items.append(item_dict)

    # Bulk insert
    self.item_repo.bulk_create(items)
```

### 5. Status Polling Endpoint

**File**: `core-service/app/api/v1/endpoints/qr_products.py`

```python
@router.get(
    "/blocks/{block_id}/status",
    response_model=QRBlockStatusResponse,
)
async def get_block_status(
    block_id: UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_permission("qr_product.read")),
):
    """
    Get block generation status with real-time progress.
    Poll this endpoint to track generation progress.
    """
    service = QRProductService(db)
    block = service.get_block(block_id, current_user.organization_id)

    # Get Celery task state if task_id exists
    task_state = None
    task_meta = {}

    if block.task_id:
        from celery.result import AsyncResult
        task_result = AsyncResult(block.task_id, app=celery_app)
        task_state = task_result.state

        if task_state == 'PROGRESS':
            task_meta = task_result.info or {}

    return QRBlockStatusResponse(
        block_id=block.id,
        status=block.status,
        task_id=block.task_id,
        task_state=task_state,
        progress=ProgressInfo(
            current=task_meta.get('current', block.progress_current),
            total=block.progress_total,
            percent=task_meta.get('percent', block.progress_percent),
            status=task_meta.get('status', ''),
        ) if block.progress_total else None,
        download_url=block.download_url,
        completed_at=block.completed_at,
        error_message=block.error_message,
    )
```

**Schema** (`core-service/app/schemas/qr_product.py`):

```python
class ProgressInfo(BaseModel):
    current: int
    total: int
    percent: int
    status: str

class QRBlockStatusResponse(BaseModel):
    block_id: UUID
    status: str
    task_id: str | None
    task_state: str | None
    progress: ProgressInfo | None
    download_url: str | None
    completed_at: datetime | None
    error_message: str | None

    model_config = {"from_attributes": True}
```

### 6. Docker Compose Configuration

**File**: `docker-compose.yml`

```yaml
version: "3.8"

services:
  # ... existing services ...

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  celery-worker:
    build: ./core-service
    command: celery -A app.celery_app worker --loglevel=info --concurrency=4
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0
      - BRAND_KEY_ENCRYPTION_SECRET=${BRAND_KEY_ENCRYPTION_SECRET}
      - GCS_BUCKET=${GCS_BUCKET}
      - GCS_CREDENTIALS_PATH=${GCS_CREDENTIALS_PATH}
    volumes:
      - ./core-service:/app
      - gcs_credentials:/credentials

  celery-beat:
    build: ./core-service
    command: celery -A app.celery_app beat --loglevel=info
    depends_on:
      - db
      - redis
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=redis://redis:6379/0

  flower:
    build: ./core-service
    command: celery -A app.celery_app flower --port=5555
    ports:
      - "5555:5555"
    depends_on:
      - redis
      - celery-worker
    environment:
      - REDIS_URL=redis://redis:6379/0

volumes:
  redis_data:
  gcs_credentials:
```

### 7. Monitoring and Health Checks

**File**: `core-service/app/api/v1/endpoints/health.py`

```python
@router.get("/celery")
async def celery_health():
    """Check if Celery workers are active."""
    from app.celery_app import celery_app

    try:
        # Inspect active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        if not active_workers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No active Celery workers"
            )

        return {
            "status": "healthy",
            "workers": list(active_workers.keys()),
            "worker_count": len(active_workers),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Celery health check failed: {str(e)}"
        )
```

## Sequence Diagrams

### Block Creation Flow

```
Frontend          FastAPI          Redis          Celery Worker          PostgreSQL          GCS
   │                 │               │                  │                    │                │
   │─POST /blocks───▶│               │                  │                    │                │
   │                 │               │                  │                    │                │
   │                 │──Validate────▶│                  │                    │                │
   │                 │               │                  │                    │                │
   │                 │──Create Block─┼─────────────────▶│                    │                │
   │                 │               │                  │                    │                │
   │                 │──Enqueue Task─▶│                  │                    │                │
   │                 │               │                  │                    │                │
   │◀─202 Accepted───│               │                  │                    │                │
   │  (task_id)      │               │                  │                    │                │
   │                 │               │                  │                    │                │
   │                 │               │──Dequeue Task───▶│                    │                │
   │                 │               │                  │                    │                │
   │                 │               │                  │──Update Status────▶│                │
   │                 │               │                  │   (in_progress)    │                │
   │                 │               │                  │                    │                │
   │                 │               │                  │──Generate Items───▶│                │
   │                 │               │                  │   (batches)        │                │
   │                 │               │                  │                    │                │
   │                 │               │                  │──Build Excel───────┼───────────────▶│
   │                 │               │                  │                    │                │
   │                 │               │                  │──Update Status────▶│                │
   │                 │               │                  │   (completed)      │                │
   │                 │               │                  │                    │                │
   │                 │               │                  │──Deduct Credits───▶│                │
   │                 │               │                  │                    │                │
```

### Status Polling Flow

```
Frontend          FastAPI          Redis          PostgreSQL
   │                 │               │                │
   │─GET /status────▶│               │                │
   │                 │               │                │
   │                 │──Get Block───┼───────────────▶│
   │                 │               │                │
   │                 │──Get Task────▶│                │
   │                 │   State       │                │
   │                 │               │                │
   │◀─200 OK─────────│               │                │
   │  (progress)     │               │                │
   │                 │               │                │
```

## Error Handling Strategy

### Retry Logic

| Error Type                | Retry? | Max Retries | Backoff                       |
| ------------------------- | ------ | ----------- | ----------------------------- |
| Database connection error | Yes    | 3           | Exponential (60s, 120s, 240s) |
| GCS upload error          | Yes    | 3           | Exponential                   |
| Redis connection error    | Yes    | 3           | Exponential                   |
| Validation error          | No     | 0           | N/A                           |
| Insufficient credits      | No     | 0           | N/A                           |
| Duplicate serial number   | Yes    | 3           | Linear (60s)                  |

### Error States

```python
# Task fails after max retries
block.status = "failed"
block.task_status = "failure"
block.error_message = "GCS upload failed after 3 retries: Connection timeout"

# Credits are NOT deducted
# User can retry by creating a new block
```

## Performance Considerations

### Batch Size Tuning

- **Small batches (100-500)**: More frequent progress updates, higher overhead
- **Medium batches (1000)**: Balanced performance and progress granularity (recommended)
- **Large batches (5000+)**: Better performance, less frequent updates

### Worker Concurrency

- **Low concurrency (1-2)**: Sequential processing, predictable resource usage
- **Medium concurrency (4-8)**: Parallel processing, good throughput (recommended)
- **High concurrency (16+)**: Maximum throughput, requires more resources

### Database Connection Pooling

```python
# SQLAlchemy engine configuration
engine = create_engine(
    settings.database_url,
    pool_size=20,  # Base pool size
    max_overflow=10,  # Additional connections
    pool_pre_ping=True,  # Verify connections
    pool_recycle=3600,  # Recycle after 1 hour
)
```

## Security Considerations

1. **Task Validation**: Always validate `organization_id` in tasks to prevent cross-tenant access
2. **Private Key Handling**: Decrypt keys only in memory, never log
3. **Task Serialization**: Use JSON (not pickle) to prevent code injection
4. **Redis Security**: Enable AUTH, use TLS in production
5. **Rate Limiting**: Limit block creation to prevent abuse

## Monitoring and Observability

### Key Metrics

- Task success/failure rate
- Task execution time (p50, p95, p99)
- Queue depth
- Worker utilization
- Credit deduction accuracy

### Logging

```python
logger.info("QR block queued", extra={
    "block_id": block.id,
    "task_id": task.id,
    "quantity": block.quantity,
    "organization_id": organization_id,
})

logger.info("Batch complete", extra={
    "block_id": block.id,
    "progress": f"{batch_end}/{total_items}",
    "percent": int((batch_end / total_items) * 100),
})

logger.error("Task failed", extra={
    "block_id": block.id,
    "error": str(e),
    "retry_count": self.request.retries,
}, exc_info=True)
```

### Flower Dashboard

Access at `http://localhost:5555`:

- Active tasks
- Task history
- Worker status
- Task execution time graphs

## Migration Strategy

### Phase 1: Infrastructure Setup (Week 1)

- Add Redis to docker-compose
- Configure Celery app
- Add database migrations
- Deploy to staging

### Phase 2: Parallel Implementation (Week 2)

- Implement async task
- Add status polling endpoint
- Feature flag OFF (use sync path)
- Test in staging

### Phase 3: Gradual Rollout (Week 3)

- Enable feature flag for 10% of requests
- Monitor metrics
- Increase to 50%, then 100%

### Phase 4: Cleanup (Week 4)

- Remove synchronous code path
- Remove feature flag
- Update documentation

## Testing Strategy

See `testing.md` for comprehensive testing approach.

## Alternatives Considered

### 1. AWS SQS + Lambda

- **Pros**: Serverless, auto-scaling
- **Cons**: Vendor lock-in, cold starts, complexity
- **Decision**: Celery chosen for simplicity and portability

### 2. RabbitMQ instead of Redis

- **Pros**: More features, better for complex routing
- **Cons**: More complex setup, higher resource usage
- **Decision**: Redis chosen for simplicity (already used for caching)

### 3. Synchronous with streaming response

- **Pros**: No infrastructure changes
- **Cons**: Still blocks connection, no retry logic
- **Decision**: Async chosen for better UX and scalability
