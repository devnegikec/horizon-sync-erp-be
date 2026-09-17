"""Main FastAPI application"""

import logging
import warnings
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import sqlalchemy as sa
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import (
    AccountLockedException,
    AuthenticationError,
    DuplicateEmailException,
    DuplicateOrganizationSlugException,
    DuplicateResourceException,
    InvalidTokenException,
    OrganizationNotFoundException,
    PasswordValidationException,
    ResourceNotFoundException,
    TokenExpiredException,
    UserNotFoundException,
    ValidationException,
)
from app.database import engine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress passlib deprecation warning
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    # Register audit trail listeners
    from app.core.audit_listener import register_audit_listeners

    register_audit_listeners()

    # Auto-seed system admin roles & permissions (idempotent)
    try:
        from scripts.seed_system_admin_roles import seed_system_admin_roles
        seed_system_admin_roles()
        logger.info("System admin roles & permissions seed completed")
    except Exception as e:
        logger.warning(f"System admin seed skipped or failed: {e}")

    # Ensure canonical organization.* permissions exist (idempotent safety net)
    try:
        from app.database import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        try:
            for action in ("read", "create", "update", "delete", "manage"):
                code = f"organization.{action}"
                db.execute(text("""
                    INSERT INTO permissions (id, code, name, resource, action, module, is_active, created_at, updated_at, extra_data)
                    SELECT
                        gen_random_uuid(),
                        :code,
                        :name,
                        'organization',
                        :action,
                        'identity',
                        true,
                        NOW(),
                        NOW(),
                        '{}'::jsonb
                    WHERE NOT EXISTS (
                        SELECT 1 FROM permissions WHERE code = :code
                    )
                """), {"code": code, "name": f"Organization {action.title()}", "action": action})
            db.commit()
            logger.info("organization.* permissions ensured")
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"organization.* permission ensure step failed: {e}")

    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Identity Service - Authentication and User Management Microservice",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """
    Health check endpoint.

    Returns service status and database connectivity.
    """
    try:
        # Test database connection
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))

        return {
            "status": "healthy",
            "service": "identity-service",
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected",
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "identity-service",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "database": "disconnected",
            },
        )


# Include API router
app.include_router(api_router, prefix="/api/v1")

# Audit context middleware (must be after CORS)
from app.middleware.audit_middleware import AuditContextMiddleware

app.add_middleware(AuditContextMiddleware)


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": error["msg"]})

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid input data",
            "details": errors,
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "AUTHENTICATION_FAILED",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(AccountLockedException)
async def account_locked_exception_handler(
    request: Request, exc: AccountLockedException
):
    """Handle account locked errors"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "ACCOUNT_LOCKED",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateEmailException)
async def duplicate_email_exception_handler(
    request: Request, exc: DuplicateEmailException
):
    """Handle duplicate email errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_EMAIL",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(PasswordValidationException)
async def password_validation_exception_handler(
    request: Request, exc: PasswordValidationException
):
    """Handle password validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "PASSWORD_VALIDATION_FAILED",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(InvalidTokenException)
async def invalid_token_exception_handler(request: Request, exc: InvalidTokenException):
    """Handle invalid token errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "INVALID_TOKEN",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(TokenExpiredException)
async def token_expired_exception_handler(request: Request, exc: TokenExpiredException):
    """Handle token expired errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "TOKEN_EXPIRED",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(UserNotFoundException)
async def user_not_found_exception_handler(
    request: Request, exc: UserNotFoundException
):
    """Handle user not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "USER_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "DATABASE_ERROR",
            "message": "A database error occurred",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateResourceException)
async def duplicate_resource_exception_handler(
    request: Request, exc: DuplicateResourceException
):
    """Handle duplicate resource errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_RESOURCE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(ResourceNotFoundException)
async def resource_not_found_exception_handler(
    request: Request, exc: ResourceNotFoundException
):
    """Handle resource not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "RESOURCE_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler_custom(
    request: Request, exc: ValidationException
):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_ERROR",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(OrganizationNotFoundException)
async def organization_not_found_exception_handler(
    request: Request, exc: OrganizationNotFoundException
):
    """Handle organization not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "ORGANIZATION_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateOrganizationSlugException)
async def duplicate_organization_slug_exception_handler(
    request: Request, exc: DuplicateOrganizationSlugException
):
    """Handle duplicate organization slug errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_ORGANIZATION_SLUG",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
