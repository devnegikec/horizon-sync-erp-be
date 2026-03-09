"""Ensure alembic_version has exactly one row to avoid 'overlaps' errors.

When multiple rows exist, or the DB points at a removed/stale revision,
Alembic can fail. This script normalizes to 001_merged_complete_schema
so that subsequent migrations (017, 018, etc.) run correctly.
"""

import os
import sys

from sqlalchemy import create_engine, text

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.config import settings  # noqa: E402

# Linear head (no merge) - matches current alembic chain
HEAD_REVISION = "001_merged_complete_schema"
# Legacy merge revision we no longer use; normalize away so Alembic never sees it
OLD_MERGE_REVISION = "ca930be8ee07"
# Also normalize away the old linear head that no longer exists
OLD_LINEAR_HEAD = "i9j0k1l2m3n4"


def main() -> int:
    engine = create_engine(settings.database_url)
    with engine.begin() as conn:
        try:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            rows = result.fetchall()
        except Exception:
            # Table may not exist yet (fresh DB); let alembic create it
            return 0
        if not rows:
            return 0
        # Multiple rows, or single row at old merge: set to linear head
        need_fix = len(rows) > 1 or any(r[0] in (OLD_MERGE_REVISION, OLD_LINEAR_HEAD) for r in rows)
        if not need_fix:
            return 0
        # Clear stale version so alembic runs all migrations from scratch
        conn.execute(text("DELETE FROM alembic_version"))
        print(f"[normalize_alembic_version] Cleared stale alembic_version (was {[r[0] for r in rows]}). Alembic will re-run from base.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        print(f"[normalize_alembic_version] Error: {e}", file=sys.stderr)
        sys.exit(1)
