#!/usr/bin/env bash
# Deploy local code to Railway for the Horizon Sync project.
#
# Runs `railway up` from the repo root so railway.toml (config-as-code) is used.
# Each service is built from its own source directory using its own Dockerfile.
#
# Usage:
#   ./deploy_local_to_railway.sh [service] ["deploy message"]
#
#   service  : one of identity-service, core-service, qr-worker,
#              search-service, nginx-gateway — or "all" to deploy every service.
#              Defaults to identity-service.
#
# Env overrides:
#   RAILWAY_PROJECT_ID    Railway project ID (default below)
#   RAILWAY_ENVIRONMENT   Railway environment (default: production)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_ID="${RAILWAY_PROJECT_ID:-7abe5082-844c-4791-8158-f47e14fb68cb}"
ENVIRONMENT="${RAILWAY_ENVIRONMENT:-production}"
SERVICE="${1:-identity-service}"
MESSAGE="${2:-deploy from local}"

ALL_SERVICES=(identity-service core-service qr-worker search-service nginx-gateway)

usage() {
  cat <<EOF
Usage: $0 [service] ["deploy message"]

Services: ${ALL_SERVICES[*]}   (or "all" for every service)
Default service: identity-service

Env overrides:
  RAILWAY_PROJECT_ID   (default: $PROJECT_ID)
  RAILWAY_ENVIRONMENT  (default: $ENVIRONMENT)
EOF
}

if [[ "$SERVICE" == "-h" || "$SERVICE" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v railway >/dev/null 2>&1; then
  echo "ERROR: Railway CLI not found. Install: npm i -g @railway/cli"
  exit 1
fi

deploy_service() {
  local svc="$1"
  echo "──────────────────────────────────────────────"
  echo "Deploying '$svc' → project $PROJECT_ID ($ENVIRONMENT)"
  echo "Message: $MESSAGE"
  echo "──────────────────────────────────────────────"
  railway up \
    -p "$PROJECT_ID" \
    -s "$svc" \
    -e "$ENVIRONMENT" \
    -m "$MESSAGE" \
    -d
}

if [[ "$SERVICE" == "all" ]]; then
  for svc in "${ALL_SERVICES[@]}"; do
    deploy_service "$svc"
  done
else
  found=0
  for svc in "${ALL_SERVICES[@]}"; do
    if [[ "$svc" == "$SERVICE" ]]; then
      found=1
      break
    fi
  done
  if [[ "$found" -ne 1 ]]; then
    echo "ERROR: Unknown service '$SERVICE'. Valid: ${ALL_SERVICES[*]}"
    usage
    exit 1
  fi
  deploy_service "$SERVICE"
fi

echo ""
echo "Deploy started. Monitor at https://railway.app/project/$PROJECT_ID/services"
