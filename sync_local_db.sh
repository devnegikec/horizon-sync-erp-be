#!/usr/bin/env bash
# =============================================================================
# sync_local_db.sh
# Pull data from Railway Postgres (source of truth) into your local Docker
# Postgres container. No local psql/pg_dump needed — everything runs inside
# the postgres container.
#
# Supports MULTIPLE source databases (core + identity), each defined as a
# named profile in .sync.env:
#
#   CORE_SOURCE_DATABASE_URL=postgresql://...     CORE_TARGET_DB=core_db
#   IDENTITY_SOURCE_DATABASE_URL=postgresql://... IDENTITY_TARGET_DB=identity_db
#
# USAGE:
#   ./sync_local_db.sh <profile> [--full]
#
#     <profile> : core | identity | all     (default: all)
#     --full    : full schema+data replace (drop/recreate objects)
#                 DEFAULT is data-only refresh (schema comes from Alembic)
#
# ENV VARS (preferred: put them in .sync.env next to this script):
#   <PROFILE>_SOURCE_DATABASE_URL   e.g. CORE_SOURCE_DATABASE_URL
#   <PROFILE>_TARGET_DB             optional, default: <profile>_db
#   LOCAL_DB_USER         default: horizon_user
#   LOCAL_DB_PASSWORD     default: horizon_pass
#   LOCAL_DB_PORT         default: 5432
#   LOCAL_CONTAINER       default: horizon_postgres
#   SYNC_PROFILES         profiles synced by `all`   (default: core identity)
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
PROFILE="${1:-all}"               # core | identity | all
MODE="data"                       # data | full
for arg in "$@"; do
  [[ "$arg" == "--full" ]] && MODE="full"
done

LOCAL_DB_USER="${LOCAL_DB_USER:-horizon_user}"
LOCAL_DB_PASSWORD="${LOCAL_DB_PASSWORD:-horizon_pass}"
LOCAL_DB_PORT="${LOCAL_DB_PORT:-5432}"
LOCAL_CONTAINER="${LOCAL_CONTAINER:-horizon_postgres}"
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

# ---------- 3. Resolve profiles to sync ----------
if [[ "$PROFILE" == "all" ]]; then
  # shellcheck disable=SC2206
  PROFILES=(${SYNC_PROFILES:-core identity})
else
  PROFILES=("$PROFILE")
fi

# ---------- 4. Sync a single profile ----------
sync_one() {
  local SOURCE_URL="$1"
  local TARGET_DB="$2"

  # 4a. Ensure the target database exists
  local db_exists
  db_exists="$(docker exec -i "$LOCAL_CONTAINER" psql -U "$LOCAL_DB_USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${TARGET_DB}'" | tr -d '[:space:]')"
  if [[ "$db_exists" != "1" ]]; then
    echo ">> Database '${TARGET_DB}' does not exist — creating it..."
    docker exec -i "$LOCAL_CONTAINER" psql -U "$LOCAL_DB_USER" -d postgres -c "CREATE DATABASE \"${TARGET_DB}\";"
  fi

  # The dump runs INSIDE the postgres container, so a host tunnel on 127.0.0.1
  # must be reached via Docker Desktop's host gateway.
  local CONTAINER_SOURCE_URL="${SOURCE_URL}"
  CONTAINER_SOURCE_URL="${CONTAINER_SOURCE_URL//127.0.0.1/host.docker.internal}"
  CONTAINER_SOURCE_URL="${CONTAINER_SOURCE_URL//@localhost:/@host.docker.internal:}"

  # 4b. Dump from Railway (inside the container)
  mkdir -p "$DUMP_DIR"
  local STAMP DUMP_FILE DUMP_FILE_HOST
  STAMP="$(date +%Y%m%d_%H%M%S)"
  DUMP_FILE="${DUMP_DIR}/${TARGET_DB}_${STAMP}.dump"

  # Docker CLI on Windows needs a native path for `docker cp` (D:/...).
  if command -v cygpath >/dev/null 2>&1; then
    DUMP_FILE_HOST="$(cygpath -m "$DUMP_FILE")"
  else
    DUMP_FILE_HOST="$DUMP_FILE"
  fi

  local DUMP_ARGS RESTORE_ARGS
  if [[ "$MODE" == "full" ]]; then
    echo ">> [FULL] Dumping schema + data for '$TARGET_DB' from Railway..."
    DUMP_ARGS=(-Fc --no-owner --no-acl)
  else
    echo ">> [DATA] Dumping data only for '$TARGET_DB' from Railway..."
    DUMP_ARGS=(--data-only -Fc --no-owner --no-acl)
  fi

  docker exec -i "$LOCAL_CONTAINER" \
    pg_dump "${DUMP_ARGS[@]}" \
    -d "$CONTAINER_SOURCE_URL" \
    -f /tmp/railway.dump

  echo ">> Copying dump out to $DUMP_FILE"
  docker cp "${LOCAL_CONTAINER}:/tmp/railway.dump" "$DUMP_FILE_HOST"
  docker exec -i "$LOCAL_CONTAINER" rm -f /tmp/railway.dump

  # 4c. Restore into the local database
  local TARGET_URL="postgresql://${LOCAL_DB_USER}:${LOCAL_DB_PASSWORD}@localhost:${LOCAL_DB_PORT}/${TARGET_DB}"

  if [[ "$MODE" == "full" ]]; then
    echo ">> [FULL] Restoring schema + data into $TARGET_DB (drop/recreate objects)..."
    RESTORE_ARGS=(--no-owner --no-acl --clean --if-exists -j 4)
  else
    echo ">> [DATA] Restoring data into $TARGET_DB (tables must already exist via Alembic)..."
    RESTORE_ARGS=(--data-only --no-owner --no-acl --disable-triggers -j 4)
  fi

  docker cp "$DUMP_FILE_HOST" "${LOCAL_CONTAINER}:/tmp/railway.dump"
  docker exec -i "$LOCAL_CONTAINER" \
    pg_restore "${RESTORE_ARGS[@]}" \
    -d "$TARGET_URL" \
    /tmp/railway.dump
  docker exec -i "$LOCAL_CONTAINER" rm -f /tmp/railway.dump

  echo "✅ Synced '$TARGET_DB' ($MODE mode). Dump: $DUMP_FILE"
}

# ---------- 5. Run the sync for each profile ----------
for P in "${PROFILES[@]}"; do
  P_UP="$(echo "$P" | tr '[:lower:]' '[:upper:]')"
  SRC_VAR="${P_UP}_SOURCE_DATABASE_URL"
  TGT_VAR="${P_UP}_TARGET_DB"

  SOURCE_URL="${!SRC_VAR:-}"
  if [[ -z "$SOURCE_URL" ]]; then
    echo "ERROR: no source URL for profile '$P'. Set ${SRC_VAR} in .sync.env."
    exit 1
  fi
  TARGET_DB="${!TGT_VAR:-${P}_db}"

  sync_one "$SOURCE_URL" "$TARGET_DB"
done

echo ""
echo "=============================================================="
echo "✅ Sync complete."
echo "=============================================================="
