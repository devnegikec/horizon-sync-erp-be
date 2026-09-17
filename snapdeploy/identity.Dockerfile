# ============================================================
# SnapDeploy Production Dockerfile — Identity Service
# ============================================================
# Deploy: Point SnapDeploy to this file (snapdeploy/identity.Dockerfile)
# Port:    8000
# ============================================================

# --- Builder Stage ---
FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY identity-service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Final Stage ---
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy only identity-service code
COPY identity-service/ .

# Production env defaults (override via SnapDeploy dashboard)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ENVIRONMENT=production \
    DEBUG=false \
    LOG_LEVEL=INFO \
    HOST=0.0.0.0 \
    PORT=8000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Startup: run migrations then start the server
CMD echo 'Running Identity Service migrations...' && \
    python -m alembic upgrade head && \
    echo 'Starting Identity Service...' && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
