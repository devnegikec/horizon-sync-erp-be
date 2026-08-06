"""Stamp all services' alembic_version tables so migrations are skipped."""
import os
import psycopg2

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_USER = os.getenv("DB_USER", "horizon_user")
DB_PASS = os.getenv("DB_PASS", "horizon_pass")

SERVICES = [
    ("core_db", "core-service"),
    ("identity_db", "identity-service"),
]


def stamp_service(db_name, service_dir):
    migrations_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        service_dir, "alembic", "versions"
    )
    if not os.path.isdir(migrations_path):
        print(f"  ! Skipping {service_dir} — migrations dir not found")
        return

    versions = sorted(f[:-3] for f in os.listdir(migrations_path) if f.endswith(".py"))
    if not versions:
        print(f"  ! No migrations found in {service_dir}")
        return

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, dbname=db_name,
        user=DB_USER, password=DB_PASS
    )
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(255) NOT NULL,
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

    conn.commit()
    cur.close()
    conn.close()
    print(f"  + {service_dir}: {inserted}/{len(versions)} versions stamped")


def main():
    print("Stamping alembic_version tables...\n")
    for db_name, service_dir in SERVICES:
        stamp_service(db_name, service_dir)
    print("\nDone. Restart docker compose.")


if __name__ == "__main__":
    main()
