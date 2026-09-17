Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/models/warehouse.py#1-1), lines 1 to 70

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/models/scan_session.py#1-1), lines 1 to 110

Ran terminal command:  cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be
docker exec -e PGPASSWORD="$PGPASSWORD" horizon_postgres psql -U horizon_user -d railway -c "SELECT id, name, code, warehouse_type FROM warehouses_extended WHERE organization_id='147f3b9d-77fd-432f-8d91-e5559af9d897' LIMIT 10;"
echo "=== existing ASN statuses ==="
docker exec -e PGPASSWORD="$PGPASSWORD" horizon_postgres psql -U horizon_user -d railway -c "SELECT id, asn_order_no, status, asn_type, warehouse_id_to FROM asn_orders WHERE organization_id='147f3b9d-77fd-432f-8d91-e5559af9d897' ORDER BY created_at DESC LIMIT 5;"

Searched for regex `def create|asn_order_no|warehouse_id_to|def update_status|serial_nos|AsnOrderItem` (`**/core-service/app/services/asn_order_service.py`), 54 results

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/services/asn_order_service.py#19-19), lines 19 to 115

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/schemas/item.py#197-197), lines 197 to 330

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/services/inbound_service.py#1080-1080), lines 1080 to 1150

Searched for regex `asn_orders|inbound|qseal|prefix=` (`**/core-service/app/api/v1/router.py`), 104 results

Searched for regex `class QRProductResponse|sr_number_type|serial_prefix|qr_type|gtin|is_active` (`**/core-service/app/schemas/qr_product.py`), 42 results

Ran terminal command:  cd /Users/devnegi/Documents/www/erpproject/horizon-sync-be
echo "=== which pythons ==="; command -v python3; command -v uv; command -v python
echo "=== does any python have requests? ==="
for p in python3 python uv; do
  command -v $p >/dev/null 2>&1 && echo "--- $p ---" && $p -c "import requests; print('requests', requests.__version__)" 2>&1 | head -1
done
echo "=== venvs ==="; ls -d .venv venv data-script/.venv 2>/dev/null
echo "=== pyproject has requests? ==="; grep -i "requests" pyproject.toml requirements-dev.txt 2>/dev/null | head

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/schemas/inbound.py#330-330), lines 330 to 460

Searched for regex `class ReceivingSlipResponse|class ReceivingSlipItemResponse|slip_number|class ReceivingSlipItem` (`**/core-service/app/schemas/inbound.py`), 7 results

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/schemas/inbound.py#260-260), lines 260 to 330

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/services/qr_decoder.py#200-200), lines 200 to 340

Read [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/core-service/app/services/qr_decoder.py#340-340), lines 340 to 376

I now have the full picture of the receiving flow. Let me create the scripts.

Created [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/data-script/qr_helpers.py)

Created [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/data-script/create_blocks_for_batches.py)

Created [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/data-script/receive_block.py)

Let me verify the scripts work end-to-end with the existing completed block.

Ran terminal command:  python3 data-script/receive_block.py --block-id 243470c4-63fe-4b29-af58-d8251c9a125e

Ran terminal command:  BLOCK_ITEM_COUNT=2 BLOCK_POLL_TIMEOUT_S=90 python3 data-script/create_blocks_for_batches.py

Checked [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/data-script/qr_helpers.py), [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/data-script/create_blocks_for_batches.py), [](file:///Users/devnegi/Documents/www/erpproject/horizon-sync-be/data-script/receive_block.py), no problems found

Created memory file [](file:///Users/devnegi/Library/Application%20Support/Code/User/workspaceStorage/916c75adf0e0e5d9775386a40e3f253c/GitHub.copilot-chat/memory-tool/memories/repo/qr-receiving-scripts.md)

Done. I wrote three scripts in data-script (all standard-library only, so plain `python3` works) and verified them end-to-end against your local stack.

## What I created

| File | Purpose |
|---|---|
| qr_helpers.py | Shared login + HTTP helpers (no `requests` needed) |
| create_blocks_for_batches.py | Create QR blocks (`qr_image=false`, master pack on) for the N latest items, poll until done |
| receive_block.py | Get parent QRs → create ASN → scan session → receiving slip |

## The full flow (no mobile app)

```
batch.py                      → create WMS batches for 10 latest items
create_blocks_for_batches.py  → create QR blocks (no images, master-pack parents)
receive_block.py              → parent QR → child serials → ASN → scan session → receiving slip
```

## How to run

```bash
# 1) (already working) batches for latest items
python3 data-script/batch.py

# 2) create QR blocks (qr_image=false, master pack) for the 10 latest items
python3 data-script/create_blocks_for_batches.py

# 3) simulate receiving for one completed block
python3 data-script/receive_block.py --block-id <block-uuid>
```

Optional config via env vars:
```bash
BLOCK_ITEM_COUNT=10 BLOCK_QUANTITY=12 MASTER_PACK_SIZE=4 \
  python3 data-script/create_blocks_for_batches.py

python3 data-script/receive_block.py \
  --block-id 243470c4-63fe-4b29-af58-d8251c9a125e \
  --warehouse-id f0099ec7-0364-416c-9806-22fe38a4c56c
```

## Verified output (real runs)

`create_blocks_for_batches.py` created 2 blocks, each completing with `parents=3`.

`receive_block.py` on your existing block produced:

```
[1/6] Block 243470c4… batch=BATCH-20260903-P009-40F6
[2/6] Found 3 parent(s), 12 child serial(s)
[3/6] Item ITM-2026-00022 sku=PTK-DUK-M002 uom=Nos
[4/6] ASN ASN-2026-00075 created + confirmed
[5/6] Scan session a5291015… started (12 scans)
[6/6] Receiving slip RS-2026-00094 status=pending_review boxes=12 items=12
  sku=PTK-DUK-M002 qty=12 batch=BATCH-20260903-P009-40F6 flag=ok
```

## Notes

- **Prerequisite**: the `qr-worker` container must be running (blocks generate asynchronously via Celery). It's up in your stack even though Docker shows it "unhealthy" (its healthcheck has no web endpoint — it still consumes jobs).
- The ASN must be `confirmed` before a session can start — the script does `confirm` automatically.
- `record_scan` doesn't resolve a master-pack **parent** serial itself; the mobile app resolves the parent to children via `linked-units`. My script does the same (scans each child serial), which is why step 2 fetches parents → linked units.
- batch.py still uses a hardcoded token that will expire — you can switch it to `from qr_helpers import login` if you want it self-refreshing.

Made changes.
