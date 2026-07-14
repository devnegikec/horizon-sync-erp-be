# Search Service

Unified Search API for ERP System - provides comprehensive search functionality across all entities with support for both global and local search.

## Features

- **Global Search**: Search across all entity types (items, customers, suppliers, warehouses, stock entries)
- **Local Search**: Search within specific entity types with field-specific filtering
- **Real-time Sync**: Event-driven architecture for instant search index updates
- **High Performance**: PostgreSQL full-text search with Redis caching
- **Security**: JWT-based authentication with role-based access control
- **Scalability**: Designed to handle 100,000+ records with <500ms response times
- **Analytics**: Comprehensive search query logging and performance monitoring

## Architecture

The service follows a layered architecture with event-driven sync:

- **API Layer**: FastAPI endpoints for search operations
- **Service Layer**: Business logic and authorization
- **Search Engine Layer**: PostgreSQL full-text search implementation
- **Data Layer**: Entity persistence and search indexing
- **Cache Layer**: Redis for query result caching
- **Event Worker**: Real-time event consumer for instant index updates

## Requirements

- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- Identity Service (for authentication)
- Core Service (for entity data)

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Run database migrations:
```bash
alembic upgrade head
```

4. Start the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Real-Time Search Sync

The service uses an **event-driven architecture** for real-time search index updates:

### How It Works

1. **Event Publishing** (Core Service):
   - When entities are created/updated/deleted in core-service
   - Events are published to Redis Stream (`search:events`)
   - Events contain full entity data for indexing

2. **Event Consumption** (Search Service):
   - Background worker consumes events from Redis Stream
   - Processes events in real-time (typically <100ms)
   - Updates search documents table immediately

3. **Fallback Sync**:
   - Periodic sync runs every hour as backup
   - Catches any missed events
   - Ensures data consistency

### Event Flow

```
Create Item → DB Commit → Publish Event → Redis Stream
                                              ↓
                               Event Consumer (Search Service)
                                              ↓
                               Update SearchDocument
                                              ↓
                          Item appears in search immediately!
```

### Configuration

Event sync settings:
- `REDIS_URL`: Redis connection for event stream
- `REDIS_STREAM_NAME`: Stream name (default: `search:events`)
- `SYNC_SERVICE_USERNAME`: Service account for fallback sync
- `SYNC_SERVICE_PASSWORD`: Service account password

### Monitoring

Check event consumer logs:
```bash
docker logs horizon_search | grep "event_consumer"
```

Common log messages:
- `"Starting event consumer for stream 'search:events'"` - Consumer started
- `"Processing entity.created for items:..."` - Event being processed
- `"Upserted search document for items:..."` - Index updated
- `"Periodic fallback sync completed"` - Hourly backup sync finished

## API Documentation

Once the service is running, visit:
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

## Configuration

Key environment variables:

- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SECRET_KEY`: JWT secret key (must match identity-service)
- `IDENTITY_SERVICE_URL`: URL of identity service
- `CORE_SERVICE_URL`: URL of core service
- `SEARCH_MAX_RESULTS`: Maximum results per query (default: 1000)
- `SEARCH_DEFAULT_PAGE_SIZE`: Default page size (default: 20)

## Project Structure

```
search-service/
├── alembic/              # Database migrations
├── app/
│   ├── api/              # API endpoints
│   ├── models/           # Data models
│   ├── services/         # Business logic & sync service
│   ├── workers/          # Background event consumer
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   ├── dependencies.py   # FastAPI dependencies
│   ├── logging_config.py # Logging configuration
│   ├── main.py           # FastAPI application
│   ├── query_parser.py   # Search query parser
│   ├── search_engine.py  # Full-text search engine
│   └── security.py       # JWT handling
├── tests/                # Test suite
├── .env.example          # Example environment variables
├── alembic.ini           # Alembic configuration
├── pytest.ini            # Pytest configuration
├── pyproject.toml        # Project metadata
└── requirements.txt      # Python dependencies
```

## License

Proprietary - Internal ERP System
