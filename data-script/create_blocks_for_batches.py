"""Create QR blocks (without QR images) for the N latest items.

For each item that has a linked QR product this script:
  1. reads the item's qr_product_id
  2. creates a QR block with qr_image=false + master pack enabled
  3. polls the async block job until it completes (needs the qr-worker running)

Usage:
    python3 data-script/create_blocks_for_batches.py

Config (env vars, all optional):
    BLOCK_ITEM_COUNT    number of latest items to process   (default 10)
    BLOCK_QUANTITY      units per block                    (default 12)
    MASTER_PACK_SIZE    units per master-pack parent       (default 4)
    BLOCK_POLL_TIMEOUT_S seconds to wait per block         (default 180)
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import UTC, datetime

from qr_helpers import api_get, api_post, login

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


def main() -> None:
    token = login()

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
    print(f"[INFO] Latest {len(item_list)} items:\n")

    created = []
    for idx, item in enumerate(item_list, 1):
        item_id = item["id"]
        try:
            detail = api_get(f"/items/{item_id}", token)
        except RuntimeError as exc:
            print(
                f"[{idx}/{len(item_list)}] {item_id} — could not fetch item detail: {exc}"
            )
            continue

        qr_product_id = detail.get("qr_product_id")
        print(
            f"[{idx}/{len(item_list)}] {detail.get('item_code')} ({detail.get('item_name')}) "
            f"qr_product_id={qr_product_id}"
        )
        if not qr_product_id:
            print("    ↳ SKIP: no linked QR product")
            continue

        batch = unique_batch(idx)
        payload = {
            "batch": batch,
            "quantity": QUANTITY,
            "qr_type": QR_TYPE,
            "qr_image": False,
            "master_pack_enabled": True,
            "master_pack_size": MASTER_PACK_SIZE,
        }
        try:
            block = api_post(f"/qr-products/{qr_product_id}/blocks", token, payload)
            block_id = block["id"]
            print(f"    ↳ block {block_id} queued (batch={batch})")
            block = wait_for_completion(block_id, token)
        except RuntimeError as exc:
            print(f"    ↳ FAILED: {exc}")
            continue

        parents = api_get(f"/qseal/blocks/{block_id}/parents", token) or {}
        parent_count = len(parents.get("nodes", []))
        print(f"    ↳ DONE status={block['status']} parents={parent_count}")
        created.append(
            {
                "block_id": block_id,
                "batch": batch,
                "qr_product_id": qr_product_id,
                "item_id": item_id,
                "parents": parent_count,
            }
        )

    print("\n================ Summary ================")
    for c in created:
        print(
            f"  block={c['block_id']} batch={c['batch']} "
            f"item={c['item_id']} parents={c['parents']}"
        )
    print(f"\nTotal blocks created: {len(created)}")


if __name__ == "__main__":
    main()
