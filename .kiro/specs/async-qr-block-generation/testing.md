# Testing Strategy: Async QR Block Generation with Celery & Redis

## Overview

This document outlines the comprehensive testing strategy for the async QR block generation feature. It covers unit tests, integration tests, load tests, and end-to-end testing scenarios to ensure reliability, performance, and correctness.

## Testing Pyramid

```
                    ┌─────────────┐
                    │   E2E Tests │  (5%)
                    │   10 tests  │
                    └─────────────┘
                  ┌───────────────────┐
                  │ Integration Tests │  (20%)
                  │    40 tests       │
                  └───────────────────┘
              ┌─────────────────────────────┐
              │      Unit Tests             │  (75%)
              │       150 tests             │
              └─────────────────────────────┘
```

## Test Environment Setup

### Prerequisites

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov pytest-mock celery[redis] fakeredis

# Start test services
docker-compose -f docker-compose.test.yml up -d redis postgres

# Run migrations
alembic upgrade head
```

### Test Configuration

**File**: `tests/conftest.py`

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.celery_app import celery_app
from celery.contrib.testing import worker
```

@pytest.fixture(scope="session")
def test_db_engine():
"""Create test database engine."""
engine = create_engine("postgresql://test:test@localhost:5433/test_db")
Base.metadata.create_all(engine)
yield engine
Base.metadata.drop_all(engine)

@pytest.fixture
def db_session(test_db_engine):
"""Create test database session."""
Session = sessionmaker(bind=test_db_engine)
session = Session()
yield session
session.rollback()
session.close()

@pytest.fixture(scope="session")
def celery_config():
"""Celery test configuration."""
return {
'broker_url': 'redis://localhost:6379/1',
'result_backend': 'redis://localhost:6379/1',
'task_always_eager': False, # Run tasks asynchronously
}

@pytest.fixture
def celery_worker(celery_app, celery_config):
"""Start Celery worker for testing."""
with worker.start_worker(celery_app, perform_ping_check=False) as w:
yield w

````

---

## 1. Unit Tests

### 1.1 Task Unit Tests

**File**: `tests/tasks/test_qr_generation.py`

#### Test: Task Dispatch
```python
def test_generate_qr_block_task_dispatch(db_session, mocker):
    """Test that task is dispatched correctly."""
    from app.tasks.qr_generation import generate_qr_block_task

    # Mock task.delay to prevent actual execution
    mock_delay = mocker.patch.object(generate_qr_block_task, 'delay')
    mock_delay.return_value.id = "test-task-id"

    # Dispatch task
    task = generate_qr_block_task.delay(
        block_id="block-uuid",
        organization_id="org-uuid",
        user_id="user-uuid"
    )

    # Verify
    assert task.id == "test-task-id"
    mock_delay.assert_called_once()
````

#### Test: Task Execution Success

```python
def test_generate_qr_block_task_success(db_session, mocker):
    """Test successful task execution."""
    from app.tasks.qr_generation import generate_qr_block_task

    # Setup test data
    block = create_test_block(db_session, status="queued")
    product = create_test_product(db_session)

    # Mock dependencies
    mocker.patch('app.services.storage_service.upload_file')
    mocker.patch('app.services.storage_service.get_signed_url', return_value="https://gcs.example.com/file.xlsx")

    # Execute task
    result = generate_qr_block_task(
        block_id=str(block.id),
        organization_id=str(block.organization_id),
        user_id="user-uuid"
    )

    # Verify
    db_session.refresh(block)
    assert block.status == "completed"
    assert block.task_status == "success"
    assert block.download_url is not None
    assert result['status'] == 'completed'
```

#### Test: Task Retry on Transient Error

```python
def test_generate_qr_block_task_retry_on_db_error(db_session, mocker):
    """Test task retries on database connection error."""
    from app.tasks.qr_generation import generate_qr_block_task
    from sqlalchemy.exc import OperationalError

    block = create_test_block(db_session, status="queued")

    # Mock to raise OperationalError on first call, succeed on second
    mock_get_block = mocker.patch('app.repositories.qr_product_repository.QRBlockRepository.get_by_id')
    mock_get_block.side_effect = [
        OperationalError("Connection lost", None, None),
        block
    ]

    # Mock retry
    mock_retry = mocker.patch.object(generate_qr_block_task, 'retry')

    # Execute task
    try:
        generate_qr_block_task(
            block_id=str(block.id),
            organization_id=str(block.organization_id),
            user_id="user-uuid"
        )
    except OperationalError:
        pass

    # Verify retry was called
    assert mock_retry.called
```

#### Test: Task Failure After Max Retries

```python
def test_generate_qr_block_task_failure_after_max_retries(db_session, mocker):
    """Test task marks block as failed after max retries."""
    from app.tasks.qr_generation import generate_qr_block_task

    block = create_test_block(db_session, status="queued")

    # Mock to always fail
    mocker.patch('app.services.storage_service.upload_file', side_effect=Exception("GCS error"))

    # Mock retry to simulate max retries reached
    mock_task = mocker.MagicMock()
    mock_task.request.retries = 3
    mock_task.max_retries = 3

    # Execute task (should fail)
    with pytest.raises(Exception):
        generate_qr_block_task(
            block_id=str(block.id),
            organization_id=str(block.organization_id),
            user_id="user-uuid"
        )

    # Verify block marked as failed
    db_session.refresh(block)
    assert block.status == "failed"
    assert block.task_status == "failure"
    assert "GCS error" in block.error_message
```

#### Test: Progress Updates

```python
def test_generate_qr_block_task_progress_updates(db_session, mocker):
    """Test task updates progress during execution."""
    from app.tasks.qr_generation import generate_qr_block_task

    block = create_test_block(db_session, status="queued", quantity=5000)
    product = create_test_product(db_session)

    # Mock update_state
    mock_update_state = mocker.patch.object(generate_qr_block_task, 'update_state')

    # Execute task
    generate_qr_block_task(
        block_id=str(block.id),
        organization_id=str(block.organization_id),
        user_id="user-uuid"
    )

    # Verify progress updates were called
    assert mock_update_state.call_count >= 5  # At least 5 batches

    # Verify progress metadata
    calls = mock_update_state.call_args_list
    for call in calls:
        assert call[1]['state'] == 'PROGRESS'
        assert 'current' in call[1]['meta']
        assert 'total' in call[1]['meta']
        assert 'percent' in call[1]['meta']
```

### 1.2 Service Unit Tests

**File**: `tests/services/test_qr_product_service_async.py`

#### Test: Create Block Async

```python
def test_create_block_async(db_session, mocker):
    """Test async block creation."""
    from app.services.qr_product_service import QRProductService

    service = QRProductService(db_session)
    product = create_test_product(db_session)

    # Mock task dispatch
    mock_delay = mocker.patch('app.tasks.qr_generation.generate_qr_block_task.delay')
    mock_delay.return_value.id = "test-task-id"

    # Mock credit check
    mocker.patch.object(service.credit_service, 'check_balance')

    # Create block
    data = QRBlockCreate(batch="TEST-001", quantity=100)
    block = service.create_block_async(
        product_id=product.id,
        data=data,
        organization_id=product.organization_id,
        user_id="user-uuid"
    )

    # Verify
    assert block.status == "queued"
    assert block.task_status == "pending"
    assert block.task_id == "test-task-id"
    assert block.progress_total == 100
    assert block.progress_current == 0
    mock_delay.assert_called_once()
```

#### Test: Batch Generation

```python
def test_generate_product_items_batch(db_session):
    """Test batch item generation."""
    from app.services.qr_product_service import QRProductService

    service = QRProductService(db_session)
    block = create_test_block(db_session, quantity=1000)
    product = create_test_product(db_session)

    # Generate batch
    service._generate_product_items_batch(
        block=block,
        product=product,
        brand=None,
        private_key=None,
        organization_id=block.organization_id,
        user_id="user-uuid",
        start_index=0,
        count=100
    )

    # Verify items created
    items = db_session.query(ProductItem).filter_by(block_id=block.id).all()
    assert len(items) == 100
    assert all(item.serial_number for item in items)
```

#### Test: Credit Check Before Dispatch

```python
def test_create_block_async_insufficient_credits(db_session, mocker):
    """Test block creation fails with insufficient credits."""
    from app.services.qr_product_service import QRProductService
    from app.exceptions import InsufficientCreditsError

    service = QRProductService(db_session)
    product = create_test_product(db_session)

    # Mock credit check to raise error
    mocker.patch.object(
        service.credit_service,
        'check_balance',
        side_effect=InsufficientCreditsError("Insufficient credits")
    )

    # Attempt to create block
    data = QRBlockCreate(batch="TEST-001", quantity=10000)

    with pytest.raises(InsufficientCreditsError):
        service.create_block_async(
            product_id=product.id,
            data=data,
            organization_id=product.organization_id,
            user_id="user-uuid"
        )

    # Verify no block created
    blocks = db_session.query(QRBlock).all()
    assert len(blocks) == 0
```

### 1.3 Endpoint Unit Tests

**File**: `tests/api/test_qr_products_async.py`

#### Test: Block Creation Returns 202

```python
@pytest.mark.asyncio
async def test_create_block_returns_202(client, db_session, auth_headers, mocker):
    """Test block creation returns 202 Accepted."""
    product = create_test_product(db_session)

    # Mock task dispatch
    mocker.patch('app.tasks.qr_generation.generate_qr_block_task.delay')

    response = await client.post(
        f"/api/v1/qr-products/{product.id}/blocks",
        json={"batch": "TEST-001", "quantity": 100},
        headers=auth_headers
    )

    assert response.status_code == 202
    data = response.json()
    assert data['status'] == 'queued'
    assert data['task_id'] is not None
```

#### Test: Status Polling Endpoint

```python
@pytest.mark.asyncio
async def test_get_block_status(client, db_session, auth_headers, mocker):
    """Test status polling endpoint."""
    block = create_test_block(db_session, status="in_progress", task_id="test-task-id")

    # Mock Celery AsyncResult
    mock_result = mocker.MagicMock()
    mock_result.state = 'PROGRESS'
    mock_result.info = {'current': 500, 'total': 1000, 'percent': 50, 'status': 'Generating...'}
    mocker.patch('celery.result.AsyncResult', return_value=mock_result)

    response = await client.get(
        f"/api/v1/qr-products/blocks/{block.id}/status",
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'in_progress'
    assert data['task_state'] == 'PROGRESS'
    assert data['progress']['current'] == 500
    assert data['progress']['total'] == 1000
    assert data['progress']['percent'] == 50
```

---

## 2. Integration Tests

### 2.1 End-to-End Block Generation

**File**: `tests/integration/test_async_block_generation.py`

#### Test: Complete Async Flow

```python
@pytest.mark.integration
def test_complete_async_block_generation_flow(client, db_session, celery_worker, auth_headers):
    """Test complete async block generation flow."""
    # Setup
    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=10000)

    # 1. Create block
    response = client.post(
        f"/api/v1/qr-products/{product.id}/blocks",
        json={"batch": "TEST-001", "quantity": 500},
        headers=auth_headers
    )
    assert response.status_code == 202
    block_id = response.json()['id']
    task_id = response.json()['task_id']

    # 2. Poll status until completed
    max_polls = 30
    for _ in range(max_polls):
        response = client.get(
            f"/api/v1/qr-products/blocks/{block_id}/status",
            headers=auth_headers
        )
        data = response.json()

        if data['status'] == 'completed':
            break

        time.sleep(1)

    # 3. Verify completion
    assert data['status'] == 'completed'
    assert data['download_url'] is not None
    assert data['completed_at'] is not None

    # 4. Verify items created
    items = db_session.query(ProductItem).filter_by(block_id=block_id).all()
    assert len(items) == 500

    # 5. Verify credits deducted
    credits = get_credit_balance(db_session, product.organization_id)
    assert credits == 9500
```

#### Test: Concurrent Block Generation

```python
@pytest.mark.integration
def test_concurrent_block_generation(client, db_session, celery_worker, auth_headers):
    """Test multiple blocks can be generated concurrently."""
    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=50000)

    # Create 10 blocks concurrently
    block_ids = []
    for i in range(10):
        response = client.post(
            f"/api/v1/qr-products/{product.id}/blocks",
            json={"batch": f"TEST-{i:03d}", "quantity": 100},
            headers=auth_headers
        )
        assert response.status_code == 202
        block_ids.append(response.json()['id'])

    # Wait for all to complete
    completed = 0
    max_wait = 60
    start_time = time.time()

    while completed < 10 and (time.time() - start_time) < max_wait:
        completed = 0
        for block_id in block_ids:
            response = client.get(
                f"/api/v1/qr-products/blocks/{block_id}/status",
                headers=auth_headers
            )
            if response.json()['status'] == 'completed':
                completed += 1
        time.sleep(1)

    # Verify all completed
    assert completed == 10

    # Verify total items
    total_items = db_session.query(ProductItem).count()
    assert total_items == 1000
```

#### Test: Task Failure and Recovery

```python
@pytest.mark.integration
def test_task_failure_and_recovery(client, db_session, celery_worker, auth_headers, mocker):
    """Test task failure handling and recovery."""
    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=10000)

    # Mock GCS upload to fail first time, succeed second time
    upload_calls = [0]
    def mock_upload(path, data, content_type):
        upload_calls[0] += 1
        if upload_calls[0] == 1:
            raise Exception("GCS upload failed")

    mocker.patch('app.services.storage_service.upload_file', side_effect=mock_upload)

    # Create block
    response = client.post(
        f"/api/v1/qr-products/{product.id}/blocks",
        json={"batch": "TEST-001", "quantity": 100},
        headers=auth_headers
    )
    block_id = response.json()['id']

    # Wait for completion or failure
    max_polls = 30
    final_status = None
    for _ in range(max_polls):
        response = client.get(
            f"/api/v1/qr-products/blocks/{block_id}/status",
            headers=auth_headers
        )
        status = response.json()['status']
        if status in ['completed', 'failed']:
            final_status = status
            break
        time.sleep(1)

    # Verify task was retried and eventually succeeded
    assert final_status == 'completed'
    assert upload_calls[0] >= 2  # At least one retry
```

### 2.2 Feature Flag Tests

**File**: `tests/integration/test_feature_flag.py`

#### Test: Sync Path When Flag Disabled

```python
@pytest.mark.integration
def test_sync_path_when_flag_disabled(client, db_session, auth_headers, settings):
    """Test synchronous generation when feature flag is disabled."""
    # Disable async flag
    settings.enable_async_block_generation = False

    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=10000)

    # Create block
    response = client.post(
        f"/api/v1/qr-products/{product.id}/blocks",
        json={"batch": "TEST-001", "quantity": 100},
        headers=auth_headers
    )

    # Should return 201 (not 202) and be immediately completed
    assert response.status_code == 201
    data = response.json()
    assert data['status'] == 'completed'
    assert data['task_id'] is None
    assert data['download_url'] is not None
```

---

## 3. Load Tests

### 3.1 Performance Tests

**File**: `tests/load/test_block_generation_performance.py`

#### Test: Large Batch Performance

```python
@pytest.mark.load
def test_large_batch_performance(client, db_session, celery_worker, auth_headers):
    """Test performance with large batch (10,000 items)."""
    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=20000)

    # Create large block
    start_time = time.time()
    response = client.post(
        f"/api/v1/qr-products/{product.id}/blocks",
        json={"batch": "LARGE-001", "quantity": 10000},
        headers=auth_headers
    )
    api_response_time = time.time() - start_time

    # Verify API responds quickly
    assert api_response_time < 0.2  # <200ms
    assert response.status_code == 202

    block_id = response.json()['id']

    # Wait for completion
    start_time = time.time()
    completed = False
    max_wait = 300  # 5 minutes

    while not completed and (time.time() - start_time) < max_wait:
        response = client.get(
            f"/api/v1/qr-products/blocks/{block_id}/status",
            headers=auth_headers
        )
        if response.json()['status'] == 'completed':
            completed = True
            break
        time.sleep(2)

    execution_time = time.time() - start_time

    # Verify performance
    assert completed
    assert execution_time < 60  # Should complete in <60 seconds

    # Verify throughput
    items_per_second = 10000 / execution_time
    assert items_per_second > 150  # At least 150 items/second
```

#### Test: Concurrent Load

```python
@pytest.mark.load
def test_concurrent_load(client, db_session, celery_worker, auth_headers):
    """Test system under concurrent load."""
    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=100000)

    # Create 50 blocks concurrently
    import concurrent.futures

    def create_block(batch_num):
        response = client.post(
            f"/api/v1/qr-products/{product.id}/blocks",
            json={"batch": f"LOAD-{batch_num:03d}", "quantity": 500},
            headers=auth_headers
        )
        return response.status_code, response.json()

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(create_block, i) for i in range(50)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    creation_time = time.time() - start_time

    # Verify all created successfully
    assert all(status == 202 for status, _ in results)
    assert creation_time < 10  # All 50 blocks created in <10 seconds

    # Wait for all to complete
    block_ids = [data['id'] for _, data in results]
    completed = 0
    max_wait = 300
    start_time = time.time()

    while completed < 50 and (time.time() - start_time) < max_wait:
        completed = sum(
            1 for block_id in block_ids
            if client.get(f"/api/v1/qr-products/blocks/{block_id}/status", headers=auth_headers).json()['status'] == 'completed'
        )
        time.sleep(5)

    total_time = time.time() - start_time

    # Verify all completed
    assert completed == 50
    assert total_time < 300  # All complete in <5 minutes
```

#### Test: Memory Usage

```python
@pytest.mark.load
def test_memory_usage(client, db_session, celery_worker, auth_headers):
    """Test memory usage during large batch generation."""
    import psutil
    import os

    product = create_test_product(db_session)
    setup_test_credits(db_session, product.organization_id, credits=20000)

    # Get initial memory
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Create large block
    response = client.post(
        f"/api/v1/qr-products/{product.id}/blocks",
        json={"batch": "MEMORY-001", "quantity": 10000},
        headers=auth_headers
    )
    block_id = response.json()['id']

    # Wait for completion
    while True:
        response = client.get(
            f"/api/v1/qr-products/blocks/{block_id}/status",
            headers=auth_headers
        )
        if response.json()['status'] == 'completed':
            break
        time.sleep(2)

    # Check final memory
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = final_memory - initial_memory

    # Verify no memory leak (increase should be <100MB)
    assert memory_increase < 100
```

---

## 4. Property-Based Tests

### 4.1 Serial Number Generation

**File**: `tests/property/test_serial_generation.py`

```python
from hypothesis import given, strategies as st

@given(
    quantity=st.integers(min_value=1, max_value=10000),
    sr_type=st.sampled_from(['R6DAN', 'R4DAN', 'S8DN', 'S10DN'])
)
def test_serial_numbers_are_unique(quantity, sr_type):
    """Property: All generated serial numbers must be unique."""
    from app.services.qr_product_service import QRProductService

    service = QRProductService(None)
    serial_gen = service._get_serial_generator(sr_type)

    serials = [serial_gen() for _ in range(quantity)]

    # Property: All serials are unique
    assert len(serials) == len(set(serials))

@given(
    prefix=st.text(min_size=0, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
    quantity=st.integers(min_value=1, max_value=1000)
)
def test_serial_numbers_have_correct_prefix(prefix, quantity):
    """Property: All serial numbers must start with the specified prefix."""
    from app.services.qr_product_service import QRProductService

    service = QRProductService(None)
    serial_gen = service._get_serial_generator('S8DN')

    serials = [f"{prefix}{serial_gen()}" for _ in range(quantity)]

    # Property: All serials start with prefix
    assert all(s.startswith(prefix) for s in serials)
```

### 4.2 QR Signing

```python
@given(
    serial=st.text(min_size=1, max_size=75),
    timestamp=st.integers(min_value=1000000000, max_value=9999999999)
)
def test_qr_signature_is_deterministic(serial, timestamp):
    """Property: Same input produces same signature."""
    from app.services.key_service import KeyService

    key_service = KeyService()
    private_key = key_service.generate_key_pair()[1]

    # Sign twice with same inputs
    sig1, _ = sign_qr_item(key_service, private_key, serial, timestamp)
    sig2, _ = sign_qr_item(key_service, private_key, serial, timestamp)

    # Property: Signatures are identical
    assert sig1 == sig2
```

---

## 5. Test Data Factories

**File**: `tests/factories.py`

```python
import factory
from app.models import QRBlock, QRProduct, Organization, ProductItem

class OrganizationFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Organization
        sqlalchemy_session_persistence = "commit"

    id = factory.Faker('uuid4')
    name = factory.Faker('company')
    short_code = factory.Sequence(lambda n: f"ORG{n:04d}")

class QRProductFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = QRProduct
        sqlalchemy_session_persistence = "commit"

    id = factory.Faker('uuid4')
    organization_id = factory.SubFactory(OrganizationFactory)
    name = factory.Faker('word')
    gtin = factory.Sequence(lambda n: f"{n:013d}")

class QRBlockFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = QRBlock
        sqlalchemy_session_persistence = "commit"

    id = factory.Faker('uuid4')
    organization_id = factory.SubFactory(OrganizationFactory)
    product_id = factory.SubFactory(QRProductFactory)
    batch = factory.Sequence(lambda n: f"BATCH-{n:04d}")
    quantity = 100
    status = "queued"
    task_status = "pending"

class ProductItemFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = ProductItem
        sqlalchemy_session_persistence = "commit"

    id = factory.Faker('uuid4')
    organization_id = factory.SubFactory(OrganizationFactory)
    product_id = factory.SubFactory(QRProductFactory)
    block_id = factory.SubFactory(QRBlockFactory)
    serial_number = factory.Sequence(lambda n: f"SN-{n:08d}")
```

---

## 6. Test Coverage Requirements

### Coverage Targets

| Component           | Target Coverage | Critical Paths |
| ------------------- | --------------- | -------------- |
| Task Implementation | 95%             | 100%           |
| Service Layer       | 90%             | 100%           |
| API Endpoints       | 85%             | 100%           |
| Repository Layer    | 80%             | N/A            |
| Utility Functions   | 90%             | N/A            |
| **Overall**         | **85%**         | **100%**       |

### Running Coverage

```bash
# Run tests with coverage
pytest --cov=app --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html

# Fail if coverage below threshold
pytest --cov=app --cov-fail-under=85
```

---

## 7. CI/CD Integration

### GitHub Actions Workflow

**File**: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run migrations
        run: alembic upgrade head
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db

      - name: Run unit tests
        run: pytest tests/unit -v --cov=app --cov-report=xml
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/1

      - name: Run integration tests
        run: pytest tests/integration -v
        env:
          DATABASE_URL: postgresql://test:test@localhost:5432/test_db
          REDIS_URL: redis://localhost:6379/1

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## 8. Test Execution Plan

### Local Development

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/tasks/test_qr_generation.py

# Run with specific marker
pytest -m integration

# Run with verbose output
pytest -v -s

# Run with coverage
pytest --cov=app --cov-report=html
```

### Pre-Commit Checks

```bash
# Run fast tests only
pytest -m "not integration and not load"

# Run linting
ruff check app/
black --check app/

# Run type checking
mypy app/
```

### CI Pipeline

1. **Unit Tests** (fast, run on every commit)
2. **Integration Tests** (slower, run on PR)
3. **Load Tests** (slowest, run nightly or on release)

---

## 9. Test Maintenance

### Adding New Tests

1. Create test file in appropriate directory
2. Use factories for test data
3. Mock external dependencies
4. Add docstring explaining what is tested
5. Use descriptive test names
6. Add appropriate markers (`@pytest.mark.integration`, etc.)

### Updating Tests

1. Update tests when requirements change
2. Keep tests in sync with implementation
3. Remove obsolete tests
4. Refactor duplicated test code into fixtures

### Test Review Checklist

- [ ] Test covers happy path
- [ ] Test covers error cases
- [ ] Test is deterministic (no flaky tests)
- [ ] Test uses appropriate fixtures
- [ ] Test has clear assertions
- [ ] Test runs in reasonable time
- [ ] Test is properly marked
- [ ] Test has descriptive name and docstring

---

## 10. Success Metrics

### Test Quality Metrics

- **Test Coverage**: ≥85% overall, 100% for critical paths
- **Test Execution Time**: <5 minutes for unit tests, <15 minutes for all tests
- **Test Reliability**: <1% flaky test rate
- **Test Maintainability**: <10% of development time spent on test maintenance

### Performance Benchmarks

- API response time: <200ms (p95)
- Task execution time: <30s for 5000 items (p95)
- Concurrent throughput: ≥100 blocks/minute
- Memory usage: <500MB per worker

---

## Appendix: Test Commands Reference

```bash
# Run all tests
pytest

# Run with markers
pytest -m unit
pytest -m integration
pytest -m load
pytest -m "not load"

# Run specific test
pytest tests/tasks/test_qr_generation.py::test_generate_qr_block_task_success

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run with verbose output
pytest -v -s

# Run in parallel
pytest -n auto

# Run with specific log level
pytest --log-cli-level=DEBUG

# Stop on first failure
pytest -x

# Run last failed tests
pytest --lf

# Generate JUnit XML report
pytest --junitxml=test-results.xml
```
