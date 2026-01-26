"""Fix seed script to use string values instead of enum members

This is a temporary workaround until SQLAlchemy enum handling is fixed.
Run this script to update seed_data.py to use string values.
"""

import re

# Read the seed file
with open("seed_data.py") as f:
    content = f.read()

# Replace enum members with their string values
replacements = [
    # WarehouseType
    (r"WarehouseType\.WAREHOUSE", '"warehouse"'),
    (r"WarehouseType\.STORE", '"store"'),
    (r"WarehouseType\.TRANSIT", '"transit"'),
    (r"WarehouseType\.VIRTUAL", '"virtual"'),
    # ValuationMethod
    (r"ValuationMethod\.FIFO", '"fifo"'),
    (r"ValuationMethod\.LIFO", '"lifo"'),
    (r"ValuationMethod\.MOVING_AVERAGE", '"moving_average"'),
    (r"ValuationMethod\.STANDARD", '"standard"'),
    # ItemType
    (r"ItemType\.STOCK", '"stock"'),
    (r"ItemType\.NON_STOCK", '"non_stock"'),
    (r"ItemType\.SERVICE", '"service"'),
    (r"ItemType\.FIXED_ASSET", '"fixed_asset"'),
    # ItemStatus
    (r"ItemStatus\.ACTIVE", '"active"'),
    (r"ItemStatus\.INACTIVE", '"inactive"'),
    (r"ItemStatus\.DISCONTINUED", '"discontinued"'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

# Write back
with open("seed_data.py", "w") as f:
    f.write(content)

print("✓ Updated seed_data.py to use string enum values")
