#!/usr/bin/env bash
# ============================================================
# SnapDeploy Start Script — Core Service
# Usage: bash snapdeploy/start-core.sh
# ============================================================
set -e

echo "=== Core Service ==="
echo "Installing dependencies..."
cd core-service && pip install -r requirements.txt

echo "Running migrations..."
python -m alembic upgrade head

echo "Starting server on port 8001..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8001
