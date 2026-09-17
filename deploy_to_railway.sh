#!/usr/bin/env bash
# deploy_to_railway.sh
# Deploy Horizon Sync backend (core-service) to Railway using Railway CLI.
# Usage examples:
#   RAILWAY_TOKEN=xxx ./deploy_to_railway.sh -p <projectId> -e production -s core-service -m
#   ./deploy_to_railway.sh --project <projectId> --env staging

set -euo pipefail

SERVICE_DIR="core-service"
PROJECT_ID=""
ENVIRONMENT="production"
RAILWAY_TOKEN=""
RUN_MIGRATIONS=0

print_usage() {
  cat <<EOF
Usage: $0 [options]

Options:
  -p, --project    Railway project ID or name (optional; you can link interactively)
  -e, --env        Railway environment (default: production)
  -s, --service    Service directory to deploy (default: core-service)
  -t, --token      Railway token (or set RAILWAY_TOKEN env)
  -m, --migrate    Run migrations after deploy (calls 'make migrate' remotely)
  -h, --help       Show this help

Notes:
  - Requires Railway CLI installed: https://docs.railway.app/develop/cli
  - This script deploys from your local copy (uses 'railway up') and may be interactive.
  - If you provide a token it will attempt non-interactive login.
EOF
}

# Basic arg parsing
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project)
      PROJECT_ID="$2"; shift 2;;
    -e|--env)
      ENVIRONMENT="$2"; shift 2;;
    -s|--service)
      SERVICE_DIR="$2"; shift 2;;
    -t|--token)
      RAILWAY_TOKEN="$2"; shift 2;;
    -m|--migrate)
      RUN_MIGRATIONS=1; shift 1;;
    -h|--help)
      print_usage; exit 0;;
    *)
      echo "Unknown arg: $1"; print_usage; exit 1;;
  esac
done

# Allow token from env if not passed as arg
RAILWAY_TOKEN="${RAILWAY_TOKEN:-${RAILWAY_TOKEN:-}}"
# Make script executable for convenience
if [[ ! -x "$(pwd)/deploy_to_railway.sh" ]]; then
  chmod +x "$(pwd)/deploy_to_railway.sh" 2>/dev/null || true
fi

echo "Service dir: $SERVICE_DIR"
[ -d "$SERVICE_DIR" ] || { echo "Service directory '$SERVICE_DIR' does not exist."; exit 1; }

# Check for railway CLI
if ! command -v railway >/dev/null 2>&1; then
  echo "Railway CLI not found. Install with: npm i -g @railway/cli"
  exit 1
fi

# Login
if [[ -n "${RAILWAY_TOKEN}" ]]; then
  echo "Logging into Railway using token..."
  railway login --ci --token "$RAILWAY_TOKEN" || {
    echo "Token login failed; try interactive 'railway login' instead."; exit 1
  }
else
  echo "No token provided; running interactive 'railway login'..."
  railway login || { echo "Railway login failed."; exit 1; }
fi

# Link project (if provided) or let user select interactively
if [[ -n "$PROJECT_ID" ]]; then
  echo "Linking to Railway project: $PROJECT_ID"
  set +e
  railway link --project "$PROJECT_ID"
  LINK_EXIT=$?
  set -e
  if [[ $LINK_EXIT -ne 0 ]]; then
    echo "Failed to link project non-interactively. Running interactive 'railway link'..."
    railway link || { echo "railway link failed."; exit 1; }
  fi
else
  echo "No project specified; running interactive 'railway link' — choose the project to deploy to."
  railway link || { echo "railway link failed."; exit 1; }
fi

# Change to service directory
pushd "$SERVICE_DIR" >/dev/null

# Show current branch/git status to user
if command -v git >/dev/null 2>&1; then
  echo "Git branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
  echo "Uncommitted changes:"
  git status --porcelain || true
fi

# Deploy using railway up
echo "Starting 'railway up' (this will build and deploy the service)."
# Run railway up; user will see interactive output. Remove --detach if you want foreground logs.
railway up || { echo "railway up failed."; popd >/dev/null; exit 1; }

# Optionally run migrations remotely
if [[ $RUN_MIGRATIONS -eq 1 ]]; then
  echo "Running migrations on remote environment ($ENVIRONMENT)..."
  # This calls the Makefile migrate target remotely. Adjust if your service requires a different command.
  railway run -- make migrate || { echo "Remote migrations failed."; popd >/dev/null; exit 1; }
fi

popd >/dev/null

echo "Deployment finished. Verify the service on Railway dashboard or run 'railway status' and health checks."

exit 0
