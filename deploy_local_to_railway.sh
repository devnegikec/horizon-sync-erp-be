#!/usr/bin/env bash
# Deploy local code to Railway for the Horizon Sync project.
#
# Runs `railway up` from the repo root so railway.toml (config-as-code) is used.
# Each service is built from its own source directory using its own Dockerfile.
#
# Migrations run automatically on deploy via each service's start command
# (see railway.toml):
#   identity-service: `python scripts/normalize_alembic_version.py && alembic upgrade head`
#   core-service:     `alembic upgrade heads`  (plural — core historically had
#                     multiple heads; single head today, e.g. 118_add_case_uom)
# Pass --migrate to explicitly re-trigger migrations after deploy (via redeploy).
#
# What this script does, in order:
#   1. Pre-flight  — Railway CLI present, authenticated, railway.toml found.
#   2. Pre-flight  — prints the git branch/commit being uploaded and warns if
#                    the working tree is dirty (use --require-clean to block).
#   3. Pre-flight  — prints the alembic head(s) per service and warns when a
#                    service that runs `upgrade head` has multiple heads.
#   4. Deploy      — `railway up -d` per service (build + deploy + start).
#   5. Post-flight — waits for the service /health to return 200 and greps the
#                    newest deploy logs for the alembic upgrade lines.
#
# Usage:
#   ./deploy_local_to_railway.sh [service] ["deploy message"] [flags]
#
#   service  : one of identity-service, core-service, qr-worker,
#              search-service, nginx-gateway — or "all" to deploy every service.
#              Defaults to identity-service.
#
# Flags:
#   -m, --migrate        After deploy, re-run migrations via `railway redeploy`.
#       --no-healthcheck Skip the post-deploy /health poll.
#       --timeout <secs> Health poll timeout (default 900).
#       --require-clean  Abort if the git working tree is dirty.
#       --dry-run        Print the railway commands without executing them.
#   -y, --yes            Pass `-y` to `railway up` (skip CLI prompts).
#   -h, --help           Show this help.
#
# Env overrides:
#   RAILWAY_PROJECT_ID    Railway project ID (default below)
#   RAILWAY_ENVIRONMENT   Railway environment (default: production)
#   RAILWAY_TOKEN         Non-interactive auth token (skips `railway login`)
#   HEALTH_TIMEOUT        Seconds to wait for /health (default 900)
#   LOG_LINES             Deploy-log lines to scan for migration output (300)
#   CORE_SERVICE_HEALTH_URL / IDENTITY_SERVICE_HEALTH_URL
#                         Override the /health probe URLs.
#
# Examples:
#   ./deploy_local_to_railway.sh core-service "warehouse user review fixes"
#   ./deploy_local_to_railway.sh core-service "fix" --migrate
#   ./deploy_local_to_railway.sh all "release" --require-clean
#   RAILWAY_TOKEN=xxx ./deploy_local_to_railway.sh core-service "ci deploy" -y

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PROJECT_ID="${RAILWAY_PROJECT_ID:-7abe5082-844c-4791-8158-f47e14fb68cb}"
ENVIRONMENT="${RAILWAY_ENVIRONMENT:-production}"

MIGRATE=0
HEALTH=1
DRY_RUN=0
ASSUME_YES=0
REQUIRE_CLEAN="${REQUIRE_CLEAN:-0}"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-900}"
LOG_LINES="${LOG_LINES:-1500}"

ALL_SERVICES=(identity-service core-service qr-worker search-service nginx-gateway)

usage() {
  cat <<EOF
Usage: $0 [service] ["deploy message"] [flags]

Services: ${ALL_SERVICES[*]}   (or "all" for every service)
Default service: identity-service

Flags:
  -m, --migrate        After deploy, re-run the service migrations (via redeploy).
      --no-healthcheck Skip the post-deploy /health poll.
      --timeout <secs> Health poll timeout in seconds (default $HEALTH_TIMEOUT).
      --require-clean  Abort when the git working tree has uncommitted changes.
      --dry-run        Print the railway commands without executing them.
  -y, --yes            Pass -y to 'railway up' (skip CLI prompts).
  -h, --help           Show this help.

Env overrides:
  RAILWAY_PROJECT_ID   (default: $PROJECT_ID)
  RAILWAY_ENVIRONMENT  (default: $ENVIRONMENT)
  RAILWAY_TOKEN        Non-interactive auth token (skips 'railway login')
  HEALTH_TIMEOUT       (default: $HEALTH_TIMEOUT)
  LOG_LINES            (default: $LOG_LINES)
EOF
}

positional=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --migrate|-m) MIGRATE=1; shift ;;
    --no-healthcheck|--no-health) HEALTH=0; shift ;;
    --timeout) HEALTH_TIMEOUT="${2:-}"; [[ -n "$HEALTH_TIMEOUT" ]] || { echo "ERROR: --timeout needs a value"; exit 1; }; shift 2 ;;
    --require-clean) REQUIRE_CLEAN=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "ERROR: Unknown flag '$1'"; usage; exit 1 ;;
    *) positional+=("$1"); shift ;;
  esac
done

SERVICE="${positional[0]:-identity-service}"
MESSAGE="${positional[1]:-deploy from local}"

section() {
  echo ""
  echo "──────────────────────────────────────────────"
  echo "$1"
  echo "──────────────────────────────────────────────"
}

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] $*"
  else
    "$@"
  fi
}

# Service names that actually exist in the Railway project (empty when the
# project cannot be queried, e.g. offline — then the static list is trusted).
existing_services() {
  railway status --json -p "$PROJECT_ID" -e "$ENVIRONMENT" 2>/dev/null | python3 -c '
import json, sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for env in data.get("environments", {}).get("edges", []):
    for si in env["node"].get("serviceInstances", {}).get("edges", []):
        name = si["node"].get("serviceName")
        if name:
            print(name)
' 2>/dev/null || true
}

service_exists() {
  local svc="$1"
  if [[ -z "${EXISTING_SERVICES:-}" ]]; then
    return 0
  fi
  echo "$EXISTING_SERVICES" | grep -qx "$svc"
}

# "<deployment-id> <status>" for the service's newest deployment.
deployment_state() {
  local svc="$1"
  railway status --json -p "$PROJECT_ID" -e "$ENVIRONMENT" 2>/dev/null | python3 -c '
import json
import sys

svc = sys.argv[1]
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for env in data.get("environments", {}).get("edges", []):
    for si in env["node"].get("serviceInstances", {}).get("edges", []):
        node = si["node"]
        if node.get("serviceName") == svc:
            ld = node.get("latestDeployment") or {}
            print(str(ld.get("id", "")) + " " + str(ld.get("status", "")))
            sys.exit(0)
' "$svc" 2>/dev/null || true
}

# ---------------------------------------------------------------- pre-flight 1
preflight_cli() {
  section "1/5  Pre-flight: Railway CLI"
  if ! command -v railway >/dev/null 2>&1; then
    echo "ERROR: Railway CLI not found. Install: npm i -g @railway/cli"
    exit 1
  fi
  echo "$(railway --version 2>/dev/null | head -1)"
  echo "project: $PROJECT_ID   environment: $ENVIRONMENT"
}

# ---------------------------------------------------------------- pre-flight 2
ensure_auth() {
  section "2/5  Pre-flight: authentication"
  if [[ -n "${RAILWAY_TOKEN:-}" ]]; then
    echo "RAILWAY_TOKEN detected — skipping interactive login."
    return 0
  fi
  if railway whoami >/dev/null 2>&1; then
    echo "$(railway whoami 2>/dev/null | head -1)"
    return 0
  fi
  echo "Not signed in to Railway."
  if [[ "${CI:-}" != "" ]]; then
    echo "ERROR: no RAILWAY_TOKEN and CI is set — cannot log in interactively."
    exit 1
  fi
  # Auth does not persist between agent/terminal sessions, so log in here.
  run railway login
  if [[ "$DRY_RUN" -ne 1 ]] && ! railway whoami >/dev/null 2>&1; then
    echo "ERROR: railway login did not complete successfully."
    exit 1
  fi
}

# ---------------------------------------------------------------- pre-flight 3
preflight_repo() {
  section "3/5  Pre-flight: repository state"
  if [[ ! -f "$SCRIPT_DIR/railway.toml" ]]; then
    echo "ERROR: railway.toml not found in $SCRIPT_DIR (config-as-code required)."
    exit 1
  fi
  if command -v git >/dev/null 2>&1 && git rev-parse --git-dir >/dev/null 2>&1; then
    echo "branch: $(git rev-parse --abbrev-ref HEAD)"
    echo "commit: $(git --no-pager log -1 --oneline)"
    local dirty
    dirty="$(git status --porcelain)"
    if [[ -n "$dirty" ]]; then
      echo "WARNING: working tree has uncommitted changes — 'railway up' uploads"
      echo "         the working directory as-is, so uncommitted code WILL ship:"
      echo "$dirty" | head -10 | sed 's/^/           /'
      if [[ "$REQUIRE_CLEAN" -eq 1 ]]; then
        echo "ERROR: --require-clean set and the tree is dirty. Commit or stash first."
        exit 1
      fi
    else
      echo "working tree: clean"
    fi
  else
    echo "WARNING: not a git repository — cannot report branch/commit."
  fi
}

# ---------------------------------------------------------------- pre-flight 4
alembic_heads() {
  local dir="$1"
  [[ -f "$SCRIPT_DIR/$dir/alembic.ini" ]] || return 0
  command -v python3 >/dev/null 2>&1 || { echo "  $dir: python3 not found, skipping head check"; return 0; }
  # Migration modules import `app.*`, so run from the service directory.
  ( cd "$SCRIPT_DIR/$dir" && python3 - <<'PY'
import sys

from alembic.config import Config
from alembic.script import ScriptDirectory

sd = ScriptDirectory.from_config(Config("alembic.ini"))
heads = sd.get_heads()
print(f"  heads: {', '.join(heads)}")
if len(heads) > 1:
    print("  WARNING: multiple heads — a service running 'alembic upgrade head'")
    print("           (singular) will fail; merge the heads first.")
PY
  ) 2>/dev/null || echo "  (alembic not importable locally — skipped)"
}

preflight_migrations() {
  section "4/5  Pre-flight: migrations"
  echo "Migrations run automatically on deploy (startCommand in railway.toml)."
  case "$SERVICE" in
    core-service|all) echo "core-service:"; alembic_heads "core-service" ;;
  esac
  case "$SERVICE" in
    identity-service|all) echo "identity-service:"; alembic_heads "identity-service" ;;
  esac
  echo "(qr-worker/search-service/nginx-gateway have no alembic migrations)"
}

# ------------------------------------------------------------------- deploy
deploy_service() {
  local svc="$1"
  section "5/5  Deploying '$svc' → $PROJECT_ID ($ENVIRONMENT)"
  echo "Message: $MESSAGE"
  local up_args=(up -p "$PROJECT_ID" -s "$svc" -e "$ENVIRONMENT" -m "$MESSAGE" -d)
  if [[ "$ASSUME_YES" -eq 1 ]]; then
    up_args+=(-y)
  fi
  run railway "${up_args[@]}"

  if [[ "$MIGRATE" -eq 1 ]]; then
    echo "Re-triggering migrations for '$svc' ..."
    run railway redeploy \
      -p "$PROJECT_ID" \
      -s "$svc" \
      -e "$ENVIRONMENT" \
      -y \
      || echo "WARNING: redeploy failed; migrations still run automatically on the next deploy."
  fi
}

# ------------------------------------------------------------- post-flight 1
health_url_for() {
  case "$1" in
    identity-service) echo "${IDENTITY_SERVICE_HEALTH_URL:-https://identity-service-production-a1eb.up.railway.app/health}" ;;
    core-service) echo "${CORE_SERVICE_HEALTH_URL:-https://core-service-production-66e9.up.railway.app/health}" ;;
    *) echo "" ;;
  esac
}

# Wait until the *new* deployment of a service reports SUCCESS. Comparing the
# deployment id against the pre-deploy baseline is what makes this a real gate —
# the /health endpoint keeps answering 200 from the previous deployment.
wait_for_deployment() {
  local svc="$1" base_id="$2" deadline state id status
  if [[ -z "$base_id" ]]; then
    echo "  no baseline deployment recorded — skipping the deployment gate."
    return 0
  fi
  echo "  previous deployment: $base_id"
  echo "  waiting for a new deployment to reach SUCCESS (timeout ${HEALTH_TIMEOUT}s) ..."
  deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
  while :; do
    state="$(deployment_state "$svc")"
    id="${state%% *}"
    status="${state##* }"
    if [[ -n "$id" && "$id" != "$base_id" ]]; then
      case "$status" in
        SUCCESS)
          echo "  deployment $id: SUCCESS"
          return 0
          ;;
        FAILED|CRASHED|REMOVED)
          echo "  ERROR: deployment $id finished with status $status."
          echo "         Build/runtime logs: railway logs -b -s $svc -p $PROJECT_ID -e $ENVIRONMENT"
          return 1
          ;;
        *)
          echo "  deployment $id: ${status:-pending} ..."
          ;;
      esac
    fi
    if [[ "$(date +%s)" -ge "$deadline" ]]; then
      echo "  WARNING: no SUCCESS deployment within ${HEALTH_TIMEOUT}s (last status: ${status:-unknown})."
      return 1
    fi
    sleep 15
  done
}

wait_for_health() {
  local svc="$1" url deadline code body
  url="$(health_url_for "$svc")"
  if [[ -z "$url" ]]; then
    echo "  no health URL configured for '$svc' — skipping health check."
    return 0
  fi
  echo "  waiting for $url (timeout ${HEALTH_TIMEOUT}s) ..."
  deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
  while :; do
    code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$url" || true)"
    if [[ "$code" == "200" ]]; then
      body="$(curl -s --max-time 15 "$url" || true)"
      echo "  OK (200): $body"
      return 0
    fi
    if [[ "$(date +%s)" -ge "$deadline" ]]; then
      echo "  WARNING: health check did not return 200 within ${HEALTH_TIMEOUT}s (last: ${code:-no response})."
      echo "           The new build may still be rolling out — check the Railway dashboard."
      return 1
    fi
    sleep 10
  done
}

verify_migrations_in_logs() {
  local svc="$1" lines
  case "$svc" in
    core-service|identity-service) ;;
    *) return 0 ;;
  esac
  lines="$(railway logs -p "$PROJECT_ID" -s "$svc" -e "$ENVIRONMENT" -d -n "$LOG_LINES" 2>&1 \
    | grep -iE "running upgrade|alembic|migrat" | tail -15 || true)"
  if [[ -z "$lines" ]]; then
    echo "  no migration output in the last $LOG_LINES log lines."
    return 0
  fi
  echo "  newest deploy log ($svc) — migration lines:"
  echo "$lines" | sed 's/^/    /'
  if ! echo "$lines" | grep -qi "running upgrade"; then
    echo "    → no 'Running upgrade' line: the database was already at head,"
    echo "      so this deploy applied no pending migrations."
  fi
}
postflight() {
  local svc="$1" base_id="$2"
  section "Post-deploy verification: $svc"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[dry-run] would wait for the new deployment to reach SUCCESS, then check /health and migration logs."
    return 0
  fi
  wait_for_deployment "$svc" "$base_id" || true
  if [[ "$HEALTH" -eq 1 ]]; then
    wait_for_health "$svc" || true
  fi
  verify_migrations_in_logs "$svc" || true
}

# ---------------------------------------------------------------------- main
preflight_cli
ensure_auth
preflight_repo
preflight_migrations

EXISTING_SERVICES="$(existing_services)"
if [[ -n "$EXISTING_SERVICES" ]]; then
  echo "services in project: $(echo "$EXISTING_SERVICES" | tr '\n' ' ')"
else
  echo "WARNING: could not list project services — trusting the static list."
fi

if [[ "$SERVICE" == "all" ]]; then
  target_services=()
  for svc in "${ALL_SERVICES[@]}"; do
    if service_exists "$svc"; then
      target_services+=("$svc")
    else
      echo "Skipping '$svc' — not present in project $PROJECT_ID."
    fi
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
  if ! service_exists "$SERVICE"; then
    echo "ERROR: service '$SERVICE' does not exist in project $PROJECT_ID."
    exit 1
  fi
  target_services=("$SERVICE")
fi

if [[ "${#target_services[@]}" -eq 0 ]]; then
  echo "ERROR: nothing to deploy."
  exit 1
fi

target_svcs=()
target_bases=()
for svc in "${target_services[@]}"; do
  base_state="$(deployment_state "$svc")"
  target_svcs+=("$svc")
  target_bases+=("${base_state%% *}")
  deploy_service "$svc"
done

i=0
while [[ "$i" -lt "${#target_svcs[@]}" ]]; do
  postflight "${target_svcs[$i]}" "${target_bases[$i]}"
  i=$((i + 1))
done

section "Done"
echo "Monitor at https://railway.app/project/$PROJECT_ID/services"
echo "Tip: build logs → railway logs -b -s <service> -p $PROJECT_ID -e $ENVIRONMENT"
