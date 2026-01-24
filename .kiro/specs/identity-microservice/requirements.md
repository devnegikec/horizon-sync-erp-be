# Identity Microservice - Requirements

## 1. Overview

Build a FastAPI-based identity microservice for authentication and user management with PostgreSQL database, SQLAlchemy ORM, and Docker containerization.

## 2. User Stories

### 2.1 User Registration

**As a** new user
**I want to** register an account
**So that** I can access the system

**Acceptance Criteria:**

- User can register with email, password, first name, and last name
- Email must be unique and validated
- Password must be hashed using secure algorithm (bcrypt/argon2)
- User receives verification email after registration
- Default user status is 'pending' until email verified
- Returns JWT access and refresh tokens upon successful registration

### 2.2 User Login

**As a** registered user
**I want to** login with my credentials
**So that** I can access protected resources

**Acceptance Criteria:**

- User can login with email and password
- System validates credentials against database
- Failed login attempts are tracked (max 5 attempts before account lock)
- Account locks for 30 minutes after 5 failed attempts
- Returns JWT access token (15 min expiry) and refresh token (7 days expiry)
- Updates last_login_at and last_login_ip fields
- Stores refresh token in database with device information

### 2.3 Token Refresh

**As a** user with valid refresh token
**I want to** obtain new access token
**So that** I can continue using the system without re-login

**Acceptance Criteria:**

- User can exchange valid refresh token for new access token
- System validates refresh token hasn't expired or been revoked
- Returns new access token with same claims
- Updates last_used_at timestamp on refresh token
- Implements token rotation (optional: issue new refresh token)

### 2.4 User Logout

**As a** logged-in user
**I want to** logout from the system
**So that** my session is terminated securely

**Acceptance Criteria:**

- User can logout with valid access token
- System revokes the associated refresh token
- Refresh token marked with revoked_at timestamp and reason
- Returns success confirmation

### 2.5 List Users

**As an** administrator
**I want to** view all users in the system
**So that** I can manage user accounts

**Acceptance Criteria:**

- Endpoint requires authentication (valid access token)
- Returns paginated list of users (default 20 per page)
- Supports filtering by status, user_type, email_verified
- Supports search by email, first_name, last_name
- Excludes sensitive fields (password_hash, mfa_secret)
- Returns user count and pagination metadata

## 3. Technical Requirements

### 3.1 Technology Stack

- **Framework:** FastAPI 0.104+
- **ORM:** SQLAlchemy 2.0+
- **Database:** PostgreSQL 15+
- **ASGI Server:** Uvicorn
- **Validation:** Pydantic v2
- **Authentication:** JWT (PyJWT)
- **Password Hashing:** passlib with bcrypt
- **Containerization:** Docker & Docker Compose

### 3.2 Database Tables

Implement the following tables from schema.dbml:

- users
- refresh_tokens
- email_verifications
- password_resets
- organizations (basic structure for multi-tenancy)
- roles
- permissions
- role_permissions
- user_organization_roles

### 3.3 API Endpoints

- `POST /api/v1/identity/register` - User registration
- `POST /api/v1/identity/login` - User login
- `POST /api/v1/identity/refresh` - Refresh access token
- `POST /api/v1/identity/logout` - User logout
- `GET /api/v1/identity/users` - List users (paginated)

### 3.4 Security Requirements

- All passwords must be hashed using bcrypt (12 rounds minimum)
- JWT tokens must use HS256 or RS256 algorithm
- Access tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Implement rate limiting on authentication endpoints
- Store refresh tokens securely with device fingerprinting
- Validate all input using Pydantic models
- Implement CORS with configurable origins

### 3.5 Docker Requirements

- Multi-stage Dockerfile for optimized image size
- Docker Compose with services: api, postgres
- Environment-based configuration
- Health check endpoints
- Volume persistence for PostgreSQL data
- Network isolation between services

### 3.6 Seed Data Requirements

- Create default organization
- Create admin role with all permissions
- Create user role with basic permissions
- Create 3 test users (1 admin, 2 regular users)
- All test users should have verified emails
- Generate sample refresh tokens for testing

## 4. Non-Functional Requirements

### 4.1 Performance

- API response time < 200ms for authentication endpoints
- Support 100 concurrent users minimum
- Database connection pooling enabled

### 4.2 Scalability

- Stateless API design for horizontal scaling
- Database migrations managed via Alembic
- Configuration via environment variables

### 4.3 Maintainability

- Clear project structure following FastAPI best practices
- Comprehensive error handling with proper HTTP status codes
- Logging for all authentication events
- API documentation via OpenAPI/Swagger

### 4.4 Reliability

- Database transactions for data consistency
- Graceful error handling and rollback
- Health check endpoint for monitoring

## 5. Out of Scope

- Email sending functionality (mock/log only)
- MFA/2FA implementation
- OAuth/SSO integration
- Password reset flow (database structure only)
- Email verification flow (database structure only)
- Advanced RBAC enforcement
- API rate limiting implementation
- Monitoring and observability tools

## 6. Database Schema Issues

After reviewing the schema.dbml file, here are observations:

### 6.1 Potential Issues

1. **Missing Primary Key Constraints:** DBML doesn't show explicit PK definitions - need to ensure `id` fields are PRIMARY KEY
2. **Missing Unique Constraints:**
   - `users.email` should be UNIQUE
   - `organizations.slug` should be UNIQUE
   - `roles.code` should be UNIQUE per organization
3. **Missing NOT NULL Constraints:** Critical fields need NOT NULL (email, password_hash, etc.)
4. **Enum Types:** Schema references custom types (e.g., `public.usertype`) - need to create these enums
5. **Index Requirements:** Need indexes on frequently queried fields (email, organization_id, etc.)

### 6.2 Required Enums

Based on schema, need to create:

- `usertype` (system_admin, organization_admin, user, etc.)
- `userstatus` (active, inactive, suspended, pending)
- `organizationtype` (enterprise, business, startup, etc.)
- `organizationstatus` (active, inactive, suspended)
- `teamrole` (owner, admin, member)
- `teamtype` (department, project, functional)
- `resourcetype` (user, organization, team, etc.)
- `actiontype` (create, read, update, delete, etc.)

### 6.3 Recommendations

1. Add explicit foreign key constraints with ON DELETE CASCADE/SET NULL
2. Add created_by/updated_by tracking on all relevant tables
3. Consider adding indexes on foreign keys
4. Add check constraints for email format validation
5. Add default values for timestamps (CURRENT_TIMESTAMP)

## 7. Success Criteria

- All 5 API endpoints functional and tested
- Docker Compose brings up entire stack successfully
- Database migrations create all required tables
- Seed data populates successfully
- Postman/curl can execute full authentication flow
- API documentation accessible at /docs
- All acceptance criteria met for user stories
