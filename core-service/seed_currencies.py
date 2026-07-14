"""Seed Currency and Exchange Rate data"""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.currency_master import CurrencyMaster
from app.models.exchange_rate import ExchangeRate

DATABASE_URL = "postgresql://horizon_user:horizon_pass@localhost:5432/core_db"
ORG_ID = uuid.UUID("bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150")

CURRENCIES_DATA = [
    {"code": "USD", "name": "US Dollar", "symbol": "$", "is_base_currency": True},
    {"code": "EUR", "name": "Euro", "symbol": "€", "is_base_currency": False},
    {
        "code": "GBP",
        "name": "British Pound Sterling",
        "symbol": "£",
        "is_base_currency": False,
    },
    {"code": "INR", "name": "Indian Rupee", "symbol": "₹", "is_base_currency": False},
    {"code": "AED", "name": "UAE Dirham", "symbol": "د.إ", "is_base_currency": False},
    {"code": "SAR", "name": "Saudi Riyal", "symbol": "﷼", "is_base_currency": False},
    {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "is_base_currency": False},
    {"code": "CNY", "name": "Chinese Yuan", "symbol": "¥", "is_base_currency": False},
    {
        "code": "AUD",
        "name": "Australian Dollar",
        "symbol": "A$",
        "is_base_currency": False,
    },
    {
        "code": "CAD",
        "name": "Canadian Dollar",
        "symbol": "C$",
        "is_base_currency": False,
    },
    {"code": "CHF", "name": "Swiss Franc", "symbol": "Fr", "is_base_currency": False},
    {
        "code": "SGD",
        "name": "Singapore Dollar",
        "symbol": "S$",
        "is_base_currency": False,
    },
    {
        "code": "MYR",
        "name": "Malaysian Ringgit",
        "symbol": "RM",
        "is_base_currency": False,
    },
    {
        "code": "BDT",
        "name": "Bangladeshi Taka",
        "symbol": "৳",
        "is_base_currency": False,
    },
    {
        "code": "PKR",
        "name": "Pakistani Rupee",
        "symbol": "₨",
        "is_base_currency": False,
    },
    {
        "code": "LKR",
        "name": "Sri Lankan Rupee",
        "symbol": "Rs",
        "is_base_currency": False,
    },
    {
        "code": "NPR",
        "name": "Nepalese Rupee",
        "symbol": "Rs",
        "is_base_currency": False,
    },
    {"code": "KWD", "name": "Kuwaiti Dinar", "symbol": "KD", "is_base_currency": False},
    {"code": "QAR", "name": "Qatari Riyal", "symbol": "QR", "is_base_currency": False},
    {"code": "OMR", "name": "Omani Rial", "symbol": "OMR", "is_base_currency": False},
]

# Exchange rates relative to USD as of seed date
# Format: (from_currency, to_currency, rate)
EXCHANGE_RATES_DATA = [
    ("USD", "EUR", 0.921000),
    ("USD", "GBP", 0.789000),
    ("USD", "INR", 83.120000),
    ("USD", "AED", 3.673000),
    ("USD", "SAR", 3.750000),
    ("USD", "JPY", 149.500000),
    ("USD", "CNY", 7.240000),
    ("USD", "AUD", 1.530000),
    ("USD", "CAD", 1.360000),
    ("USD", "CHF", 0.884000),
    ("USD", "SGD", 1.340000),
    ("USD", "MYR", 4.720000),
    ("USD", "BDT", 110.000000),
    ("USD", "PKR", 278.500000),
    ("USD", "LKR", 315.000000),
    ("USD", "NPR", 133.000000),
    ("USD", "KWD", 0.307000),
    ("USD", "QAR", 3.641000),
    ("USD", "OMR", 0.385000),
    # Reverse rates (to USD)
    ("EUR", "USD", 1.086000),
    ("GBP", "USD", 1.267000),
    ("INR", "USD", 0.012030),
    ("AED", "USD", 0.272200),
    ("SAR", "USD", 0.266700),
    ("JPY", "USD", 0.006689),
    ("CNY", "USD", 0.138100),
    ("AUD", "USD", 0.653600),
    ("CAD", "USD", 0.735300),
    ("CHF", "USD", 1.130900),
    ("SGD", "USD", 0.746300),
    ("MYR", "USD", 0.211900),
]


def seed_currencies():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    cur_created = 0
    cur_skipped = 0
    rate_created = 0
    rate_skipped = 0
    effective_date = date.today()

    try:
        # --- Currencies ---
        print("Seeding currencies...")
        for data in CURRENCIES_DATA:
            existing = (
                db.query(CurrencyMaster)
                .filter(
                    CurrencyMaster.organization_id == ORG_ID,
                    CurrencyMaster.code == data["code"],
                    CurrencyMaster.deleted_at.is_(None),
                )
                .first()
            )

            if existing:
                print(f"  skip  {data['code']} — already exists")
                cur_skipped += 1
                continue

            currency = CurrencyMaster(
                id=uuid.uuid4(),
                organization_id=ORG_ID,
                code=data["code"],
                name=data["name"],
                symbol=data["symbol"],
                is_base_currency=data["is_base_currency"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(currency)
            base_tag = " (base)" if data["is_base_currency"] else ""
            print(f"  create {data['code']} — {data['name']}{base_tag}")
            cur_created += 1

        db.flush()

        # --- Exchange Rates ---
        print("\nSeeding exchange rates...")
        for from_cur, to_cur, rate in EXCHANGE_RATES_DATA:
            existing = (
                db.query(ExchangeRate)
                .filter(
                    ExchangeRate.from_currency == from_cur,
                    ExchangeRate.to_currency == to_cur,
                    ExchangeRate.effective_date == effective_date,
                )
                .first()
            )

            if existing:
                print(
                    f"  skip  {from_cur} → {to_cur} on {effective_date} — already exists"
                )
                rate_skipped += 1
                continue

            exchange_rate = ExchangeRate(
                id=uuid.uuid4(),
                organization_id=ORG_ID,
                from_currency=from_cur,
                to_currency=to_cur,
                rate=rate,
                effective_date=effective_date,
                captured_at=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
            db.add(exchange_rate)
            print(f"  create {from_cur} → {to_cur} = {rate}")
            rate_created += 1

        db.commit()
        print(
            f"\n✓ Currency seed complete — {cur_created} currencies created, {cur_skipped} skipped"
        )
        print(
            f"✓ Exchange rate seed complete — {rate_created} rates created, {rate_skipped} skipped"
        )

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_currencies()
