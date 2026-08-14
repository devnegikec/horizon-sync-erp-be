#!/usr/bin/env bash
# =============================================================================
# sync_local_db.sh
# Pull data from Railway Postgres (source of truth) into your local Docker
# Postgres container. No local psql/pg_dump needed — everything runs inside
# the postgres container.
#
# USAGE:
#   ./sync_local_db.sh <database> [--full]
#
#     <database> : local DB name to restore into   (default: railway)
#     --full     : full schema+data replace (drop/recreate objects)
#                  DEFAULT is data-only refresh (schema comes from Alembic)
#
# ENV VARS (preferred: put them in .sync.env next to this script):
#   SOURCE_DATABASE_URL   Railway Postgres URL. Get it from Railway dashboard
#                         -> Postgres -> Connect -> "Public Network" connection
#                         string. (If Railway CLI is installed and this is unset,
#                         a `railway connect` tunnel is used automatically.)
#   LOCAL_DB_USER         default: horizon_user
#   LOCAL_DB_PASSWORD     default: horizon_pass
#   LOCAL_DB_PORT         default: 5432
#   LOCAL_CONTAINER       default: horizon_postgres
#   RAILWAY_SERVICE       default: Postgres   (Railway plugin service name)
# =============================================================================
set -euo pipefail

# Prevent Git Bash (MSYS) from rewriting container paths like /tmp/foo.dump
# into Windows paths (C:/Users/.../Temp/foo.dump) when invoking docker.exe.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL="*"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.sync.env"

# ---------- 0. Load .sync.env if present (optional, keeps secrets out of shell) ----------
if [[ -f "$ENV_FILE" ]]; then
  echo ">> Loading $ENV_FILE"
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

# ---------- Config ----------
TARGET_DB="${1:-railway}"
MODE="data"                       # data | full
for arg in "$@"; do
  [[ "$arg" == "--full" ]] && MODE="full"
done

LOCAL_DB_USER="${LOCAL_DB_USER:-horizon_user}"
LOCAL_DB_PASSWORD="${LOCAL_DB_PASSWORD:-horizon_pass}"
LOCAL_DB_PORT="${LOCAL_DB_PORT:-5432}"
LOCAL_CONTAINER="${LOCAL_CONTAINER:-horizon_postgres}"
RAILWAY_SERVICE="${RAILWAY_SERVICE:-Postgres}"
DUMP_DIR="${SCRIPT_DIR}/.db_dumps"

# ---------- 1. Verify Docker daemon is up ----------
if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon is not running. Start Docker Desktop, wait for it to"
  echo "       finish booting (whale icon stops animating), then re-run this script."
  exit 1
fi

# ---------- 2. Ensure the local Postgres container is running ----------
if ! docker ps --format '{{.Names}}' | grep -q "^${LOCAL_CONTAINER}$"; then
  echo ">> Local Postgres container '${LOCAL_CONTAINER}' is not running — starting it..."
  cd "$SCRIPT_DIR"
  docker compose up -d postgres
  echo ">> Waiting for Postgres to be healthy..."
  for _ in $(seq 1 30); do
    status="$(docker inspect -f '{{.State.Health.Status}}' "$LOCAL_CONTAINER" 2>/dev/null || echo starting)"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
fi
echo ">> Local Postgres is up."

# ---------- 2b. Ensure the target database exists ----------
db_exists="$(docker exec -i "$LOCAL_CONTAINER" psql -U "$LOCAL_DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" | tr -d '[:space:]')"
if [[ "$db_exists" != "1" ]]; then
  echo ">> Database '${TARGET_DB}' does not exist — creating it..."
  docker exec -i "$LOCAL_CONTAINER" psql -U "$LOCAL_DB_USER" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";"
fi

# ---------- 3. Resolve the source (Railway) URL ----------
SOURCE_URL="${SOURCE_DATABASE_URL:-}"
RAILWAY_PID=""
cleanup() { [[ -n "$RAILWAY_PID" ]] && kill "$RAILWAY_PID" 2>/dev/null || true; }
trap cleanup EXIT

if [[ -z "$SOURCE_URL" ]]; then
  if command -v railway >/dev/null 2>&1; then
    echo ">> Opening Railway tunnel ($RAILWAY_SERVICE)..."
    TUNNEL_LOG="$(mktemp)"
    railway connect "$RAILWAY_SERVICE" >"$TUNNEL_LOG" 2>&1 &
    RAILWAY_PID=$!
    for _ in $(seq 1 30); do
      SOURCE_URL="$(grep -oE 'postgresql://[^ )]+' "$TUNNEL_LOG" | head -1 || true)"
      [[ -n "$SOURCE_URL" ]] && break
      sleep 1
    done
    if [[ -z "$SOURCE_URL" ]]; then
      echo "ERROR: Could not detect tunnel URL. Output was:"
      cat "$TUNNEL_LOG"
      exit 1
    fi
    echo ">> Tunnel URL acquired."
  else
    echo "ERROR: No SOURCE_DATABASE_URL set and Railway CLI not found."
    echo "  Fix: either"
    echo "   1) copy the Public Network URL from Railway dashboard -> Postgres -> Connect"
    echo "      into .sync.env as SOURCE_DATABASE_URL=... , or"
    echo "   2) install the Railway CLI:  npm i -g @railway/cli  (then railway login)"
    exit 1
  fi
fi

# The dump runs INSIDE the postgres container, so a host tunnel on 127.0.0.1
# must be reached via Docker Desktop's host gateway.
CONTAINER_SOURCE_URL="${SOURCE_URL}"
CONTAINER_SOURCE_URL="${CONTAINER_SOURCE_URL//127.0.0.1/host.docker.internal}"
CONTAINER_SOURCE_URL="${CONTAINER_SOURCE_URL//@localhost:/@host.docker.internal:}"

# ---------- 4. Dump from Railway (inside the container) ----------
mkdir -p "$DUMP_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
DUMP_FILE="${DUMP_DIR}/${TARGET_DB}_${STAMP}.dump"

# Docker CLI on Windows needs a native path for `docker cp` (D:/...), not the
# MSYS /d/... form, otherwise it mis-parses the leading slash as a drive letter.
if command -v cygpath >/dev/null 2>&1; then
  DUMP_FILE_HOST="$(cygpath -m "$DUMP_FILE")"
else
  DUMP_FILE_HOST="$DUMP_FILE"
fi

if [[ "$MODE" == "full" ]]; then
  echo ">> [FULL] Dumping schema + data from Railway..."
  DUMP_ARGS=(-Fc --no-owner --no-acl)
else
  echo ">> [DATA] Dumping data only from Railway..."
  DUMP_ARGS=(--data-only -Fc --no-owner --no-acl)
fi

docker exec -i "$LOCAL_CONTAINER" \
  pg_dump "${DUMP_ARGS[@]}" \
  -d "$CONTAINER_SOURCE_URL" \
  -f /tmp/railway.dump

echo ">> Copying dump out to $DUMP_FILE"
docker cp "${LOCAL_CONTAINER}:/tmp/railway.dump" "$DUMP_FILE_HOST"
docker exec -i "$LOCAL_CONTAINER" rm -f /tmp/railway.dump

# ---------- 5. Restore into the local database ----------
TARGET_URL="postgresql://${LOCAL_DB_USER}:${LOCAL_DB_PASSWORD}@localhost:${LOCAL_DB_PORT}/${TARGET_DB}"

if [[ "$MODE" == "full" ]]; then
  echo ">> [FULL] Restoring schema + data into $TARGET_DB (drop/recreate objects)..."
  RESTORE_ARGS=(--no-owner --no-acl --clean --if-exists -j 4)
else
  echo ">> [DATA] Restoring data into $TARGET_DB (tables must already exist via Alembic)..."
  RESTORE_ARGS=(--data-only --no-owner --no-acl --disable-triggers -j 4)
fi

# Copy the dump back into the container and restore from it.
docker cp "$DUMP_FILE_HOST" "${LOCAL_CONTAINER}:/tmp/railway.dump"
docker exec -i "$LOCAL_CONTAINER" \
  pg_restore "${RESTORE_ARGS[@]}" \
  -d "$TARGET_URL" \
  /tmp/railway.dump
docker exec -i "$LOCAL_CONTAINER" rm -f /tmp/railway.dump

echo ""
echo "=============================================================="
echo "✅ Sync complete: Railway -> local '$TARGET_DB' ($MODE mode)"
echo "   Dump archived at: $DUMP_FILE"
echo "=============================================================="
