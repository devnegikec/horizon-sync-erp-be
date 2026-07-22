# Root Dockerfile for Railway monorepo - Core Service
# Railway GitHub integration looks for Dockerfile at repo root.

FROM python:3.11-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY core-service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

COPY core-service/ .

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
