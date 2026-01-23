# Identity Microservice - Design Document

## 1. Architecture Overview

### 1.1 System Architecture

```
┌─────────────────┐
│   API Gateway   │ (Future)
└────────┬────────┘
         │
┌────────▼────────────────────────────────────┐
│     Identity Service (FastAPI)              │
│  ┌──────────────────────────────────────┐  │
│  │  API Layer (Routes/Controllers)      │  │
│  └──────────────┬───────────────────────┘  │
│  ┌──────────────▼───────────────────────┐  │
│  │  Business Logic Layer (Services)     │  │
│  └──────────────┬───────────────────────┘  │
│  ┌──────────────▼───────────────────────┐  │
│  │  Data Access Layer (Repositories)    │  │
│  └──────────────┬───────────────────────┘  │
└─────────────────┼───────────────────────────┘
                  │
         ┌────────▼────────┐
         │   PostgreSQL    │
         │    Database     │
         └─────────────────┘
```

### 1.2 Project Structure

```
identity-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection
│   ├── dependencies.py         # Dependency injection
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py       # Main API router
│   │       └── endpoints/
│   │           ├── __init__.py
│   │           ├── auth.py     # Auth endpoints
│   │           └── users.py    # User endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py         # JWT, password hashing
│   │   └── exceptions.py       # Custom exceptions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── organization.py
│   │   ├── role.py
│   │   └── token.py
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── auth.py
│   │   └── token.py
│   │
│   ├── services/
│   │   ├── __init__.py
```

│ │ ├── auth_service.py
│ │ └── user_service.py
│ │
│ └── repositories/
│ ├── **init**.py
│ ├── user_repository.py
│ └── token_repository.py
│
├── alembic/ # Database migrations
│ ├── versions/
│ └── env.py
│
├── scripts/
│ └── seed_data.py # Database seeding
│
├── tests/
│ ├── **init**.py
│ ├── conftest.py
│ └── test_auth.py
│
├── .env.example
├── .dockerignore
├── .gitignore
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md

```

## 2. Database Design

### 2.1 PostgreSQL Enums
```

```sql
CREATE TYPE usertype AS ENUM ('system_admin', 'organization_admin', 'user', 'guest');
CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'suspended', 'pending');
CREATE TYPE organizationtype AS ENUM ('enterprise', 'business', 'startup', 'individual');
CREATE TYPE organizationstatus AS ENUM ('active', 'inactive', 'suspended', 'trial');
CREATE TYPE teamrole AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE teamtype AS ENUM ('department', 'project', 'functional', 'cross_functional');
CREATE TYPE resourcetype AS ENUM ('user', 'organization', 'team', 'role', 'permission');
CREATE TYPE actiontype AS ENUM ('create', 'read', 'update', 'delete', 'manage', 'execute');
```

### 2.2 Core Tables (SQLAlchemy Models)

#### 2.2.1 Users Table

```python
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    display_name = Column(String(200))
    phone = Column(String(20))
    avatar_url = Column(String(500))
    user_type = Column(Enum(UserType), default=UserType.USER, nullable=False)
    status = Column(Enum(UserStatus), default=UserStatus.PENDING, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_verified_at = Column(DateTime(timezone=True))
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255))
    mfa_backup_codes = Column(JSONB)
    last_login_at = Column(DateTime(timezone=True))
    last_login_ip = Column(String(45))
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True))
    preferences = Column(JSONB, default={})
    timezone = Column(String(50), default='UTC')
    language = Column(String(10), default='en')
    extra_data = Column(JSONB, default={})
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2.2.2 Refresh Tokens Table

```python
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    token_family = Column(String(255), index=True)
    device_id = Column(String(255))
    device_name = Column(String(255))
    device_type = Column(String(50))
    os_info = Column(String(100))
    browser_info = Column(String(100))
    ip_address = Column(String(45))
    user_agent = Column(Text)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True))
    revoked_reason = Column(String(100))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="refresh_tokens")
```

#### 2.2.3 Organizations Table

```python
class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    description = Column(Text)
    email = Column(String(255))
    phone = Column(String(20))
    website = Column(String(255))
    organization_type = Column(Enum(OrganizationType), default=OrganizationType.BUSINESS)
    status = Column(Enum(OrganizationStatus), default=OrganizationStatus.ACTIVE)
    is_active = Column(Boolean, default=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    settings = Column(JSONB, default={})
    extra_data = Column(JSONB, default={})
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2.2.4 Roles Table

```python
class Role(Base):
    __tablename__ = "roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'))
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False)
    description = Column(Text)
    is_system = Column(Boolean, default=False)
    is_default = Column(Boolean, default=False)
    hierarchy_level = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2.2.5 Permissions Table

```python
class Permission(Base):
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    resource = Column(Enum(ResourceType), nullable=False)
    action = Column(Enum(ActionType), nullable=False)
    module = Column(String(50))
    category = Column(String(50))
    is_active = Column(Boolean, default=True)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2.2.6 Role Permissions Table

```python
class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    permission_id = Column(UUID(as_uuid=True), ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False)
    conditions = Column(JSONB, default={})
```

#### 2.2.7 User Organization Roles Table

```python
class UserOrganizationRole(Base):
    __tablename__ = "user_organization_roles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id', ondelete='CASCADE'), nullable=False)
    is_primary = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default='active')
    invited_by_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))
    invited_at = Column(DateTime(timezone=True))
    joined_at = Column(DateTime(timezone=True))
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
```

#### 2.2.8 Email Verifications Table

```python
class EmailVerification(Base):
    __tablename__ = "email_verifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    email = Column(String(255), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    verified_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
```

## 3. API Design

### 3.1 Authentication Flow

```
Registration Flow:
1. POST /api/v1/identity/register
2. Validate input (email, password strength)
3. Check email uniqueness
4. Hash password with bcrypt
5. Create user record (status: pending)
6. Create email verification token
7. Log verification token (mock email)
8. Return access + refresh tokens

Login Flow:
1. POST /api/v1/identity/login
2. Find user by email
3. Check account lock status
4. Verify password
5. Update failed_login_attempts
6. Generate access + refresh tokens
7. Store refresh token with device info
8. Update last_login_at, last_login_ip
9. Return tokens

Token Refresh Flow:
1. POST /api/v1/identity/refresh
2. Validate refresh token format
3. Check token in database
4. Verify not expired/revoked
5. Generate new access token
6. Update last_used_at
7. Return new access token

Logout Flow:
1. POST /api/v1/identity/logout
2. Extract refresh token from request
3. Mark token as revoked
4. Set revoked_at timestamp
5. Return success
```

### 3.2 API Endpoints Specification

#### 3.2.1 POST /api/v1/identity/register

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "first_name": "John",
  "last_name": "Doe",
  "phone": "+1234567890"
}
```

**Validation Rules:**

- email: valid email format, max 255 chars
- password: min 8 chars, must contain uppercase, lowercase, number, special char
- first_name: required, 2-100 chars
- last_name: required, 2-100 chars
- phone: optional, valid phone format

**Success Response (201):**

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe",
    "user_type": "user",
    "status": "pending",
    "email_verified": false,
    "created_at": "2024-01-23T10:00:00Z"
  },
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Responses:**

- 400: Validation error (weak password, invalid email)
- 409: Email already exists
- 500: Internal server error

#### 3.2.2 POST /api/v1/identity/login

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "device_info": {
    "device_name": "Chrome on MacOS",
    "device_type": "browser",
    "os_info": "MacOS 14.0",
    "browser_info": "Chrome 120"
  }
}
```

**Success Response (200):**

```json
{
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "display_name": "John Doe",
    "user_type": "user",
    "status": "active",
    "email_verified": true,
    "last_login_at": "2024-01-23T10:00:00Z"
  },
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Responses:**

- 400: Invalid credentials
- 401: Invalid email or password
- 403: Account locked (too many failed attempts)
- 403: Account suspended/inactive
- 500: Internal server error

#### 3.2.3 POST /api/v1/identity/refresh

**Request Body:**

```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Success Response (200):**

```json
{
  "access_token": "eyJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

**Error Responses:**

- 400: Missing refresh token
- 401: Invalid or expired refresh token
- 401: Token has been revoked
- 500: Internal server error

#### 3.2.4 POST /api/v1/identity/logout

**Headers:**

```
Authorization: Bearer <access_token>
```

**Request Body:**

```json
{
  "refresh_token": "eyJhbGc..."
}
```

**Success Response (200):**

```json
{
  "message": "Successfully logged out"
}
```

**Error Responses:**

- 400: Missing refresh token
- 401: Unauthorized (invalid access token)
- 404: Refresh token not found
- 500: Internal server error

#### 3.2.5 GET /api/v1/identity/users

**Headers:**

```
Authorization: Bearer <access_token>
```

**Query Parameters:**

- page: integer (default: 1)
- page_size: integer (default: 20, max: 100)
- status: string (active, inactive, suspended, pending)
- user_type: string (system_admin, organization_admin, user)
- email_verified: boolean
- search: string (searches email, first_name, last_name)
- sort_by: string (created_at, email, last_login_at)
- sort_order: string (asc, desc)

**Success Response (200):**

```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "first_name": "John",
      "last_name": "Doe",
      "display_name": "John Doe",
      "user_type": "user",
      "status": "active",
      "email_verified": true,
      "last_login_at": "2024-01-23T10:00:00Z",
      "created_at": "2024-01-20T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

**Error Responses:**

- 401: Unauthorized
- 403: Forbidden (insufficient permissions)
- 500: Internal server error

## 4. Security Implementation

### 4.1 Password Hashing

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 4.2 JWT Token Generation

```python
from jose import jwt
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key-here"  # From environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
```

### 4.3 Token Payload Structure

```python
# Access Token Payload
{
    "sub": "user_id",           # Subject (user ID)
    "email": "user@example.com",
    "user_type": "user",
    "type": "access",
    "exp": 1234567890,          # Expiration timestamp
    "iat": 1234567000           # Issued at timestamp
}

# Refresh Token Payload
{
    "sub": "user_id",
    "token_family": "uuid",     # For token rotation
    "type": "refresh",
    "exp": 1234567890,
    "iat": 1234567000
}
```

### 4.4 Password Validation

```python
import re

def validate_password(password: str) -> tuple[bool, str]:
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain special character"
    return True, "Password is valid"
```

### 4.5 Account Locking Logic

```python
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 30

async def handle_failed_login(user: User, db: Session):
    user.failed_login_attempts += 1

    if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_DURATION_MINUTES)
        user.status = UserStatus.SUSPENDED

    db.commit()

async def check_account_lock(user: User) -> bool:
    if user.locked_until and user.locked_until > datetime.utcnow():
        return True

    # Unlock account if lock period expired
    if user.locked_until and user.locked_until <= datetime.utcnow():
        user.locked_until = None
        user.failed_login_attempts = 0
        user.status = UserStatus.ACTIVE

    return False
```

## 5. Configuration Management

### 5.1 Environment Variables (.env)

```bash
# Application
APP_NAME=Identity Service
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql://user:password@postgres:5432/identity_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Security
SECRET_KEY=your-super-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
CORS_ALLOW_CREDENTIALS=true

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Logging
LOG_LEVEL=INFO
```

### 5.2 Configuration Class (config.py)

```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    app_name: str = "Identity Service"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["http://localhost:3000"]
    cors_allow_credentials: bool = True

    # Rate Limiting
    rate_limit_per_minute: int = 60

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

## 6. Docker Configuration

### 6.1 Dockerfile

```dockerfile
# Multi-stage build for optimized image size
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 Docker Compose (docker-compose.yml)

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:15-alpine
    container_name: identity_postgres
    environment:
      POSTGRES_USER: identity_user
      POSTGRES_PASSWORD: identity_pass
      POSTGRES_DB: identity_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U identity_user -d identity_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - identity_network

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: identity_api
    environment:
      DATABASE_URL: postgresql://identity_user:identity_pass@postgres:5432/identity_db
      SECRET_KEY: ${SECRET_KEY:-dev-secret-key-change-in-production}
      DEBUG: ${DEBUG:-false}
      ENVIRONMENT: ${ENVIRONMENT:-development}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - ./app:/app/app
      - ./alembic:/app/alembic
    command: >
      sh -c "
        alembic upgrade head &&
        python scripts/seed_data.py &&
        uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      "
    networks:
      - identity_network

volumes:
  postgres_data:

networks:
  identity_network:
    driver: bridge
```

## 7. Database Initialization Script

### 7.1 init_db.sql

```sql
-- Create custom enum types
CREATE TYPE usertype AS ENUM ('system_admin', 'organization_admin', 'user', 'guest');
CREATE TYPE userstatus AS ENUM ('active', 'inactive', 'suspended', 'pending');
CREATE TYPE organizationtype AS ENUM ('enterprise', 'business', 'startup', 'individual');
CREATE TYPE organizationstatus AS ENUM ('active', 'inactive', 'suspended', 'trial');
CREATE TYPE teamrole AS ENUM ('owner', 'admin', 'member', 'viewer');
CREATE TYPE teamtype AS ENUM ('department', 'project', 'functional', 'cross_functional');
CREATE TYPE resourcetype AS ENUM ('user', 'organization', 'team', 'role', 'permission');
CREATE TYPE actiontype AS ENUM ('create', 'read', 'update', 'delete', 'manage', 'execute');

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

## 8. Seed Data Specification

### 8.1 Default Organization

```python
{
    "name": "Default Organization",
    "slug": "default-org",
    "display_name": "Default Organization",
    "organization_type": "business",
    "status": "active",
    "is_active": True
}
```

### 8.2 Default Roles

```python
roles = [
    {
        "name": "System Administrator",
        "code": "system_admin",
        "description": "Full system access",
        "is_system": True,
        "hierarchy_level": 100
    },
    {
        "name": "Organization Administrator",
        "code": "org_admin",
        "description": "Organization-level access",
        "is_system": True,
        "hierarchy_level": 50
    },
    {
        "name": "User",
        "code": "user",
        "description": "Standard user access",
        "is_system": True,
        "is_default": True,
        "hierarchy_level": 10
    }
]
```

### 8.3 Default Permissions

```python
permissions = [
    # User permissions
    {"code": "user.create", "name": "Create User", "resource": "user", "action": "create"},
    {"code": "user.read", "name": "Read User", "resource": "user", "action": "read"},
    {"code": "user.update", "name": "Update User", "resource": "user", "action": "update"},
    {"code": "user.delete", "name": "Delete User", "resource": "user", "action": "delete"},
    {"code": "user.manage", "name": "Manage Users", "resource": "user", "action": "manage"},

    # Organization permissions
    {"code": "org.create", "name": "Create Organization", "resource": "organization", "action": "create"},
    {"code": "org.read", "name": "Read Organization", "resource": "organization", "action": "read"},
    {"code": "org.update", "name": "Update Organization", "resource": "organization", "action": "update"},
    {"code": "org.delete", "name": "Delete Organization", "resource": "organization", "action": "delete"},

    # Role permissions
    {"code": "role.create", "name": "Create Role", "resource": "role", "action": "create"},
    {"code": "role.read", "name": "Read Role", "resource": "role", "action": "read"},
    {"code": "role.update", "name": "Update Role", "resource": "role", "action": "update"},
    {"code": "role.delete", "name": "Delete Role", "resource": "role", "action": "delete"},
]
```

### 8.4 Test Users

```python
users = [
    {
        "email": "admin@example.com",
        "password": "Admin123!",
        "first_name": "System",
        "last_name": "Administrator",
        "user_type": "system_admin",
        "status": "active",
        "email_verified": True,
        "role": "system_admin"
    },
    {
        "email": "john.doe@example.com",
        "password": "User123!",
        "first_name": "John",
        "last_name": "Doe",
        "user_type": "user",
        "status": "active",
        "email_verified": True,
        "role": "user"
    },
    {
        "email": "jane.smith@example.com",
        "password": "User123!",
        "first_name": "Jane",
        "last_name": "Smith",
        "user_type": "user",
        "status": "active",
        "email_verified": True,
        "role": "user"
    }
]
```

## 9. Pydantic Schemas

### 9.1 User Schemas

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID

class UserBase(BaseModel):
    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class UserResponse(UserBase):
    id: UUID
    display_name: Optional[str]
    user_type: str
    status: str
    email_verified: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    users: list[UserResponse]
    pagination: dict
```

### 9.2 Auth Schemas

```python
class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    device_info: Optional[dict] = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class LogoutRequest(BaseModel):
    refresh_token: str

class RegisterResponse(BaseModel):
    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
```

## 10. Error Handling

### 10.1 Custom Exceptions

```python
class AuthenticationError(Exception):
    pass

class AccountLockedException(Exception):
    pass

class TokenExpiredException(Exception):
    pass

class InvalidTokenException(Exception):
    pass

class UserNotFoundException(Exception):
    pass

class DuplicateEmailException(Exception):
    pass
```

### 10.2 Error Response Format

```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Example error responses
{
    "error": "AUTHENTICATION_FAILED",
    "message": "Invalid email or password",
    "timestamp": "2024-01-23T10:00:00Z"
}

{
    "error": "ACCOUNT_LOCKED",
    "message": "Account locked due to too many failed login attempts",
    "details": {
        "locked_until": "2024-01-23T10:30:00Z",
        "reason": "max_failed_attempts"
    },
    "timestamp": "2024-01-23T10:00:00Z"
}

{
    "error": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
        "password": ["Password must contain uppercase letter"]
    },
    "timestamp": "2024-01-23T10:00:00Z"
}
```

## 11. Dependencies & Requirements

### 11.1 requirements.txt

```txt
# FastAPI
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9

# Validation
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0

# Security
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Utilities
python-dotenv==1.0.0
```

## 12. Testing Strategy

### 12.1 Test Coverage Areas

- Unit tests for password hashing/validation
- Unit tests for JWT token generation/validation
- Integration tests for all API endpoints
- Database transaction tests
- Authentication flow tests
- Error handling tests

### 12.2 Test Data

```python
# Test fixtures
@pytest.fixture
def test_user():
    return {
        "email": "test@example.com",
        "password": "Test123!",
        "first_name": "Test",
        "last_name": "User"
    }

@pytest.fixture
def test_db():
    # Create test database session
    pass

@pytest.fixture
def auth_headers(test_user):
    # Generate valid auth headers
    pass
```

## 13. Logging Strategy

### 13.1 Log Events

```python
# Authentication events
logger.info(f"User login attempt: {email}")
logger.info(f"User login success: {user_id}")
logger.warning(f"Failed login attempt: {email}")
logger.warning(f"Account locked: {user_id}")

# Token events
logger.info(f"Access token generated: {user_id}")
logger.info(f"Refresh token generated: {user_id}")
logger.info(f"Token refresh: {user_id}")
logger.warning(f"Invalid token attempt: {token_id}")

# User management
logger.info(f"User registered: {user_id}")
logger.info(f"User logout: {user_id}")
```

## 14. Health Check Endpoint

### 14.1 GET /health

```python
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    try:
        # Check database connection
        db.execute("SELECT 1")

        return {
            "status": "healthy",
            "service": "identity-service",
            "version": settings.app_version,
            "timestamp": datetime.utcnow(),
            "database": "connected"
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "identity-service",
            "error": str(e),
            "timestamp": datetime.utcnow()
        }
```

## 15. Implementation Notes

### 15.1 Database Migrations

- Use Alembic for all schema changes
- Create initial migration with all tables
- Seed data runs after migrations
- Migrations are idempotent

### 15.2 Token Storage

- Refresh tokens stored in database with hash
- Access tokens are stateless (not stored)
- Token family for rotation tracking
- Device fingerprinting for security

### 15.3 Performance Considerations

- Database connection pooling (20 connections)
- Index on frequently queried fields (email, token_hash)
- Pagination for list endpoints
- Lazy loading for relationships

### 15.4 Security Best Practices

- Never log passwords or tokens
- Use parameterized queries (SQLAlchemy ORM)
- Validate all input with Pydantic
- Rate limiting on auth endpoints
- HTTPS only in production
- Secure cookie settings for tokens

## 16. Future Enhancements (Out of Scope)

- Email verification flow implementation
- Password reset flow implementation
- MFA/2FA support
- OAuth2 integration (Google, GitHub)
- SSO support
- Advanced RBAC with conditions
- Audit logging for all actions
- Rate limiting middleware
- Redis for token blacklisting
- Prometheus metrics
- OpenTelemetry tracing
