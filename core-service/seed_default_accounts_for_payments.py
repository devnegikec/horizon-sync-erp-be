"""Seed default account mappings required for payment confirmation.

Configures:
- Cash (account 1110) as default for transaction_type 'cash'
- Accounts Receivable (account 1120) as default for transaction_type 'accounts_receivable'

These are required when confirming customer payments (journal posting).

Prerequisites:
- Chart of accounts must be seeded first (python seed_chart_of_accounts.py)

Usage:
    python seed_default_accounts_for_payments.py
"""

import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
)
# Same as seed_chart_of_accounts.py; override with ORGANIZATION_ID env if needed
ORG_ID = uuid.UUID(os.getenv("ORGANIZATION_ID", "b1f71de1-0a19-424e-9580-1d3f871c5b1f"))

# Account codes from seed_chart_of_accounts.py
CASH_ACCOUNT_CODE = "1110"  # Cash and Cash Equivalents
AR_ACCOUNT_CODE = "1120"  # Accounts Receivable


def seed_default_accounts():
    """Insert or update default account mappings for payment confirmation."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    with Session() as session:
        try:
            print("=" * 70)
            print("Default Accounts for Payments – Seeding")
            print("=" * 70)
            print(f"\nOrganization ID: {ORG_ID}")
            print("Mapping: cash → 1110, accounts_receivable → 1120\n")

            # Resolve account IDs by code
            result = session.execute(
                text("""
                    SELECT account_code, id FROM accounts
                    WHERE organization_id = :org_id
                    AND account_code IN (:code_cash, :code_ar)
                """),
                {
                    "org_id": str(ORG_ID),
                    "code_cash": CASH_ACCOUNT_CODE,
                    "code_ar": AR_ACCOUNT_CODE,
                },
            )
            rows = {row.account_code: row.id for row in result}

            if CASH_ACCOUNT_CODE not in rows:
                raise RuntimeError(
                    f"Account {CASH_ACCOUNT_CODE} (Cash) not found. Run seed_chart_of_accounts.py first."
                )
            if AR_ACCOUNT_CODE not in rows:
                raise RuntimeError(
                    f"Account {AR_ACCOUNT_CODE} (Accounts Receivable) not found. Run seed_chart_of_accounts.py first."
                )

            cash_id = str(rows[CASH_ACCOUNT_CODE])
            ar_id = str(rows[AR_ACCOUNT_CODE])
            now = datetime.now(UTC)
            org_str = str(ORG_ID)

            # Set default_accounts (scenario = NULL for payment defaults).
            # IMPORTANT: Only create mappings if they don't exist.
            # Do NOT update existing mappings to avoid breaking user configurations.
            for transaction_type, account_id, label in [
                ("cash", cash_id, "Cash"),
                ("accounts_receivable", ar_id, "Accounts Receivable"),
            ]:
                existing = session.execute(
                    text("""
                        SELECT id, account_id FROM default_accounts
                        WHERE organization_id = :org_id
                          AND transaction_type = :transaction_type
                          AND scenario IS NULL
                    """),
                    {"org_id": org_str, "transaction_type": transaction_type},
                ).fetchone()

                if existing:
                    # Mapping already exists - skip to avoid overwriting user configuration
                    print(f"  ⊘ {label} → {transaction_type} (already exists, skipped)")
                else:
                    session.execute(
                        text("""
                            INSERT INTO default_accounts (
                                id, organization_id, transaction_type, scenario, account_id,
                                created_at, updated_at
                            ) VALUES (
                                gen_random_uuid(), :org_id, :transaction_type, NULL, :account_id,
                                :now, :now
                            )
                        """),
                        {
                            "org_id": org_str,
                            "transaction_type": transaction_type,
                            "account_id": account_id,
                            "now": now,
                        },
                    )
                    print(f"  ✓ {label} → {transaction_type} (created)")

            session.commit()
            print("\n✓ Default accounts for payments configured successfully.")
            print(
                "  You can now confirm customer payments (POST .../payments/{id}/confirm)."
            )
            print("=" * 70)

        except Exception as e:
            session.rollback()
            print(f"\n✗ Error: {e}")
            raise


if __name__ == "__main__":
    seed_default_accounts()
