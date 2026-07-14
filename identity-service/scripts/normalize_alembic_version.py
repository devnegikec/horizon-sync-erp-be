"""Normalize alembic_version for the identity service.

If the DB contains a revision that no longer has a corresponding migration
file (e.g. '011' was applied then the file was deleted), Alembic will refuse
to run with:

    FAILED: Can't locate revision identified by '011'

This script detects that situation and stamps the DB back to the latest
revision that actually exists on disk, so `alembic upgrade head` can proceed.
"""

import os
import sys

from sqlalchemy import create_engine, text

# Allow `from app.config import settings` when run from /app inside the container
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings  # noqa: E402

# The highest revision file that currently exists on disk.
# Update this whenever a new migration is added.
LATEST_KNOWN_REVISION = "010"

# Any revision IDs that are known to be stale / deleted.
# Add to this list if more orphaned revisions appear in future.
STALE_REVISIONS = {"011"}


def get_known_revisions() -> set[str]:
    """Scan the alembic/versions directory and return all revision IDs."""
    versions_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "alembic",
        "versions",
    )
    known = set()
    if not os.path.isdir(versions_dir):
        return known
    for fname in os.listdir(versions_dir):
        if not fname.endswith(".py") or fname.startswith("__"):
            continue
        fpath = os.path.join(versions_dir, fname)
        with open(fpath) as f:
            for line in f:
                line = line.strip()
                if line.startswith("revision"):
                    # e.g.  revision = "010"  or  revision = '010'
                    rev = line.split("=", 1)[1].strip().strip("\"'")
                    known.add(rev)
                    break
    return known


def main() -> int:
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        # Check if alembic_version table exists at all
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = result.fetchall()
        except Exception:
            # Fresh DB — let Alembic create the table and run from scratch
            print("[normalize_alembic_version] alembic_version table not found — fresh DB, nothing to do.")
            return 0

        if not rows:
            print("[normalize_alembic_version] alembic_version is empty — nothing to do.")
            return 0

        current_versions = {r[0] for r in rows}
        print(f"[normalize_alembic_version] Current alembic_version: {current_versions}")

        known_revisions = get_known_revisions()
        print(f"[normalize_alembic_version] Known revisions on disk: {sorted(known_revisions)}")

        # Find any version in the DB that doesn't exist on disk
        orphaned = current_versions - known_revisions
        if not orphaned:
            print("[normalize_alembic_version] All versions are valid — nothing to do.")
            return 0

        print(f"[normalize_alembic_version] Orphaned revision(s) detected: {orphaned}")
        print(f"[normalize_alembic_version] Stamping DB to latest known revision: {LATEST_KNOWN_REVISION}")

        # Replace whatever is in the table with the latest known good revision
        conn.execute(text("DELETE FROM alembic_version"))
        conn.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:rev)"),
            {"rev": LATEST_KNOWN_REVISION},
        )
        print(f"[normalize_alembic_version] Done. alembic_version is now '{LATEST_KNOWN_REVISION}'.")

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[normalize_alembic_version] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
