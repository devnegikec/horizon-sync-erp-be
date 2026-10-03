"""Simulate the inbound receiving flow without the mobile app.

Given a completed QR block (with master packs enabled), this script:
  1. resolves the block's parent QSeal nodes and their child serial numbers
  2. creates + confirms an ASN for the linked WMS item
  3. starts an inbound scan session linked to the ASN
  4. scans every child serial as a bare serial — the same thing the mobile app
     does after it scans a parent QR and expands its linked child units
  5. ends the session → generates a receiving slip (grouped under each parent)

Usage:
    python3 data-script/receive_block.py --block-id <uuid> [--warehouse-id <uuid>] [--item-id <uuid>]

The item is auto-resolved from the block's QR product when --item-id is omitted.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import UTC, datetime

from qr_helpers import api_get, api_post, login

# Default receiving warehouse (EcityTTK_prestige for the TTK-Prestige org).
DEFAULT_WAREHOUSE_ID = os.environ.get(
    "WAREHOUSE_ID", "f0099ec7-0364-416c-9806-22fe38a4c56c"
)


def find_item_by_qr_product(product_id: str, token: str) -> dict | None:
    """Resolve the WMS item linked to a QR product by paging the item list."""
    page = 1
    while True:
        data = api_get("/items", token, {"page": page, "page_size": 100})
        rows = (data or {}).get("items", [])
        if not rows:
            return None
        for row in rows:
            detail = api_get(f"/items/{row['id']}", token)
            if detail.get("qr_product_id") == product_id:
                return detail
        page += 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-id", required=True, help="Completed QR block UUID")
    parser.add_argument("--warehouse-id", default=DEFAULT_WAREHOUSE_ID)
    parser.add_argument(
        "--item-id", default=None, help="WMS item UUID (auto-resolved when omitted)"
    )
    args = parser.parse_args()

    token = login()

    # 1. Block + product
    block = api_get(f"/qr-products/blocks/{args.block_id}", token)
    if block.get("status") != "completed":
        sys.exit(
            f"[FATAL] Block status is '{block.get('status')}', expected 'completed'"
        )
    product_id = block["product_id"]
    batch = block["batch"]
    print(f"[1/6] Block {block['id']} batch={batch} product={product_id}")

    # 2. Parent QSeal nodes + child serials
    parents = api_get(f"/qseal/blocks/{args.block_id}/parents", token) or {}
    nodes = parents.get("nodes", [])
    child_serials: list[str] = []
    for node in nodes:
        detail = api_get(f"/qseal/parents/{node['id']}/linked-units", token)
        for unit in detail.get("linked_units", []):
            serial = unit.get("serial_number")
            if serial:
                child_serials.append(serial)
    child_serials = list(dict.fromkeys(child_serials))  # de-dupe, preserve order
    print(f"[2/6] Found {len(nodes)} parent(s), {len(child_serials)} child serial(s)")
    if not child_serials:
        sys.exit(
            "[FATAL] No child serials found — is master pack enabled on this block?"
        )

    # 3. Resolve the WMS item
    item = None
    if args.item_id:
        item = api_get(f"/items/{args.item_id}", token)
    else:
        item = find_item_by_qr_product(product_id, token)
    if not item:
        sys.exit("[FATAL] Could not resolve the WMS item — pass --item-id")
    sku = item.get("sku") or item.get("item_code") or "SKU"
    uom = item.get("uom") or "pcs"
    print(f"[3/6] Item {item['item_code']} sku={sku} uom={uom}")

    session_id = None
    try:
        # 4. Create + confirm ASN
        asn_payload = {
            "order_date": datetime.now(UTC).isoformat(),
            "delivery_date": datetime.now(UTC).isoformat(),
            "warehouse_id_to": args.warehouse_id,
            "asn_type": "purchase",
            "items": [
                {
                    "item_id": item["id"],
                    "qty": len(child_serials),
                    "uom": uom,
                    "serial_nos": child_serials,
                }
            ],
        }
        asn = api_post("/asn-orders", token, asn_payload)
        api_post(f"/asn-orders/{asn['id']}/confirm", token, {})
        print(f"[4/6] ASN {asn['asn_order_no']} (id={asn['id']}) created + confirmed")

        # 5. Start scan session + scan every child serial
        session = api_post(
            "/inbound/sessions",
            token,
            {
                "warehouse_id": args.warehouse_id,
                "asn_order_id": asn["id"],
                "dock_location": "DOCK-A",
            },
        )
        session_id = session["id"]
        print(f"[5/6] Scan session {session_id} started")
        for i, serial in enumerate(child_serials, 1):
            # Scan the bare child serial. The decoder resolves it to the WMS item
            # and sets batch_number = child serial, which is what the receiving-slip
            # builder keys on to group children under their QSeal parent and pull
            # the real dispatch batch / dates from QSealParameters.
            api_post(f"/inbound/sessions/{session_id}/scan", token, {"qr_data": serial})
            print(f"    scanned {i}/{len(child_serials)}: {serial}")

        # 6. End session → receiving slip
        slip = api_post(f"/inbound/sessions/{session_id}/end", token, {})
    except Exception as exc:
        print(f"[ERROR] Receiving flow failed: {exc}")
        if session_id is not None:
            try:
                api_post(f"/inbound/sessions/{session_id}/cancel", token, {})
                print(f"[CLEANUP] Cancelled scan session {session_id}")
            except Exception as cancel_exc:
                print(f"[CLEANUP] Could not cancel session {session_id}: {cancel_exc}")
        sys.exit(1)
    print(
        f"[6/6] Receiving slip {slip.get('slip_number')} (id={slip.get('id')}) "
        f"status={slip.get('status')} boxes={slip.get('total_boxes')} items={slip.get('total_items')}"
    )
    print("================ DONE ================")
    for group in slip.get("groups", []):
        print(f"  product={group.get('product_name')}")
        for line in group.get("items", []):
            print(
                f"    sku={line.get('sku')} qty={line.get('quantity')} "
                f"batch={line.get('batch_number')} flag={line.get('flag')}"
            )


if __name__ == "__main__":
    main()
