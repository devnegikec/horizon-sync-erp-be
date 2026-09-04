"""Create QR blocks for the N latest items and receive them all under
ONE ASN and ONE receiving slip.

Flow:
  1. (optional) create a QR block per item (qr_image=false, master pack on)
  2. resolve every block's parent QSeal nodes + child serial numbers
  3. build ONE ASN containing every item (one line per item)
  4. start ONE inbound scan session linked to that ASN
  5. scan every child serial as a bare serial (same as the mobile app)
  6. end the session → ONE receiving slip

Usage:
    # create blocks for the latest items + receive everything in one ASN/slip
    python3 data-script/receive_all.py

    # receive EXISTING completed blocks in one ASN/slip (skip creation)
    python3 data-script/receive_all.py --block-ids <uuid1>,<uuid2>,...

Config (env vars, all optional):
    BLOCK_ITEM_COUNT    number of latest items to process   (default 10)
    BLOCK_QUANTITY      units per block                    (default 12)
    MASTER_PACK_SIZE    units per master-pack parent       (default 4)
    BLOCK_POLL_TIMEOUT_S seconds to wait per block         (default 180)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from datetime import UTC, datetime

from qr_helpers import api_get, api_post, login

DEFAULT_WAREHOUSE_ID = os.environ.get(
    "WAREHOUSE_ID", "f0099ec7-0364-416c-9806-22fe38a4c56c"
)
ITEM_COUNT = int(os.environ.get("BLOCK_ITEM_COUNT", "10"))
QUANTITY = int(os.environ.get("BLOCK_QUANTITY", "12"))
MASTER_PACK_SIZE = int(os.environ.get("MASTER_PACK_SIZE", "4"))
QR_TYPE = os.environ.get("QR_TYPE", "dynamic")
POLL_TIMEOUT_S = int(os.environ.get("BLOCK_POLL_TIMEOUT_S", "180"))


def unique_batch(index: int) -> str:
    suffix = uuid.uuid4().hex[:6].upper()
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"BATCH-{stamp}-BLK{index:03d}-{suffix}"


def wait_for_completion(block_id: str, token: str) -> dict:
    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        block = api_get(f"/qr-products/blocks/{block_id}", token)
        status = block.get("status")
        if status == "completed":
            return block
        if status == "failed":
            raise RuntimeError(f"Block {block_id} failed: {block.get('error_message')}")
        print(f"    ... status={status} progress={block.get('progress')}%")
        time.sleep(3)
    raise TimeoutError(f"Block {block_id} did not complete within {POLL_TIMEOUT_S}s")


def find_item_by_qr_product(product_id: str, token: str) -> dict | None:
    """Resolve the WMS item linked to a QR product by paging the item list."""
    page = 1
    while page <= 20:
        data = api_get("/items", token, {"page": page, "page_size": 100})
        rows = (data or {}).get("items", [])
        if not rows:
            return None
        for row in rows:
            detail = api_get(f"/items/{row['id']}", token)
            if detail.get("qr_product_id") == product_id:
                return detail
        page += 1
    return None


def resolve_block_children(block: dict, token: str) -> tuple[dict, list[str]]:
    """Return (item_detail, child_serials) for a completed block."""
    product_id = block["product_id"]
    parents = api_get(f"/qseal/blocks/{block['id']}/parents", token) or {}
    nodes = parents.get("nodes", [])
    child_serials: list[str] = []
    for node in nodes:
        detail = api_get(f"/qseal/parents/{node['id']}/linked-units", token)
        for unit in detail.get("linked_units", []):
            serial = unit.get("serial_number")
            if serial:
                child_serials.append(serial)
    child_serials = list(dict.fromkeys(child_serials))  # de-dupe, preserve order

    item = find_item_by_qr_product(product_id, token)
    if item is None:
        raise RuntimeError(f"No WMS item found for qr_product {product_id}")
    return item, child_serials


def create_block_for_item(qr_product_id: str, index: int, token: str) -> dict:
    payload = {
        "batch": unique_batch(index),
        "quantity": QUANTITY,
        "qr_type": QR_TYPE,
        "qr_image": False,
        "master_pack_enabled": True,
        "master_pack_size": MASTER_PACK_SIZE,
    }
    block = api_post(f"/qr-products/{qr_product_id}/blocks", token, payload)
    block_id = block["id"]
    print(f"    ↳ block {block_id} queued (batch={payload['batch']})")
    return wait_for_completion(block_id, token)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--block-ids",
        default=None,
        help="Comma-separated completed block UUIDs to receive (skips block creation)",
    )
    parser.add_argument("--warehouse-id", default=DEFAULT_WAREHOUSE_ID)
    args = parser.parse_args()

    token = login()

    # ── 1. Get the blocks to receive ─────────────────────────────────────────
    blocks: list[dict] = []
    if args.block_ids:
        for block_id in [b.strip() for b in args.block_ids.split(",") if b.strip()]:
            block = api_get(f"/qr-products/blocks/{block_id}", token)
            if block.get("status") != "completed":
                sys.exit(f"[FATAL] Block {block_id} status='{block.get('status')}'")
            blocks.append(block)
        print(f"[1/5] Using {len(blocks)} existing block(s)")
    else:
        items = api_get(
            "/items",
            token,
            {
                "page": 1,
                "page_size": ITEM_COUNT,
                "sort_by": "created_at",
                "sort_order": "desc",
            },
        )
        item_list = (items or {}).get("items", [])
        print(f"[1/5] Creating blocks for {len(item_list)} latest item(s):\n")
        for idx, item in enumerate(item_list, 1):
            item_id = item["id"]
            try:
                detail = api_get(f"/items/{item_id}", token)
            except RuntimeError as exc:
                print(f"[{idx}/{len(item_list)}] {item_id} — fetch failed: {exc}")
                continue
            qr_product_id = detail.get("qr_product_id")
            print(
                f"[{idx}/{len(item_list)}] {detail.get('item_code')} ({detail.get('item_name')})"
            )
            if not qr_product_id:
                print("    ↳ SKIP: no linked QR product")
                continue
            try:
                block = create_block_for_item(qr_product_id, idx, token)
            except RuntimeError as exc:
                print(f"    ↳ FAILED: {exc}")
                continue
            print(f"    ↳ DONE status={block['status']}")
            blocks.append(block)

    if not blocks:
        sys.exit("[FATAL] No blocks to receive")

    # ── 2. Resolve item + child serials per block, merged by item ────────────
    aggregated: dict[str, dict] = {}  # item_id -> {"item": ..., "serials": [...]}
    total_serials = 0
    print(f"\n[2/5] Resolving parent QR → child serials for {len(blocks)} block(s)")
    for block in blocks:
        item, child_serials = resolve_block_children(block, token)
        bucket = aggregated.setdefault(item["id"], {"item": item, "serials": []})
        bucket["serials"].extend(child_serials)
        bucket["serials"] = list(dict.fromkeys(bucket["serials"]))
        total_serials += len(child_serials)
        print(
            f"    block={block['id']} item={item.get('item_code')} serials={len(child_serials)}"
        )
    print(f"    TOTAL items={len(aggregated)} serials={total_serials}")

    # ── 3. ONE ASN with all items ────────────────────────────────────────────
    asn_items = [
        {
            "item_id": bucket["item"]["id"],
            "qty": len(bucket["serials"]),
            "uom": bucket["item"].get("uom") or "pcs",
            "serial_nos": bucket["serials"],
        }
        for bucket in aggregated.values()
    ]
    asn_payload = {
        "order_date": datetime.now(UTC).isoformat(),
        "delivery_date": datetime.now(UTC).isoformat(),
        "warehouse_id_to": args.warehouse_id,
        "asn_type": "purchase",
        "items": asn_items,
    }
    asn = api_post("/asn-orders", token, asn_payload)
    api_post(f"/asn-orders/{asn['id']}/confirm", token, {})
    print(
        f"[3/5] ONE ASN {asn['asn_order_no']} (id={asn['id']}) with {len(asn_items)} line(s)"
    )

    # ── 4. ONE scan session, scan all children ───────────────────────────────
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
    print(f"[4/5] Scan session {session_id} started")
    all_serials = [
        serial for bucket in aggregated.values() for serial in bucket["serials"]
    ]
    for i, serial in enumerate(all_serials, 1):
        api_post(f"/inbound/sessions/{session_id}/scan", token, {"qr_data": serial})
        if i % 10 == 0 or i == len(all_serials):
            print(f"    scanned {i}/{len(all_serials)}")

    # ── 5. End session → ONE receiving slip ──────────────────────────────────
    slip = api_post(f"/inbound/sessions/{session_id}/end", token, {})
    print(
        f"[5/5] Receiving slip {slip.get('slip_number')} (id={slip.get('id')}) "
        f"status={slip.get('status')} boxes={slip.get('total_boxes')} items={slip.get('total_items')}"
    )
    print("================ DONE ================")
    for group in slip.get("groups", []):
        parent = group.get("parent_qseal") or {}
        print(
            f"  group: product={group.get('product_name')} "
            f"parent={parent.get('serial_number') or '-'} ({len(group.get('items', []))} units)"
        )
        for line in group.get("items", []):
            print(
                f"    sku={line.get('sku')} serial={line.get('serial_number')} "
                f"batch={line.get('batch_number')} qty={line.get('quantity')} flag={line.get('flag')}"
            )


if __name__ == "__main__":
    main()
