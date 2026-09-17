# ============================================================
# SnapDeploy Production Dockerfile — Core Service
# ============================================================
# Deploy: Point SnapDeploy to this file (snapdeploy/core.Dockerfile)
# Port:    8001
# ============================================================

# --- Builder Stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY core-service/requirements.txt .

RUN pip install --upgrade pip \
    && pip install numpy==1.26.4 \
    && pip install pandas==2.1.4 \
    && pip install -r requirements.txt

# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages \
    /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy only core-service code
COPY core-service/ .

# Production env defaults (override via SnapDeploy dashboard)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Startup: run migrations then start the server
CMD echo 'Running Core Service migrations...' && \
    python -m alembic upgrade head && \
    echo 'Starting Core Service...' && \
    uvicorn app.main:app --host 0.0.0.0 --port 8001
