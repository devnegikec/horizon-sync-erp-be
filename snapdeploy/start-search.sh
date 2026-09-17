#!/usr/bin/env bash
# ============================================================
# SnapDeploy Start Script — Search Service
# Usage: bash snapdeploy/start-search.sh
# ============================================================
set -e

echo "=== Search Service ==="
echo "Installing dependencies..."
cd search-service && pip install -r requirements.txt

echo "Running migrations..."
python -m alembic upgrade head

echo "Starting server on port 8002..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8002
