#!/usr/bin/env bash
# ============================================================
# SnapDeploy Start Script — Identity Service
# Usage: bash snapdeploy/start-identity.sh
# ============================================================
set -e

echo "=== Identity Service ==="
echo "Installing dependencies..."
cd identity-service && pip install -r requirements.txt

echo "Running migrations..."
python -m alembic upgrade head

echo "Starting server on port 8000..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
