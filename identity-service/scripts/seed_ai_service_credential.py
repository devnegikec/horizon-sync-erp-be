"""Seed script: create the ai-service machine-to-machine credential.

Usage (inside identity-service container or venv):
    python scripts/seed_ai_service_credential.py

This creates a ServiceCredential row for ai-service so it can obtain
JWTs via the client-credentials endpoint.

The generated secret is printed ONCE. Save it in your .env or secrets manager.
"""

import os
import secrets
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, ".")

from app.core.security import hash_password  # bcrypt hash, re-used for secrets
from app.database import Base
from app.models.service_credential import ServiceCredential

# Use env var (set by docker-compose) or fallback to localhost for bare-metal runs
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://horizon_user:horizon_pass@localhost:5432/identity_db",
)

# Permissions granted to ai-service (read-only WMS for Phase 1)
AI_SERVICE_PERMISSIONS = [
    "stock.read",
    "asn_order.read",
    "warehouse.read",
    "user.read",
    "put_away.read",
]


def seed():
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(engine, checkfirst=True)

    with Session(engine) as session:
        existing = (
            session.query(ServiceCredential)
            .filter(ServiceCredential.client_id == "ai-service")
            .first()
        )
        if existing:
            print("ai-service credential already exists. Skipping.")
            return

        raw_secret = "ai-" + secrets.token_urlsafe(32)
        secret_hash = hash_password(raw_secret)

        cred = ServiceCredential(
            client_id="ai-service",
            client_secret_hash=secret_hash,
            service_name="AI Service (MCP, Ingestion, Copilot, Detection)",
            permissions=AI_SERVICE_PERMISSIONS,
            scopes="wms:read",
            is_active=True,
        )
        session.add(cred)
        session.commit()

        print("=" * 60)
        print("ai-service credential created successfully!")
        print("=" * 60)
        print(f"client_id:     ai-service")
        print(f"client_secret: {raw_secret}")
        print(f"permissions:   {AI_SERVICE_PERMISSIONS}")
        print("=" * 60)
        print("IMPORTANT: Save the client_secret now — it cannot be retrieved later.")
        print("=" * 60)


if __name__ == "__main__":
    seed()
