# Search Service

Unified Search API for ERP System - provides comprehensive search functionality across all entities with support for both global and local search.

## Features

- **Global Search**: Search across all entity types (items, customers, suppliers, warehouses, stock entries)
- **Local Search**: Search within specific entity types with field-specific filtering
- **High Performance**: PostgreSQL full-text search with Redis caching
- **Security**: JWT-based authentication with role-based access control
- **Scalability**: Designed to handle 100,000+ records with <500ms response times
- **Analytics**: Comprehensive search query logging and performance monitoring

## Architecture

The service follows a layered architecture:

- **API Layer**: FastAPI endpoints for search operations
- **Service Layer**: Business logic and authorization
- **Search Engine Layer**: PostgreSQL full-text search implementation
- **Data Layer**: Entity persistence and search indexing
- **Cache Layer**: Redis for query result caching

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
│   ├── api/              # API endpoints (future)
│   ├── models/           # Data models
│   ├── services/         # Business logic (future)
│   ├── config.py         # Configuration
│   ├── database.py       # Database setup
│   ├── dependencies.py   # FastAPI dependencies
│   ├── logging_config.py # Logging configuration
│   ├── main.py           # FastAPI application
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
