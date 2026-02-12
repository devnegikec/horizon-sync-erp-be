"""Main FastAPI application for Search Service"""

import asyncio
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

from app.config import settings
from app.database import async_engine, AsyncSessionLocal
from app.logging_config import get_logger
from app.services.sync_service import start_auto_sync
from app.workers.event_consumer import SearchIndexEventConsumer

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = get_logger(__name__)

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
    logger.info(f"Core Service URL: {settings.core_service_url}")
    logger.info(f"Redis URL: {settings.redis_url}")
    
    # Start event consumer for real-time sync
    event_consumer = SearchIndexEventConsumer()
    consumer_task = asyncio.create_task(event_consumer.start())
    logger.info("Started real-time event consumer for search index updates")
    
    # Start periodic fallback sync (runs every hour as backup)
    start_auto_sync(app, AsyncSessionLocal, interval_seconds=3600)
    logger.info("Started periodic fallback sync (every 60 minutes)")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    
    # Stop event consumer
    await event_consumer.stop()
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    
    await async_engine.dispose()


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Search Service - Unified Search API for ERP System",
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
        async with async_engine.connect() as conn:
            await conn.execute(sa.text("SELECT 1"))

        return {
            "status": "healthy",
            "service": "search-service",
            "version": settings.app_version,
            "environment": settings.environment,
            "timestamp": datetime.now(UTC).isoformat(),
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": "search-service",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
                "database": "disconnected",
            },
        )


# Exception handlers
def create_error_response(status_code: int, message: str, code: str):
    """Utility to create consistent error responses"""
    return JSONResponse(
        status_code=status_code,
        content={
            "detail": {
                "message": message,
                "status_code": status_code,
                "code": code,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"] if loc != "body")
        errors.append({"field": field, "message": error["msg"]})

    logger.warning(f"Validation error: {errors}")
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message="Invalid input data",
        code="VALIDATION_ERROR",
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors"""
    logger.warning(f"Value error: {exc}")
    return create_error_response(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=str(exc),
        code="INVALID_VALUE",
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    logger.error(f"Database error: {exc}", exc_info=True)
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="A database error occurred",
        code="DATABASE_ERROR",
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general errors"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        message="An unexpected error occurred",
        code="INTERNAL_SERVER_ERROR",
    )


# Include API router
from app.api.v1.router import api_router

app.include_router(api_router, prefix="/api/v1")
