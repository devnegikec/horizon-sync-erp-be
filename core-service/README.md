# Core Service

Core Service is a microservice handling **Inventory**, **Order**, and **Billing** management for the Horizon Sync ERP system.

## Features

### Current (v1.0.0)

- **Inventory Management**
  - Items CRUD (Create, Read, Update, Delete)
  - Item Groups categorization
  - Warehouses management
  - Stock settings (batch, serial numbers)
  - Reorder level tracking

### Planned

- Stock movements and entries
- Purchase receipts
- Delivery notes
- Invoicing
- Payment processing

## API Endpoints

### Items

| Method | Endpoint             | Description         |
| ------ | -------------------- | ------------------- |
| POST   | `/api/v1/items`      | Create a new item   |
| GET    | `/api/v1/items`      | List items          |
| GET    | `/api/v1/items/{id}` | Get item by ID      |
| PUT    | `/api/v1/items/{id}` | Update an item      |
| DELETE | `/api/v1/items/{id}` | Soft delete an item |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Identity Service running (for authentication and shared database)

### Running the Service

1. **Ensure Identity Service is running first:**

   ```bash
   cd ../identity-service
   docker compose up -d
   ```

2. **Start Core Service:**

   ```bash
   cd core-service
   cp .env.example .env
   docker compose up -d
   ```

3. **Access the API:**
   - API: http://localhost:8001
   - Swagger UI: http://localhost:8001/docs
   - ReDoc: http://localhost:8001/redoc

### Authentication

All endpoints require authentication. Get a token from Identity Service:

```bash
# Login to get token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!"}'

# Use the access_token in Core Service requests
curl http://localhost:8001/api/v1/items \
  -H "Authorization: Bearer <access_token>"
```

## Development

### Project Structure

```
core-service/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── items.py
│   │       └── router.py
│   ├── core/
│   │   ├── exceptions.py
│   │   └── security.py
│   ├── models/
│   │   ├── base.py
│   │   ├── item.py
│   │   ├── item_group.py
│   │   └── warehouse.py
│   ├── repositories/
│   │   └── item_repository.py
│   ├── schemas/
│   │   ├── common.py
│   │   └── item.py
│   ├── services/
│   │   └── item_service.py
│   ├── config.py
│   ├── database.py
│   ├── dependencies.py
│   └── main.py
├── alembic/
├── scripts/
│   └── seed_data.py
├── tests/
│   ├── conftest.py
│   ├── test_health.py
│   └── test_items.py
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

### Running Tests

```bash
# Inside container
docker compose exec api pytest

# With coverage
docker compose exec api pytest --cov=app --cov-report=html
```

### Linting

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Configuration

### Environment Variables

| Variable               | Description                              | Default                  |
| ---------------------- | ---------------------------------------- | ------------------------ |
| `DATABASE_URL`         | PostgreSQL connection string             | Required                 |
| `SECRET_KEY`           | JWT secret (must match identity-service) | Required                 |
| `IDENTITY_SERVICE_URL` | URL of identity service                  | http://identity_api:8000 |
| `DEBUG`                | Enable debug mode                        | false                    |
| `CORS_ORIGINS`         | Allowed CORS origins                     | http://localhost:3000    |

## Architecture

Core Service shares the database with Identity Service and validates JWT tokens using the same secret key. For complex permission checks, it can call the Identity Service API.

```
┌─────────────┐     ┌─────────────┐
│   Client    │────▶│   Gateway   │
└─────────────┘     └─────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│   Identity    │ │     Core      │ │    Other      │
│   Service     │ │   Service     │ │   Services    │
│   (Auth)      │ │  (Inventory)  │ │   (Future)    │
└───────────────┘ └───────────────┘ └───────────────┘
        │                 │                 │
        └────────────────┬┼─────────────────┘
                         ▼
                  ┌─────────────┐
                  │  PostgreSQL │
                  │  (Shared)   │
                  └─────────────┘
```

## License

Proprietary - Horizon Sync
