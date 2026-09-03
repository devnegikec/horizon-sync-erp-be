#!/usr/bin/env bash
# Deploy local code to Railway for the Horizon Sync project.
#
# Runs `railway up` from the repo root so railway.toml (config-as-code) is used.
# Each service is built from its own source directory using its own Dockerfile.
#
# Migrations run automatically on deploy via each service's start command
# (see railway.toml): `scripts/normalize_alembic_version.py && alembic upgrade`.
# Pass --migrate to explicitly re-trigger migrations after deploy.
#
# Usage:
#   ./deploy_local_to_railway.sh [service] ["deploy message"] [--migrate]
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
MIGRATE=0

ALL_SERVICES=(identity-service core-service qr-worker search-service nginx-gateway)

usage() {
  cat <<EOF
Usage: $0 [service] ["deploy message"] [--migrate]

Services: ${ALL_SERVICES[*]}   (or "all" for every service)
Default service: identity-service

Flags:
  --migrate, -m   After deploy, re-run the service migrations (via redeploy).

Env overrides:
  RAILWAY_PROJECT_ID   (default: $PROJECT_ID)
  RAILWAY_ENVIRONMENT  (default: $ENVIRONMENT)
EOF
}

positional=()
for arg in "$@"; do
  case "$arg" in
    --migrate|-m) MIGRATE=1 ;;
    -h|--help) usage; exit 0 ;;
    *) positional+=("$arg") ;;
  esac
done

SERVICE="${positional[0]:-identity-service}"
MESSAGE="${positional[1]:-deploy from local}"

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

  if [[ "$MIGRATE" -eq 1 ]]; then
    echo "Re-triggering migrations for '$svc' ..."
    railway redeploy \
      -p "$PROJECT_ID" \
      -s "$svc" \
      -e "$ENVIRONMENT" \
      -y \
      || echo "WARNING: redeploy failed; migrations still run automatically on the next deploy."
  fi
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
