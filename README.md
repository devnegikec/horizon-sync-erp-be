# Horizon Sync Backend

A microservices-based ERP system built with FastAPI and PostgreSQL.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        Clients                               │
│              (Web App, Mobile App, API Consumers)            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway (Future)                     │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐     ┌───────────────┐     ┌───────────────┐
│   Identity    │     │     Core      │     │    Future     │
│   Service     │     │   Service     │     │   Services    │
│   :8000       │     │   :8001       │     │               │
├───────────────┤     ├───────────────┤     ├───────────────┤
│ • Auth        │     │ • Inventory   │     │ • Reporting   │
│ • Users       │     │ • Orders      │     │ • Analytics   │
│ • Roles       │     │ • Billing     │     │ • Notifications│
│ • Permissions │     │ • Warehouses  │     │               │
└───────────────┘     └───────────────┘     └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              ▼
                    ┌───────────────┐
                    │  PostgreSQL   │
                    │   (Shared)    │
                    │   :5432       │
                    └───────────────┘
```

## Project Structure

```
horizon-sync-be/
├── docker-compose.yml          # 🐳 Main orchestration (run this!)
├── .env.example                # Environment variables template
├── Makefile                    # Helpful commands
├── schema.dbml                 # Database schema documentation
│
├── identity-service/           # Authentication & User Management
│   ├── app/
│   │   ├── api/v1/endpoints/   # Auth, Users endpoints
│   │   ├── models/             # User, Role, Organization models
│   │   ├── services/           # Business logic
│   │   └── repositories/       # Database operations
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Unit tests
│   └── Dockerfile
│
├── core-service/               # Inventory, Orders, Billing
│   ├── app/
│   │   ├── api/v1/endpoints/   # Items, Warehouses endpoints
│   │   ├── models/             # Item, ItemGroup, Warehouse models
│   │   ├── services/           # Business logic
│   │   └── repositories/       # Database operations
│   ├── alembic/                # Database migrations
│   ├── tests/                  # Unit tests
│   └── Dockerfile
│
└── (future services...)
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Make (optional, for convenience commands)

### 1. Setup Environment

```bash
# Clone and enter the project
cd horizon-sync-be

# Copy environment file
cp .env.example .env

# Install dev tools and pre-commit hooks (optional but recommended)
make install
```

### 2. Start All Services

```bash
# Using Make (recommended)
make up

# Or using Docker Compose directly
docker compose up -d
```

### 3. Access the APIs

| Service          | URL                           | Description                |
| ---------------- | ----------------------------- | -------------------------- |
| Identity Service | http://localhost:8000         | Auth & User Management     |
| Identity Docs    | http://localhost:8000/docs    | Swagger UI                 |
| Core Service     | http://localhost:8001         | Inventory & Orders         |
| Core Docs        | http://localhost:8001/docs    | Swagger UI                 |
| PostgreSQL       | localhost:5432                | Database                   |

### 4. Test the APIs

```bash
# Check health
curl http://localhost:8000/health
curl http://localhost:8001/health

# Login (Identity Service)
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "Admin123!"}'

# Use the token for Core Service
curl http://localhost:8001/api/v1/items \
  -H "Authorization: Bearer <your_access_token>"
```

## Common Commands

```bash
# Setup
make install              # Install pre-commit hooks & dev dependencies

# Docker
make up                   # Start all services
make down                 # Stop all services
make logs                 # View all logs
make logs-identity        # View Identity Service logs
make logs-core            # View Core Service logs
make build                # Rebuild all services
make clean                # Stop and remove volumes

# Testing
make test                 # Run all tests (Docker)
make test-local           # Run all tests (local Python)
make test-identity        # Run Identity Service tests
make test-core            # Run Core Service tests
make test-cov             # Run tests with coverage

# Linting
make lint                 # Run pre-commit on all files
make lint-fix             # Run ruff with auto-fix
make format               # Format all Python code

# Database
make migrate              # Run all migrations
make seed                 # Re-seed all data

# Shell Access
make shell-identity       # Bash into Identity container
make shell-core           # Bash into Core container
make db-shell             # PostgreSQL shell

# Health Check
make health               # Check all service health
```

## Default Test Credentials

After seeding, these accounts are available:

| Role         | Email                  | Password   |
| ------------ | ---------------------- | ---------- |
| System Admin | admin@example.com      | Admin123!  |
| Regular User | john.doe@example.com   | User123!   |
| Regular User | jane.smith@example.com | User123!   |

## Development

### Adding a New Service

1. Create a new folder: `new-service/`
2. Copy structure from `core-service/`
3. Update `docker-compose.yml` to add the service
4. Update `Makefile` with new commands

### Running a Service Standalone

Each service has a `docker-compose.standalone.yml` for isolated development:

```bash
# Identity service standalone
cd identity-service
docker compose -f docker-compose.standalone.yml up -d

# Core service standalone (requires identity-service running)
cd core-service
docker compose -f docker-compose.standalone.yml up -d
```

### Pre-commit Hooks

Pre-commit runs automatically on `git commit` and `git push`:

```bash
# Install hooks (done automatically with make install)
pre-commit install
pre-commit install --hook-type pre-push

# Run manually on all files
make lint

# Run with auto-fix
make lint-fix
```

### Database Migrations

```bash
# Create new migration (inside container)
make shell-identity
python -m alembic revision --autogenerate -m "description"

# Apply migrations
make migrate
```

## API Documentation

- **Identity Service**: http://localhost:8000/docs (Swagger) or http://localhost:8000/redoc (ReDoc)
- **Core Service**: http://localhost:8001/docs (Swagger) or http://localhost:8001/redoc (ReDoc)

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:

| Variable      | Description                          | Default       |
| ------------- | ------------------------------------ | ------------- |
| `SECRET_KEY`  | JWT signing key (must match across services) | Required |
| `DB_USER`     | PostgreSQL username                  | horizon_user  |
| `DB_PASSWORD` | PostgreSQL password                  | horizon_pass  |
| `DB_NAME`     | PostgreSQL database name             | horizon_db    |
| `DEBUG`       | Enable debug mode                    | false         |

## License

Proprietary - Horizon Sync
