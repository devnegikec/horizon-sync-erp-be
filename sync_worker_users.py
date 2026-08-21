"""
Idempotent sync: keep identity `users` (auth) and core `warehouse_users` (access)
in line with `wms_workers` (source of truth for worker QR codes).

Background:
- Mobile QR login matches `users.qr_code`.
- Warehouse visibility (`/warehouse-users/my-warehouses`) matches `warehouse_users`.
- `wms_workers.barcode` is what the admin prints on the worker QR.
When a worker exists in `wms_workers` but not in `users`/`warehouse_users`,
scanning their QR either fails ("Invalid QR code") or logs in with no warehouses.

Run:  ../.venv/Scripts/python.exe sync_worker_users.py
"""
import secrets
import uuid

import bcrypt
import psycopg2

DB = "postgresql://horizon_user:horizon_pass@localhost:5432/railway"

# Valid, non-reserved domain — `.local` is rejected by Pydantic EmailStr.
FALLBACK_EMAIL_DOMAIN = "warehouse.horizonsync.com"


def _role_for(worker_role: str | None) -> str:
    if worker_role in ("warehouse_supervisor", "supervisor"):
        return "supervisor"
    if worker_role == "manager":
        return "manager"
    return "operator"


def main() -> None:
    conn = psycopg2.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT id, organization_id, warehouse_id, first_name, last_name,
                   display_name, email, barcode, phone, role
            FROM wms_workers
            WHERE is_active = true AND barcode IS NOT NULL
            ORDER BY created_at
            """
        )
        workers = cur.fetchall()

        cur.execute(
            """
            SELECT organization_id, id
            FROM roles
            WHERE code = 'warehouse_work_user' AND is_active = true
            """
        )
        role_by_org = {r[0]: r[1] for r in cur.fetchall()}

        created = fixed_emails = assigned_wh = 0
        for (wid, org, wh_id, fn, ln, dn, email, barcode, phone,
             worker_role) in workers:
            # --- 1. Ensure users row exists (auth) ---
            cur.execute(
                "SELECT id, email FROM users WHERE qr_code = %s", (barcode,)
            )
            user_row = cur.fetchone()

            if not user_row:
                email = email or f"{barcode}@{FALLBACK_EMAIL_DOMAIN}"
                cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
                if cur.fetchone():
                    print(f"SKIP {barcode}: email {email} already exists")
                    continue
                password_hash = bcrypt.hashpw(
                    secrets.token_urlsafe(16).encode(), bcrypt.gensalt()
                ).decode()
                fn = fn or "Worker"
                ln = ln or barcode
                dn = dn or f"{fn} {ln}"
                uid = str(uuid.uuid4())
                cur.execute(
                    """
                    INSERT INTO users
                        (id, email, password_hash, first_name, last_name,
                         display_name, phone, user_type, status, is_active,
                         email_verified, qr_code, preferences, timezone, language,
                         created_at, updated_at)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, 'warehouse_worker', 'active',
                         true, true, %s, '{}', 'UTC', 'en', NOW(), NOW())
                    """,
                    (uid, email, password_hash, fn, ln, dn, phone, barcode),
                )
                created += 1
                print(f"CREATED user for {barcode} -> {email}")
            else:
                uid, existing_email = user_row
                if existing_email and existing_email.endswith("@warehouse.local"):
                    fixed = f"{barcode}@{FALLBACK_EMAIL_DOMAIN}"
                    cur.execute(
                        "SELECT 1 FROM users WHERE email = %s AND id != %s",
                        (fixed, uid),
                    )
                    if not cur.fetchone():
                        cur.execute(
                            "UPDATE users SET email = %s WHERE id = %s",
                            (fixed, uid),
                        )
                        fixed_emails += 1
                        print(f"FIXED email for {barcode} -> {fixed}")

            # --- 2. Ensure org role assignment (auth) ---
            role_id = role_by_org.get(org)
            if role_id:
                cur.execute(
                    """
                    SELECT 1 FROM user_organization_roles
                    WHERE user_id = %s AND organization_id = %s AND role_id = %s
                    """,
                    (uid, org, role_id),
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO user_organization_roles
                            (id, user_id, organization_id, role_id, is_primary,
                             is_active, status, created_at, updated_at)
                        VALUES
                            (%s, %s, %s, %s, true, true, 'active', NOW(), NOW())
                        """,
                        (str(uuid.uuid4()), uid, org, role_id),
                    )
            else:
                print(f"WARN {barcode}: no warehouse_work_user role for org {org}")

            # --- 3. Ensure warehouse assignment (core access) ---
            if wh_id:
                cur.execute(
                    """
                    SELECT 1 FROM warehouse_users
                    WHERE user_id = %s AND warehouse_id = %s
                    """,
                    (uid, wh_id),
                )
                if not cur.fetchone():
                    cur.execute(
                        """
                        INSERT INTO warehouse_users
                            (id, organization_id, user_id, warehouse_id, role,
                             is_primary, is_active, created_at, updated_at)
                        VALUES
                            (%s, %s, %s, %s, %s, false, true, NOW(), NOW())
                        """,
                        (str(uuid.uuid4()), org, uid, wh_id,
                         _role_for(worker_role)),
                    )
                    assigned_wh += 1
                    print(
                        f"ASSIGNED warehouse for {barcode} "
                        f"(role={_role_for(worker_role)})"
                    )

        conn.commit()
        print(
            f"\nDone. created_users={created}, fixed_emails={fixed_emails}, "
            f"warehouse_assignments={assigned_wh}"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
