"""Mark all migrations as applied in the alembic_version table."""
import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "core_db")
DB_USER = os.getenv("DB_USER", "horizon_user")
DB_PASS = os.getenv("DB_PASS", "horizon_pass")

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core-service", "alembic", "versions"
)


def main():
    versions = sorted(f[:-3] for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".py"))
    print(f"Found {len(versions)} migrations")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        )
    """)

    inserted = 0
    for v in versions:
        cur.execute(
            "INSERT INTO alembic_version (version_num) VALUES (%s) ON CONFLICT DO NOTHING",
            (v,)
        )
        if cur.rowcount > 0:
            inserted += 1
            print(f"  + {v}")
        else:
            print(f"  – {v} (already present)")

    conn.commit()
    cur.close()
    conn.close()
    print(f"\nDone: {inserted} new versions stamped")


if __name__ == "__main__":
    main()
