# Identity Service - FastAPI Microservice

A production-ready authentication and user management microservice built with FastAPI, SQLAlchemy, PostgreSQL, and Docker.

## Features

- ✅ User registration with email validation
- ✅ JWT-based authentication (access + refresh tokens)
- ✅ Account locking after failed login attempts
- ✅ Role-Based Access Control (RBAC)
- ✅ Multi-tenancy with organizations
- ✅ PostgreSQL database with Alembic migrations
- ✅ Docker containerization
- ✅ OpenAPI/Swagger documentation
- ✅ Comprehensive error handling

## Tech Stack

- **Framework:** FastAPI 0.104+
- **Database:** PostgreSQL 15+
- **ORM:** SQLAlchemy 2.0+
- **Migrations:** Alembic
- **Authentication:** JWT (PyJWT)
- **Password Hashing:** Passlib with bcrypt
- **Validation:** Pydantic v2
- **Server:** Uvicorn
- **Containerization:** Docker & Docker Compose

## Project Structure

```
identity-service/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Security, exceptions
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # Data access layer
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── config.py        # Configuration
│   ├── database.py      # Database setup
│   └── main.py          # FastAPI app
├── alembic/             # Database migrations
├── scripts/             # Utility scripts
├── tests/               # Test suite
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)

### Using Docker (Recommended)

1. Clone the repository
2. Copy environment file:

   ```bash
   cp .env.example .env
   ```

3. Update `.env` with your configuration (especially `SECRET_KEY`)

4. Start the services:

   ```bash
   docker-compose up --build
   ```

5. Access the API:
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### Local Development

1. Create virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up PostgreSQL database and update `.env`

4. Run migrations:

   ```bash
   alembic upgrade head
   ```

5. Seed database:

   ```bash
   python scripts/seed_data.py
   ```

6. Start the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Endpoints

### Authentication

- `POST /api/v1/identity/register` - Register new user
- `POST /api/v1/identity/login` - User login
- `POST /api/v1/identity/refresh` - Refresh access token
- `POST /api/v1/identity/logout` - User logout

### Users

- `GET /api/v1/identity/users` - List users (paginated, requires auth)

### System

- `GET /health` - Health check endpoint

## Test Credentials

After running seed data, you can use these credentials:

| Email                  | Password  | Role         |
| ---------------------- | --------- | ------------ |
| admin@example.com      | Admin123! | System Admin |
| john.doe@example.com   | User123!  | User         |
| jane.smith@example.com | User123!  | User         |

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:

- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT secret key (min 32 characters)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Access token expiration (default: 15)
- `REFRESH_TOKEN_EXPIRE_DAYS` - Refresh token expiration (default: 7)

## Database Migrations

Create a new migration:

```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:

```bash
alembic upgrade head
```

Rollback migration:

```bash
alembic downgrade -1
```

## Testing

Run tests:

```bash
pytest
```

Run with coverage:

```bash
pytest --cov=app tests/
```

## Security Features

- **Password Hashing:** Bcrypt with 12 rounds
- **JWT Tokens:** HS256 algorithm
- **Access Tokens:** 15-minute expiration
- **Refresh Tokens:** 7-day expiration, stored in database
- **Account Locking:** 5 failed attempts = 30-minute lock
- **Device Tracking:** Refresh tokens tied to devices
- **Input Validation:** Pydantic schemas for all inputs

## API Documentation

Interactive API documentation is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

MIT License

## Support

For issues and questions, please open an issue on GitHub.

Test
