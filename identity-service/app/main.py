"""Main FastAPI application"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
import sqlalchemy as sa
import warnings

# Suppress passlib deprecation warning (internal to the library in Python 3.11+)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib")
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.api.v1.router import api_router
from app.database import engine, Base
from app.core.exceptions import (
    AuthenticationError,
    AccountLockedException,
    DuplicateEmailException,
    PasswordValidationException,
    InvalidTokenException,
    TokenExpiredException,
    UserNotFoundException
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for the application"""
    # Startup
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print(f"Environment: {settings.environment}")
    print(f"Debug mode: {settings.debug}")
    yield
    # Shutdown
    print(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Identity Service - Authentication and User Management Microservice",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected"
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "identity-service",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "database": "disconnected"
            }
        )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({
            "field": field,
            "message": error["msg"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Invalid input data",
            "details": errors,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "AUTHENTICATION_FAILED",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(AccountLockedException)
async def account_locked_exception_handler(request: Request, exc: AccountLockedException):
    """Handle account locked errors"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "ACCOUNT_LOCKED",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(DuplicateEmailException)
async def duplicate_email_exception_handler(request: Request, exc: DuplicateEmailException):
    """Handle duplicate email errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_EMAIL",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(PasswordValidationException)
async def password_validation_exception_handler(request: Request, exc: PasswordValidationException):
    """Handle password validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "PASSWORD_VALIDATION_FAILED",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(InvalidTokenException)
async def invalid_token_exception_handler(request: Request, exc: InvalidTokenException):
    """Handle invalid token errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "INVALID_TOKEN",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(TokenExpiredException)
async def token_expired_exception_handler(request: Request, exc: TokenExpiredException):
    """Handle token expired errors"""
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={
            "error": "TOKEN_EXPIRED",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(UserNotFoundException)
async def user_not_found_exception_handler(request: Request, exc: UserNotFoundException):
    """Handle user not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "USER_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "DATABASE_ERROR",
            "message": "A database error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )



