"""Repository for admin user management.

Uses raw SQL via sqlalchemy.text() for users and user_organization_roles tables
(owned by identity-service but sharing the same database).
"""

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


class AdminUserRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── List with filters and pagination ─────────────────────────────

    def list_users(
        self,
        organization_id: uuid.UUID | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Return paginated list of users with optional filters.

        Joins users → user_organization_roles → organizations to include
        organization_name. Returns (rows_as_dicts, total_count).
        """
        where_clauses: list[str] = ["u.deleted_at IS NULL"]
        params: dict = {}

        if organization_id:
            where_clauses.append("uor.organization_id = :organization_id")
            params["organization_id"] = organization_id

        if search:
            where_clauses.append(
                "(LOWER(u.email) LIKE :search OR LOWER(u.phone) LIKE :search "
                "OR LOWER(u.first_name) LIKE :search OR LOWER(u.last_name) LIKE :search)"
            )
            params["search"] = f"%{search.lower()}%"

        if is_active is not None:
            where_clauses.append("u.is_active = :is_active")
            params["is_active"] = is_active

        where_sql = " AND ".join(where_clauses)

        # Count
        count_row = self.db.execute(
            text(
                f"""
                SELECT COUNT(DISTINCT u.id)::int AS total
                FROM users u
                LEFT JOIN user_organization_roles uor ON uor.user_id = u.id
                WHERE {where_sql}
                """
            ),
            params,
        ).one()
        total = count_row.total

        # Data
        offset = (page - 1) * page_size
        params["limit"] = page_size
        params["offset"] = offset

        rows = self.db.execute(
            text(
                f"""
                SELECT DISTINCT ON (u.id)
                    u.id, u.email, u.first_name, u.last_name, u.phone,
                    u.user_type, u.is_active, u.created_at,
                    uor.organization_id,
                    o.name AS organization_name
                FROM users u
                LEFT JOIN user_organization_roles uor ON uor.user_id = u.id
                LEFT JOIN organizations o ON o.id = uor.organization_id
                WHERE {where_sql}
                ORDER BY u.id, u.created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        ).fetchall()

        users = []
        for row in rows:
            # Fetch roles for this user from user_organization_roles
            role_rows = self.db.execute(
                text(
                    """
                    SELECT r.code FROM user_organization_roles uor
                    JOIN roles r ON r.id = uor.role_id
                    WHERE uor.user_id = :user_id
                    """
                ),
                {"user_id": row.id},
            ).fetchall()
            roles = [r.code for r in role_rows]

            users.append({
                "id": row.id,
                "email": row.email,
                "first_name": row.first_name,
                "last_name": row.last_name,
                "phone": row.phone,
                "roles": roles,
                "user_type": row.user_type if isinstance(row.user_type, str) else row.user_type.value if row.user_type else "user",
                "is_active": row.is_active,
                "organization_id": row.organization_id,
                "organization_name": row.organization_name,
                "created_at": row.created_at,
            })
        return users, total

    # ── Get by ID ────────────────────────────────────────────────────

    def get_by_id(self, user_id: uuid.UUID) -> dict | None:
        """Return full user record with organization name, or None."""
        row = self.db.execute(
            text(
                """
                SELECT u.id, u.email, u.first_name, u.last_name,
                       u.display_name, u.phone, u.user_type,
                       u.is_active, u.created_at, u.updated_at,
                       uor.organization_id,
                       o.name AS organization_name
                FROM users u
                LEFT JOIN user_organization_roles uor ON uor.user_id = u.id
                LEFT JOIN organizations o ON o.id = uor.organization_id
                WHERE u.id = :user_id AND u.deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"user_id": user_id},
        ).first()
        if not row:
            return None

        # Fetch roles
        role_rows = self.db.execute(
            text(
                """
                SELECT r.code FROM user_organization_roles uor
                JOIN roles r ON r.id = uor.role_id
                WHERE uor.user_id = :user_id
                """
            ),
            {"user_id": user_id},
        ).fetchall()
        roles = [r.code for r in role_rows]

        return {
            "id": row.id,
            "email": row.email,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "display_name": row.display_name,
            "phone": row.phone,
            "roles": roles,
            "user_type": row.user_type if isinstance(row.user_type, str) else row.user_type.value if row.user_type else "user",
            "is_active": row.is_active,
            "organization_id": row.organization_id,
            "organization_name": row.organization_name,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }


    # ── Check email uniqueness ───────────────────────────────────────

    def email_exists(self, email: str, exclude_id: uuid.UUID | None = None) -> bool:
        """Return True if a user with this email already exists."""
        sql = "SELECT COUNT(*)::int AS cnt FROM users WHERE LOWER(email) = LOWER(:email) AND deleted_at IS NULL"
        params: dict = {"email": email}
        if exclude_id:
            sql += " AND id != :exclude_id"
            params["exclude_id"] = exclude_id
        row = self.db.execute(text(sql), params).one()
        return row.cnt > 0

    # ── Create ───────────────────────────────────────────────────────

    def create_user(self, data: dict) -> dict:
        """Insert a new user and link to organization. Returns created record."""
        user_id = uuid.uuid4()
        organization_id = data.pop("organization_id")
        roles = data.pop("roles", ["user"])

        self.db.execute(
            text(
                """
                INSERT INTO users (id, email, password_hash, first_name, last_name,
                                   display_name, phone, user_type, is_active,
                                   status, email_verified, created_at, updated_at)
                VALUES (:id, :email, :password_hash, :first_name, :last_name,
                        :display_name, :phone, :user_type, true,
                        'active', false, NOW(), NOW())
                """
            ),
            {
                "id": user_id,
                "email": data["email"],
                "password_hash": data["password_hash"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "display_name": f"{data['first_name']} {data['last_name']}",
                "phone": data.get("phone"),
                "user_type": data.get("user_type", "user"),
            },
        )

        # Link user to organization with roles
        for role_code in roles:
            # Look up role_id by code for this org (or system role)
            role_row = self.db.execute(
                text(
                    """
                    SELECT id FROM roles
                    WHERE code = :code AND (organization_id = :org_id OR is_system = true)
                    LIMIT 1
                    """
                ),
                {"code": role_code, "org_id": organization_id},
            ).first()

            role_id = role_row.id if role_row else None
            if role_id:
                self.db.execute(
                    text(
                        """
                        INSERT INTO user_organization_roles
                            (id, user_id, organization_id, role_id, is_primary, is_active, status, created_at, updated_at)
                        VALUES (:id, :user_id, :org_id, :role_id, true, true, 'active', NOW(), NOW())
                        """
                    ),
                    {
                        "id": uuid.uuid4(),
                        "user_id": user_id,
                        "org_id": organization_id,
                        "role_id": role_id,
                    },
                )

        self.db.flush()
        return self.get_by_id(user_id)  # type: ignore

    # ── Update ───────────────────────────────────────────────────────

    def update_user(self, user_id: uuid.UUID, data: dict) -> dict | None:
        """Partially update a user. Returns updated record."""
        roles = data.pop("roles", None)

        # Update user fields if any remain
        if data:
            set_clauses = [f"{k} = :{k}" for k in data.keys()]
            set_clauses.append("updated_at = NOW()")
            params = {"user_id": user_id, **data}
            self.db.execute(
                text(
                    f"""
                    UPDATE users
                    SET {', '.join(set_clauses)}
                    WHERE id = :user_id AND deleted_at IS NULL
                    """
                ),
                params,
            )

        # Update roles if provided — replace existing role assignments
        if roles is not None:
            # Get user's organization
            org_row = self.db.execute(
                text(
                    """
                    SELECT organization_id FROM user_organization_roles
                    WHERE user_id = :user_id LIMIT 1
                    """
                ),
                {"user_id": user_id},
            ).first()

            if org_row:
                org_id = org_row.organization_id
                # Remove existing role assignments
                self.db.execute(
                    text("DELETE FROM user_organization_roles WHERE user_id = :user_id"),
                    {"user_id": user_id},
                )
                # Insert new role assignments
                for role_code in roles:
                    role_row = self.db.execute(
                        text(
                            """
                            SELECT id FROM roles
                            WHERE code = :code AND (organization_id = :org_id OR is_system = true)
                            LIMIT 1
                            """
                        ),
                        {"code": role_code, "org_id": org_id},
                    ).first()
                    if role_row:
                        self.db.execute(
                            text(
                                """
                                INSERT INTO user_organization_roles
                                    (id, user_id, organization_id, role_id, is_primary, is_active, status, created_at, updated_at)
                                VALUES (:id, :user_id, :org_id, :role_id, true, true, 'active', NOW(), NOW())
                                """
                            ),
                            {
                                "id": uuid.uuid4(),
                                "user_id": user_id,
                                "org_id": org_id,
                                "role_id": role_row.id,
                            },
                        )

        self.db.flush()
        return self.get_by_id(user_id)
