import uuid
from datetime import UTC, datetime

import requests
from qr_helpers import login

# API Endpoints
BASE_URL = "http://localhost:8001/api/v1"
# NOTE: batches.item_id is a FK to `items.id`, so we must fetch from /items
# (NOT /qr-products, whose IDs are qr_products.id and violate the FK).
ITEMS_URL = f"{BASE_URL}/items"
BATCHES_URL = f"{BASE_URL}/batches"

BASE_HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "ngrok-skip-browser-warning": "true",
    "Origin": "http://localhost:4200",
}


def get_all_products(page_size=20, headers=None):
    """Fetches all product IDs across paginated pages."""
    headers = headers or BASE_HEADERS
    product_ids = []
    page = 1
    has_next = True

    print("[INFO] Fetching products...")

    while has_next:
        params = {
            "page": page,
            "page_size": page_size,
            "sort_by": "created_at",
            "sort_order": "desc",
        }

        try:
            response = requests.get(ITEMS_URL, headers=headers, params=params)

            if response.status_code == 200:
                res_data = response.json()
                items = res_data.get("items", [])
                page_ids = [p["id"] for p in items if "id" in p]
                product_ids.extend(page_ids)

                print(f"  [PAGE {page}] Fetched {len(page_ids)} products.")

                pagination = res_data.get("pagination", {})
                has_next = pagination.get("has_next", False)
                page += 1
            else:
                print(
                    f"  [ERROR] Failed to fetch page {page}: HTTP {response.status_code} - {response.text}"
                )
                break

        except Exception as e:
            print(f"  [ERROR] Exception on page {page}: {str(e)}")
            break

    print(f"[INFO] Total retrieved product IDs: {len(product_ids)}\n")
    return product_ids


def generate_unique_batch_payload(item_id: str, index: int):
    """Generates a guaranteed unique batch payload for a single product."""
    now = datetime.now(UTC)

    mfg_date = now.strftime("%Y-%m-%dT00:00:00Z")
    try:
        exp = now.replace(year=now.year + 4)
    except ValueError:
        # Feb 29 in a leap year — the target year is not a leap year.
        exp = now.replace(year=now.year + 4, month=2, day=28)
    exp_date = exp.strftime("%Y-%m-%dT00:00:00Z")

    # Format: BATCH-<YYYYMMDD>-P<INDEX>-<UNIQUE_UUID_4CHAR>
    # e.g., BATCH-20260903-P001-A9F2
    unique_suffix = uuid.uuid4().hex[:4].upper()
    batch_no = f"BATCH-{now.strftime('%Y%m%d')}-P{str(index).zfill(3)}-{unique_suffix}"

    return {
        "batch_no": batch_no,
        "item_id": item_id,
        "manufacturing_date": mfg_date,
        "expiry_date": exp_date,
        "supplier_batch_no": None,
        "status": "active",
        "description": f"Unique batch generated for item {item_id}",
    }


def create_one_unique_batch_per_product():
    token = login()
    headers = {**BASE_HEADERS, "Authorization": f"Bearer {token}"}
    product_ids = get_all_products(page_size=20, headers=headers)

    if not product_ids:
        print("[WARN] No product IDs found. Exiting batch creation.")
        return

    total_created = 0
    total_failed = 0

    print("--- Starting Batch Creation (1 Unique Batch per Product) ---\n")

    for prod_idx, item_id in enumerate(product_ids, 1):
        payload = generate_unique_batch_payload(item_id, prod_idx)
        batch_no = payload["batch_no"]

        # Explicit print log for batch_no as requested
        print(
            f"[{prod_idx}/{len(product_ids)}] Preparing batch | Item ID: {item_id} | batch_no: {batch_no}"
        )

        try:
            response = requests.post(BATCHES_URL, headers=headers, json=payload)

            if response.status_code in (200, 201):
                print(f"  └─ SUCCESS: Batch '{batch_no}' created successfully.\n")
                total_created += 1
            else:
                print(f"  └─ FAILED: HTTP {response.status_code} - {response.text}\n")
                total_failed += 1

        except Exception as e:
            print(f"  └─ ERROR: Request failed for batch '{batch_no}': {str(e)}\n")
            total_failed += 1

    print("================ Summary ================")
    print(f"Total Products Processed: {len(product_ids)}")
    print(f"Total Batches Created:    {total_created}")
    print(f"Total Batches Failed:     {total_failed}")


if __name__ == "__main__":
    create_one_unique_batch_per_product()
