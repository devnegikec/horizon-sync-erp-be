"""Main FastAPI application for AI Service"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.copilot import router as copilot_router
from app.api.detect import router as detect_router
from app.api.ingest import router as ingest_router
from app.api.mcp import router as mcp_router
from app.config import settings
from app.database import Base, engine
from app.models import ChatLog, DiscrepancyAlert, DiscrepancyFeedback, IngestionJob, VectorChunk

logger = logging.getLogger(__name__)


def _create_tables():
    """Create all SQLAlchemy tables on startup (dev convenience)."""
    # Try to enable pgvector extension (RAG / embeddings); ignore failure
    try:
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning("pgvector extension not available (RAG features disabled): %s", e)

    # Create tables one-by-one so a single pgvector failure doesn't block others
    created = 0
    failed = 0
    for table in Base.metadata.sorted_tables:
        try:
            table.create(engine, checkfirst=True)
            logger.info("Table created / verified: %s", table.name)
            created += 1
        except Exception as e:
            logger.warning("Table %s creation failed (pgvector missing?): %s", table.name, e)
            failed += 1
    logger.info("Table creation: %d succeeded, %d failed", created, failed)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler: startup and shutdown logic."""
    logger.info("AI Service starting up...")
    _create_tables()
    # Future: initialize vector DB connection, load models, warm caches
    yield
    logger.info("AI Service shutting down...")
    # Future: close connections, save state


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.MCP_SERVER_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
app.include_router(ingest_router, prefix="/ai", tags=["ai-ingestion"])
app.include_router(copilot_router, prefix="/ai", tags=["ai-copilot"])
app.include_router(detect_router, prefix="/ai", tags=["ai-detection"])


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker / load balancer."""
    return {"status": "healthy", "service": settings.APP_NAME}
