# ============================================================
# SnapDeploy Production Dockerfile — Search Service
# ============================================================
# Deploy: Point SnapDeploy to this file (snapdeploy/search.Dockerfile)
# Port:    8002
# ============================================================

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY search-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only search-service code
COPY search-service/ .

# Create non-root user
RUN useradd -m -u 1000 searchuser && chown -R searchuser:searchuser /app
USER searchuser

# Production env defaults (override via SnapDeploy dashboard)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8002

EXPOSE 8002

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8002/health || exit 1

# Startup: run migrations then start the server
CMD echo 'Running Search Service migrations...' && \
    python -m alembic upgrade head && \
    echo 'Starting Search Service...' && \
    uvicorn app.main:app --host 0.0.0.0 --port 8002
