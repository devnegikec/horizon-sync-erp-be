"""Main FastAPI application for Core Service"""

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
    AuthenticationError,
    AuthorizationError,
    CannotDeleteException,
    ChartOfAccountNotFoundException,
    CircularReferenceException,
    CustomerNotFoundException,
    DuplicateAccountCodeException,
    DuplicateCustomerCodeException,
    DuplicateItemCodeException,
    DuplicateItemGroupCodeException,
    DuplicateSupplierCodeException,
    DuplicateWarehouseCodeException,
    ItemGroupNotFoundException,
    ItemNotFoundException,
    SupplierNotFoundException,
    ValidationError,
    WarehouseNotFoundException,
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
    logger.info(f"Identity Service URL: {settings.identity_service_url}")
    yield
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Core Service - Inventory, Order, and Billing Management Microservice",
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
            "service": "core-service",
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
                "service": "core-service",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "database": "disconnected",
            },
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


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization errors"""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "AUTHORIZATION_FAILED",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(ItemNotFoundException)
async def item_not_found_exception_handler(
    request: Request, exc: ItemNotFoundException
):
    """Handle item not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "ITEM_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(ItemGroupNotFoundException)
async def item_group_not_found_exception_handler(
    request: Request, exc: ItemGroupNotFoundException
):
    """Handle item group not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "ITEM_GROUP_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(WarehouseNotFoundException)
async def warehouse_not_found_exception_handler(
    request: Request, exc: WarehouseNotFoundException
):
    """Handle warehouse not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "WAREHOUSE_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateItemCodeException)
async def duplicate_item_code_exception_handler(
    request: Request, exc: DuplicateItemCodeException
):
    """Handle duplicate item code errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_ITEM_CODE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateItemGroupCodeException)
async def duplicate_item_group_code_exception_handler(
    request: Request, exc: DuplicateItemGroupCodeException
):
    """Handle duplicate item group code errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_ITEM_GROUP_CODE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateWarehouseCodeException)
async def duplicate_warehouse_code_exception_handler(
    request: Request, exc: DuplicateWarehouseCodeException
):
    """Handle duplicate warehouse code errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_WAREHOUSE_CODE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(CustomerNotFoundException)
async def customer_not_found_exception_handler(
    request: Request, exc: CustomerNotFoundException
):
    """Handle customer not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "CUSTOMER_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(SupplierNotFoundException)
async def supplier_not_found_exception_handler(
    request: Request, exc: SupplierNotFoundException
):
    """Handle supplier not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "SUPPLIER_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(ChartOfAccountNotFoundException)
async def chart_of_account_not_found_exception_handler(
    request: Request, exc: ChartOfAccountNotFoundException
):
    """Handle chart of account not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "CHART_OF_ACCOUNT_NOT_FOUND",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateCustomerCodeException)
async def duplicate_customer_code_exception_handler(
    request: Request, exc: DuplicateCustomerCodeException
):
    """Handle duplicate customer code errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_CUSTOMER_CODE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateSupplierCodeException)
async def duplicate_supplier_code_exception_handler(
    request: Request, exc: DuplicateSupplierCodeException
):
    """Handle duplicate supplier code errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_SUPPLIER_CODE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(DuplicateAccountCodeException)
async def duplicate_account_code_exception_handler(
    request: Request, exc: DuplicateAccountCodeException
):
    """Handle duplicate account code errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "DUPLICATE_ACCOUNT_CODE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(CircularReferenceException)
async def circular_reference_exception_handler(
    request: Request, exc: CircularReferenceException
):
    """Handle circular reference errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "CIRCULAR_REFERENCE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(CannotDeleteException)
async def cannot_delete_exception_handler(request: Request, exc: CannotDeleteException):
    """Handle cannot delete errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "CANNOT_DELETE",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(ValidationError)
async def custom_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle custom validation errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "VALIDATION_FAILED",
            "message": str(exc),
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    logger.error(f"Database error: {exc}")
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
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now(UTC).isoformat(),
        },
    )
