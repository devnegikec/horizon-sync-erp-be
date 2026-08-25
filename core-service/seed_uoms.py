"""Seed UOM (Unit of Measure) data"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.models.uom import UOM

DATABASE_URL = settings.database_url
ORG_ID = uuid.UUID("bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150")

UOMS_DATA = [
    # Quantity
    {"name": "Piece", "abbreviation": "PCS", "description": "Individual unit or piece"},
    {"name": "Dozen", "abbreviation": "DOZ", "description": "12 pieces"},
    {"name": "Pair", "abbreviation": "PR", "description": "Set of two"},
    {
        "name": "Set",
        "abbreviation": "SET",
        "description": "Group of items sold together",
    },
    {"name": "Box", "abbreviation": "BOX", "description": "Standard box packaging"},
    {"name": "Carton", "abbreviation": "CTN", "description": "Carton packaging"},
    {"name": "Pack", "abbreviation": "PCK", "description": "Packaged bundle"},
    {"name": "Roll", "abbreviation": "ROL", "description": "Roll of material"},
    {"name": "Sheet", "abbreviation": "SHT", "description": "Flat sheet"},
    {"name": "Bundle", "abbreviation": "BDL", "description": "Bundled items"},
    # Weight
    {"name": "Kilogram", "abbreviation": "KG", "description": "Metric unit of weight"},
    {
        "name": "Gram",
        "abbreviation": "GM",
        "description": "Metric unit of weight (1/1000 kg)",
    },
    {
        "name": "Milligram",
        "abbreviation": "MG",
        "description": "Metric unit of weight (1/1000 g)",
    },
    {"name": "Metric Ton", "abbreviation": "MT", "description": "1000 kilograms"},
    {"name": "Pound", "abbreviation": "LB", "description": "Imperial unit of weight"},
    {
        "name": "Ounce",
        "abbreviation": "OZ",
        "description": "Imperial unit of weight (1/16 lb)",
    },
    # Volume
    {"name": "Liter", "abbreviation": "LTR", "description": "Metric unit of volume"},
    {
        "name": "Milliliter",
        "abbreviation": "ML",
        "description": "Metric unit of volume (1/1000 L)",
    },
    {
        "name": "Cubic Meter",
        "abbreviation": "CBM",
        "description": "Metric unit of volume",
    },
    {"name": "Gallon", "abbreviation": "GAL", "description": "Imperial unit of volume"},
    # Length
    {"name": "Meter", "abbreviation": "MTR", "description": "Metric unit of length"},
    {
        "name": "Centimeter",
        "abbreviation": "CM",
        "description": "Metric unit of length (1/100 m)",
    },
    {
        "name": "Millimeter",
        "abbreviation": "MM",
        "description": "Metric unit of length (1/1000 m)",
    },
    {
        "name": "Kilometer",
        "abbreviation": "KM",
        "description": "Metric unit of length (1000 m)",
    },
    {"name": "Inch", "abbreviation": "IN", "description": "Imperial unit of length"},
    {
        "name": "Foot",
        "abbreviation": "FT",
        "description": "Imperial unit of length (12 inches)",
    },
    {
        "name": "Yard",
        "abbreviation": "YD",
        "description": "Imperial unit of length (3 feet)",
    },
    # Area
    {
        "name": "Square Meter",
        "abbreviation": "SQM",
        "description": "Metric unit of area",
    },
    {
        "name": "Square Foot",
        "abbreviation": "SQF",
        "description": "Imperial unit of area",
    },
    # Time / Service
    {"name": "Hour", "abbreviation": "HR", "description": "Unit of time"},
    {"name": "Day", "abbreviation": "DAY", "description": "Unit of time (24 hours)"},
    {"name": "Month", "abbreviation": "MON", "description": "Unit of time"},
    {"name": "Year", "abbreviation": "YR", "description": "Unit of time (12 months)"},
    # Other
    {"name": "Unit", "abbreviation": "UNIT", "description": "Generic unit"},
    {"name": "Lot", "abbreviation": "LOT", "description": "Batch or lot of items"},
    {"name": "Pallet", "abbreviation": "PLT", "description": "Pallet load"},
    {"name": "Container", "abbreviation": "CNT", "description": "Shipping container"},
    {"name": "Bag", "abbreviation": "BAG", "description": "Bag packaging"},
    {"name": "Drum", "abbreviation": "DRM", "description": "Drum container"},
    {"name": "Bottle", "abbreviation": "BTL", "description": "Bottle packaging"},
]

# abbreviation -> (uom_type, precision)
UOM_TYPE_MAP = {
    # count
    "PCS": ("count", 0), "DOZ": ("count", 0), "PR": ("count", 0),
    "SET": ("count", 0), "BOX": ("count", 0), "CTN": ("count", 0),
    "PCK": ("count", 0), "ROL": ("count", 0), "SHT": ("count", 0),
    "BDL": ("count", 0), "UNIT": ("count", 0), "LOT": ("count", 0),
    "PLT": ("count", 0), "CNT": ("count", 0), "BAG": ("count", 0),
    "DRM": ("count", 0), "BTL": ("count", 0),
    # weight
    "KG": ("weight", 3), "GM": ("weight", 0), "MG": ("weight", 0),
    "MT": ("weight", 3), "LB": ("weight", 2), "OZ": ("weight", 2),
    # volume
    "LTR": ("volume", 2), "ML": ("volume", 0), "CBM": ("volume", 3),
    "GAL": ("volume", 2),
    # length
    "MTR": ("length", 2), "CM": ("length", 1), "MM": ("length", 0),
    "KM": ("length", 2), "IN": ("length", 1), "FT": ("length", 1),
    "YD": ("length", 1),
    # area
    "SQM": ("area", 2), "SQF": ("area", 2),
    # time
    "HR": ("time", 1), "DAY": ("time", 0), "MON": ("time", 0),
    "YR": ("time", 0),
}


def seed_uoms():
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    created = 0
    skipped = 0

    try:
        for uom_data in UOMS_DATA:
            uom_type, precision = UOM_TYPE_MAP.get(uom_data["abbreviation"], (None, 0))

            existing = (
                db.query(UOM)
                .filter(
                    UOM.organization_id == ORG_ID,
                    UOM.abbreviation == uom_data["abbreviation"],
                    UOM.deleted_at.is_(None),
                )
                .first()
            )

            if existing:
                updated = False
                if existing.uom_type is None and uom_type is not None:
                    existing.uom_type = uom_type
                    updated = True
                if getattr(existing, "precision", None) is None and precision:
                    existing.precision = precision
                    updated = True
                if updated:
                    print(f"  update {uom_data['abbreviation']} — set uom_type={uom_type}, precision={precision}")
                else:
                    print(f"  skip  {uom_data['abbreviation']} — already exists")
                skipped += 1
                continue

            uom = UOM(
                id=uuid.uuid4(),
                organization_id=ORG_ID,
                name=uom_data["name"],
                abbreviation=uom_data["abbreviation"],
                uom_type=uom_type,
                precision=precision,
                description=uom_data["description"],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            db.add(uom)
            print(f"  create {uom_data['abbreviation']} — {uom_data['name']}")
            created += 1

        db.commit()
        print(f"\n✓ UOM seed complete — {created} created, {skipped} skipped")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_uoms()
