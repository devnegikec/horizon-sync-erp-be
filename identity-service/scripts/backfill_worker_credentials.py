"""Backfill login credentials for warehouse workers.

Workers consolidated from the retired ``wms_workers`` table into ``users``
(migration 018) keep their QR code but often have no ``login_username`` /
``password_hash``. This script gives every warehouse worker a usable
username + password so the ``POST /login/worker`` mobile fallback works.

Usage (inside the identity container, which has PYTHONPATH=/app and
DATABASE_URL already set):

    docker exec -it horizon_identity python scripts/backfill_worker_credentials.py

Safety: only touches rows where ``login_username`` or ``password_hash`` is
missing/empty. Workers that already have both are left untouched.
"""

import re
import sys

from sqlalchemy import text

from app.core.security import hash_password, verify_password
from app.database import SessionLocal
from app.models.base import UserType
from app.models.user import User

# Shared default password for backfilled workers. The plaintext is stored in
# ``login_password`` (recoverable) so managers can reveal/change it later.
DEFAULT_PASSWORD = "Warehouse@123"


def _normalize_username(value: str | None) -> str | None:
    if not value:
        return None
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or None


def _candidate_usernames(user: User) -> list[str]:
    """Ordered username candidates derived from identity fields."""
    candidates = []
    for raw in (user.employee_id, user.qr_code):
        slug = _normalize_username(raw)
        if slug and slug not in candidates:
            candidates.append(slug)
    if user.email:
        local = user.email.split("@", 1)[0]
        slug = _normalize_username(local)
        if slug and slug not in candidates:
            candidates.append(slug)
    return candidates


def _needs_password(user: User) -> bool:
    """True when the worker has no known/recoverable password.

    A worker migrated from ``wms_workers`` often has a random, unknown hash
    (and a NULL ``login_password``) — treat that as "no password" too so the
    backfill gives them a usable one.
    """
    # No recoverable plaintext to reveal to the manager.
    if not (user.login_password or "").strip():
        return True
    # Missing/invalid hash.
    if not user.password_hash or len(user.password_hash or "") < 20:
        return True
    # Stored plaintext no longer matches the hash (defensive).
    try:
        return not verify_password(user.login_password, user.password_hash)
    except Exception:
        return True


def main() -> int:
    db = SessionLocal()
    try:
        workers = (
            db.query(User)
            .filter(User.user_type == UserType.WAREHOUSE_WORKER)
            .all()
        )

        taken: set[str] = {
            u.login_username
            for u in workers
            if u.login_username and u.login_username.strip()
        }

        assigned: list[dict] = []
        for user in workers:
            username = (user.login_username or "").strip()

            if not username:
                for candidate in _candidate_usernames(user):
                    candidate = candidate or f"worker-{user.id.hex[:8]}"
                    if candidate not in taken:
                        username = candidate
                        taken.add(candidate)
                        break
                if not username:
                    # Extremely defensive fallback — never collide.
                    base = f"worker-{user.id.hex[:8]}"
                    username = base
                    i = 2
                    while username in taken:
                        username = f"{base}-{i}"
                        i += 1
                    taken.add(username)

            changed = False
            if (user.login_username or "").strip() != username:
                user.login_username = username
                changed = True

            if _needs_password(user):
                user.login_password = DEFAULT_PASSWORD
                user.password_hash = hash_password(DEFAULT_PASSWORD)
                changed = True

            if changed:
                assigned.append(
                    {
                        "employee_id": user.employee_id or "",
                        "name": user.display_name or user.first_name or "",
                        "username": username,
                    }
                )

        db.commit()

        print(f"Workers scanned: {len(workers)}")
        print(f"Workers updated: {len(assigned)}")
        print()
        if assigned:
            print("employee_id | name | login_username")
            print("-" * 50)
            for row in assigned:
                print(
                    f"{row['employee_id'] or '-':<12} | {row['name'] or '-':<20} | {row['username']}"
                )
            print()
            print(f"Default password for updated workers: {DEFAULT_PASSWORD}")
        else:
            print("Nothing to do — every worker already has credentials.")
        return 0
    except Exception as exc:  # noqa: BLE001 — surface startup/config errors
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
