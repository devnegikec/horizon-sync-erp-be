"""Consolidate workers into users and retire wms_workers.

Revision ID: 018
Revises: 017
Create Date: 2026-08-30

Treats a warehouse worker as a first-class ``users`` row (user_type =
warehouse_worker) with the warehouse-specific fields living on ``users``:
``employee_id``, ``login_username`` (recoverable) and ``login_password``.

Migrates existing ``wms_workers`` rows into ``users`` + ``warehouse_users``,
drops the ``wms_devices.assigned_to_worker_id`` foreign key, and drops the
``wms_workers`` table.
"""

import secrets
import uuid

import sqlalchemy as sa
from sqlalchemy import text

from alembic import op
from app.core.security import hash_password

revision = "018"
down_revision = "017"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c"
        ),
        {"t": table, "c": column},
    ).fetchone()
    return row is not None


def _table_exists(conn, table: str) -> bool:
    return conn.execute(text("SELECT to_regclass(:t)"), {"t": f"public.{table}"}).scalar() is not None


def upgrade():  # noqa: C901 - data migration requires many branches
    conn = op.get_bind()

    # 1. Add worker columns to users
    if not _column_exists(conn, "users", "employee_id"):
        op.add_column("users", sa.Column("employee_id", sa.String(100), nullable=True))
    if not _column_exists(conn, "users", "login_username"):
        op.add_column("users", sa.Column("login_username", sa.String(100), nullable=True))
    if not _column_exists(conn, "users", "login_password"):
        op.add_column("users", sa.Column("login_password", sa.String(255), nullable=True))

    op.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_login_username "
            "ON users (login_username) WHERE login_username IS NOT NULL"
        )
    )

    # 2. Migrate existing wms_workers rows (if the table still exists)
    if _table_exists(conn, "wms_workers"):
        rows = conn.execute(
            text(
                "SELECT id, organization_id, warehouse_id, first_name, last_name, "
                "display_name, email, phone, barcode, employee_id, login_username, "
                "role, status, is_active FROM wms_workers"
            )
        ).fetchall()

        for row in rows:
            (wid, org, wh, fn, ln, dn, email, phone, barcode, eid, lu, role, status, is_active) = row
            # Match an existing user by qr_code (barcode) or email
            user = None
            if barcode:
                user = conn.execute(
                    text("SELECT id FROM users WHERE qr_code=:q"), {"q": barcode}
                ).fetchone()
            if not user and email:
                user = conn.execute(
                    text("SELECT id FROM users WHERE email=:e"), {"e": email}
                ).fetchone()

            if user:
                uid = str(user[0])
                conn.execute(
                    text(
                        "UPDATE users SET "
                        "employee_id = COALESCE(employee_id, :eid), "
                        "login_username = COALESCE(login_username, :lu), "
                        "qr_code = COALESCE(qr_code, :q), "
                        "is_active = :ia, "
                        "updated_at = NOW() "
                        "WHERE id = :uid"
                    ),
                    {"eid": eid, "lu": lu, "q": barcode, "ia": bool(is_active), "uid": uid},
                )
            else:
                # Create a user for this worker (random placeholder password;
                # workers log in via QR or a managed username/password)
                em = email or f"{barcode or wid}@warehouse.horizonsync.com"
                if conn.execute(text("SELECT 1 FROM users WHERE email=:e"), {"e": em}).fetchone():
                    em = f"{barcode or wid}.{str(wid)[:8]}@warehouse.horizonsync.com"
                uid = str(uuid.uuid4())
                pw = hash_password(secrets.token_urlsafe(16))
                conn.execute(
                    text(
                        "INSERT INTO users (id, email, password_hash, first_name, last_name, "
                        "display_name, phone, user_type, status, is_active, email_verified, "
                        "qr_code, employee_id, login_username, preferences, timezone, language, "
                        "created_at, updated_at) "
                        "VALUES (:id,:em,:pw,:fn,:ln,:dn,:ph,'warehouse_worker','active',:ia,"
                        "true,:q,:eid,:lu,'{}','UTC','en',NOW(),NOW())"
                    ),
                    {
                        "id": uid,
                        "em": em,
                        "pw": pw,
                        "fn": fn or "Worker",
                        "ln": ln or (barcode or str(wid)[:8]),
                        "dn": dn or f"{fn} {ln}",
                        "ph": phone or "",
                        "ia": bool(is_active),
                        "q": barcode,
                        "eid": eid,
                        "lu": lu,
                    },
                )

            # Ensure warehouse assignment
            if wh:
                wh_role = "operator"
                if role in ("warehouse_supervisor", "supervisor"):
                    wh_role = "supervisor"
                elif role == "manager":
                    wh_role = "manager"
                exists = conn.execute(
                    text("SELECT 1 FROM warehouse_users WHERE user_id=:u AND warehouse_id=:w"),
                    {"u": uid, "w": str(wh)},
                ).fetchone()
                if not exists:
                    conn.execute(
                        text(
                            "INSERT INTO warehouse_users (id, organization_id, user_id, "
                            "warehouse_id, role, is_primary, is_active, created_at, updated_at) "
                            "VALUES (:id,:org,:u,:w,:r,false,true,NOW(),NOW())"
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "org": str(org) if org else None,
                            "u": uid,
                            "w": str(wh),
                            "r": wh_role,
                        },
                    )

    # 3. Drop the wms_devices FK to wms_workers (keep the column as a plain UUID)
    if _table_exists(conn, "wms_devices"):
        fk = conn.execute(
            text(
                "SELECT constraint_name FROM information_schema.table_constraints "
                "WHERE table_name='wms_devices' AND constraint_type='FOREIGN KEY' "
                "AND constraint_name LIKE '%assigned_to_worker%'"
            )
        ).fetchone()
        if fk:
            op.execute(
                text(f'ALTER TABLE wms_devices DROP CONSTRAINT IF EXISTS "{fk[0]}"')
            )

    # 4. Drop wms_workers
    if _table_exists(conn, "wms_workers"):
        op.execute(text("DROP TABLE wms_workers"))


def downgrade():
    # Recreating the retired wms_workers table is not supported.
    pass
