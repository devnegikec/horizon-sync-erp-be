"""Merge the duplicate "Mother Warehouse" rows (dry-run by default).

Findings from the live DB:

    'Mother Warehouse'  WH-2026-00001  id=f43d9a79-...  (STUB: 3 locations, 6 users, 0 stock)
    'Mother warehouse ' WH-2026-00002  id=8bc22a62-...  (CANONICAL: 1668 locations, stock/activity)

The stub is referenced only by 3 warehouse_locations and 6 warehouse_users —
no stock, slips, or put-away activity. The canonical warehouse already has its
own HOLD / QUARANTINE / RECEIVING-STAGE bins, and the stub's 3 locations are
empty, so they are soft-deactivated (not repointed) to avoid duplicate special
bins. The 6 user rows are repointed to the canonical warehouse, the trailing-
space name is trimmed, and the stub is soft-deactivated.

Usage (venv active):
    python merge_duplicate_warehouses.py              # dry-run (no writes)
    python merge_duplicate_warehouses.py --apply      # perform the merge

Note: a remaining CODE collision (WH-2026-00002 shared between 'ECity
Bangalore' and the canonical Mother warehouse) is only reported — it is not
auto-fixed because choosing a new code needs a human decision.
"""

from __future__ import annotations

import argparse
import os
import sys

import dotenv
from sqlalchemy import create_engine, text

STUB_ID = "f43d9a79-2ea5-4246-a732-a9f3f76cdc79"        # 'Mother Warehouse'
CANONICAL_ID = "8bc22a62-9e7a-4839-8f39-e58f6087d25e"    # 'Mother warehouse '
CANONICAL_NAME = "Mother Warehouse"

ENV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "core-service", ".env"
)


def _engine():
    if os.path.exists(ENV_PATH):
        dotenv.load_dotenv(ENV_PATH)
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL not set and core-service/.env not found")
    return create_engine(url)


def _plan(engine):
    with engine.connect() as c:
        locs = c.execute(
            text(
                "SELECT id, code, full_path, is_active "
                "FROM warehouse_locations WHERE warehouse_id = :s"
            ),
            {"s": STUB_ID},
        ).all()

        users = c.execute(
            text(
                "SELECT id, user_id, role, is_primary, is_active "
                "FROM warehouse_users WHERE warehouse_id = :s"
            ),
            {"s": STUB_ID},
        ).all()

        canonical_user_ids = {
            r[0]
            for r in c.execute(
                text("SELECT user_id FROM warehouse_users WHERE warehouse_id = :c"),
                {"c": CANONICAL_ID},
            ).all()
        }

        code_collisions = c.execute(
            text(
                """
                SELECT code, COUNT(*) AS n
                FROM warehouses_extended
                WHERE is_active IS TRUE
                GROUP BY code HAVING COUNT(*) > 1
                ORDER BY code
                """
            )
        ).all()

    return {
        "locations": locs,
        "users": users,
        "canonical_user_ids": canonical_user_ids,
        "code_collisions": code_collisions,
    }


def report(plan) -> None:
    print("=== Merge plan: stub -> canonical ===")
    print(f"  STUB      : {STUB_ID} ('Mother Warehouse')")
    print(f"  CANONICAL : {CANONICAL_ID} ('Mother warehouse ') -> renamed to {CANONICAL_NAME!r}")
    print()
    print(f"  warehouse_locations to deactivate : {len(plan['locations'])}")
    for r in plan["locations"]:
        print(f"    {r[0]} code={r[1]} path={r[2]!r} active={r[3]}")
    print()
    print(f"  warehouse_users to move         : {len(plan['users'])}")
    for r in plan["users"]:
        already = r[1] in plan["canonical_user_ids"]
        action = "DEACTIVATE (user already in canonical)" if already else "REPOINT"
        print(f"    {r[0]} user={r[1]} role={r[2]} primary={r[3]} active={r[4]} -> {action}")
    print()
    print(f"  canonical name fix              : 'Mother warehouse ' -> 'Mother Warehouse'")
    print("  stub action                     : is_active = false")
    print()
    print("=== Remaining active-warehouse CODE collisions (NOT auto-fixed) ===")
    if not plan["code_collisions"]:
        print("  (none)")
    for r in plan["code_collisions"]:
        print(f"  code {r[0]}: {r[1]} active warehouses share this code")


def apply_merge(engine) -> None:
    plan = _plan(engine)
    with engine.begin() as c:
        # 1. Soft-deactivate the stub's empty special locations (HOLD,
        #    QUARANTINE, RECEIVING-STAGE) — the canonical already has its own.
        c.execute(
            text("UPDATE warehouse_locations SET is_active = false WHERE warehouse_id = :s"),
            {"s": STUB_ID},
        )

        # 2. Repoint users; deactivate rows whose user already exists on the
        #    canonical warehouse to avoid duplicate assignments.
        for user_row in plan["users"]:
            user_id, row_id = user_row[1], user_row[0]
            if user_id in plan["canonical_user_ids"]:
                c.execute(
                    text("UPDATE warehouse_users SET is_active = false WHERE id = :id"),
                    {"id": row_id},
                )
            else:
                c.execute(
                    text("UPDATE warehouse_users SET warehouse_id = :c WHERE id = :id"),
                    {"c": CANONICAL_ID, "id": row_id},
                )

        # 3. Fix trailing-space name.
        c.execute(
            text("UPDATE warehouses_extended SET name = :n WHERE id = :c"),
            {"n": CANONICAL_NAME, "c": CANONICAL_ID},
        )

        # 4. Soft-deactivate the stub.
        c.execute(
            text("UPDATE warehouses_extended SET is_active = false WHERE id = :s"),
            {"s": STUB_ID},
        )

    print(f"Merged stub {STUB_ID} into canonical {CANONICAL_ID}.")
    print(f"Deactivated {len(plan['locations'])} empty stub locations and moved {len(plan['users'])} user rows.")
    print(f"Renamed canonical to {CANONICAL_NAME!r} and deactivated the stub.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply the merge (default is dry-run).")
    args = parser.parse_args()

    engine = _engine()
    if args.apply:
        apply_merge(engine)
    else:
        report(_plan(engine))


if __name__ == "__main__":
    main()
