"""Seed end-to-end returns demo data for both Prestige warehouses.

Run inside the core container:
    docker exec horizon_core python -m app._seed_returns_demo

For each warehouse it creates:
  * outbound delivery notes (the dispatch reference a return points at),
  * a `ready` registration the dock can start receiving,
  * a registration driven through a full handheld session to a note awaiting
    supervisor approval,
and for Ecity additionally approves a note and generates put-away.

Everything goes over real HTTP against the documented endpoints, so this run is
itself an end-to-end test of the returns contract.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal

import requests

from app.database import SessionLocal
from app.models.base import DocumentStatus
from app.models.customer import Customer
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.item import Item
from app.models.warehouse import Warehouse

CORE = os.getenv("CORE_BASE_URL", "http://localhost:8001")
IDENTITY = os.getenv("IDENTITY_BASE_URL", "http://identity-service:8000")
EMAIL = os.getenv("SEED_EMAIL", "ttkwmsmanager@prestige.com")
PASSWORD = os.getenv("SEED_PASSWORD", "Test@123")

WAREHOUSES = [
    ("Mother warehouse", "8bc22a62-9e7a-4839-8f39-e58f6087d25e"),
    ("Ecity Warehouse", "f0099ec7-0364-416c-9806-22fe38a4c56c"),
]

PASSED: list[str] = []
FAILED: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> bool:
    if condition:
        PASSED.append(label)
        print(f"  PASS  {label}")
    else:
        FAILED.append(f"{label} {detail}".strip())
        print(f"  FAIL  {label} {detail}")
    return bool(condition)


class Api:
    def __init__(self, token: str):
        self.headers = {"Authorization": f"Bearer {token}"}

    def call(self, method, path, body=None, expect=(200, 201)):
        resp = requests.request(
            method, f"{CORE}/api/v1{path}", headers=self.headers, json=body, timeout=60
        )
        ok = resp.status_code in expect
        if not ok:
            print(f"      {method} {path} -> {resp.status_code} {resp.text[:300]}")
        return resp, ok

    def get(self, path, expect=(200,)):
        return self.call("GET", path, None, expect)

    def post(self, path, body=None, expect=(200, 201)):
        return self.call("POST", path, body, expect)


def login() -> str:
    resp = requests.post(
        f"{IDENTITY}/api/v1/identity/login",
        json={"email": EMAIL, "password": PASSWORD},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def organization_id(token: str) -> str:
    resp = requests.get(
        f"{IDENTITY}/api/v1/identity/me",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["organization_id"]


def make_dispatch(
    db, warehouse_id, warehouse_name, suffix, item, qty, serials, batch, customer
):
    """Create (or reuse) a dispatch document the return can cite."""
    org_short = str(customer.organization_id).split("-")[0]
    number = (
        f"DN-RET-{warehouse_name[:2].upper()}-{suffix}-{org_short}"
        f"-{datetime.now(UTC):%y%m%d}"
    )
    existing = (
        db.query(DeliveryNote).filter(DeliveryNote.delivery_note_no == number).first()
    )
    if existing:
        return existing

    note = DeliveryNote(
        organization_id=customer.organization_id,
        delivery_note_no=number,
        customer_id=customer.id,
        delivery_date=datetime.now(UTC),
        status=DocumentStatus.SUBMITTED,
        warehouse_id=warehouse_id,
        reference_type="seed",
        remarks=f"SEED-RETURNS {suffix}",
        submitted_at=datetime.now(UTC),
    )
    db.add(note)
    db.flush()
    db.add(
        DeliveryNoteItem(
            organization_id=customer.organization_id,
            delivery_note_id=note.id,
            item_id=item.id,
            qty=Decimal(str(qty)),
            uom=item.uom or "NOS",
            warehouse_id=warehouse_id,
            batch_no=batch,
            serial_nos=serials,
            sort_order=0,
        )
    )
    db.commit()
    return note


def register(api, warehouse_id, note, sku, qty, serials, label, note_text):
    resp, ok = api.post(
        "/returns/registrations",
        {
            "reference_type": "delivery_note",
            "invoice_no": note.delivery_note_no,
            "warehouse_id": warehouse_id,
            "return_reason_code": "RETURN_DAMAGED",
            "note": note_text,
            "lines": [
                {"sku": sku, "quantity": qty, "uom": "NOS", "serials": serials or None}
            ],
        },
    )
    check(f"[{label}] create registration", ok)
    return resp.json() if ok else None


def run_session(api, label, registration, sku, serials, batch, *, approve):  # noqa: C901
    reg_id = registration["id"]

    resp, ok = api.post(
        f"/returns/registrations/{reg_id}/sessions", {"dock_location": "DOCK-B"}
    )
    if not check(f"[{label}] open dock session", ok):
        return None
    session_id = resp.json()["id"]

    _, ok = api.post(f"/returns/registrations/{reg_id}/sessions", {}, expect=(409,))
    check(f"[{label}] second session refused (409)", ok)

    scanned = []
    for serial in serials:
        _, ok = api.post(
            f"/returns/sessions/{session_id}/scans",
            {
                "qr_data": json.dumps(
                    {"id": serial, "sku": sku, "qty": 1, "batch": batch}
                ),
                "device_type": "mobile",
                "os": "Android 14",
            },
        )
        if check(f"[{label}] scan {serial}", ok):
            scanned.append(serial)
    if not scanned:
        return None

    _, ok = api.post(
        f"/returns/sessions/{session_id}/scans",
        {
            "qr_data": json.dumps(
                {"id": scanned[0], "sku": sku, "qty": 1, "batch": batch}
            )
        },
        expect=(409,),
    )
    check(f"[{label}] re-scan of same unit refused (409)", ok)

    _, ok = api.post(
        f"/returns/sessions/{session_id}/scans",
        {
            "qr_data": json.dumps(
                {"id": f"NX-{label}-1", "sku": "NOT-ON-RETURN", "qty": 1}
            )
        },
        expect=(404,),
    )
    check(f"[{label}] SKU not on the return refused (404)", ok)

    _, ok = api.post(
        f"/returns/sessions/{session_id}/end", {"note": "early"}, expect=(409,)
    )
    check(f"[{label}] end blocked while unclassified (409)", ok)

    resp, ok = api.get(f"/returns/sessions/{session_id}")
    item_ids = [i["id"] for i in resp.json()["items"]] if ok else []
    if not item_ids:
        return None

    _, ok = api.post(
        f"/returns/sessions/{session_id}/classify",
        {"item_id": item_ids[0], "condition": "damaged"},
        expect=(400,),
    )
    check(f"[{label}] damaged without reason refused (400)", ok)

    resp, ok = api.post(
        f"/returns/sessions/{session_id}/classify",
        {
            "item_id": item_ids[0],
            "condition": "damaged",
            "reason_code": "RETURN_DAMAGED",
            "note": "Dent on the lid",
        },
    )
    body = resp.json() if ok else {}
    check(
        f"[{label}] classify damaged -> QUARANTINE",
        ok and body.get("destination") == "QUARANTINE",
        str(body),
    )
    check(
        f"[{label}] damaged raised a pending exception",
        body.get("exception_id") is not None
        and body.get("exception_status") == "pending_approval",
        str(body),
    )

    if len(item_ids) > 1:
        _, ok = api.post(
            f"/returns/sessions/{session_id}/classify/bulk",
            {"items": [{"item_id": i, "condition": "good"} for i in item_ids[1:]]},
        )
        check(f"[{label}] bulk classify good", ok)

    resp, ok = api.post(
        f"/returns/sessions/{session_id}/end", {"note": "One unit damaged, rest good"}
    )
    if not check(f"[{label}] end session", ok):
        return None
    end = resp.json()
    note_id = end["receipt_note"]["id"]
    check(
        f"[{label}] note number uses the RRN series",
        end["receipt_note"]["note_no"].startswith("RRN"),
        end["receipt_note"]["note_no"],
    )
    check(
        f"[{label}] registration moved to received",
        end["registration_status"] == "received",
    )
    check(
        f"[{label}] conditions counted (good + damaged)",
        end["conditions"]["good"] >= 1 and end["conditions"]["damaged"] >= 1,
        str(end["conditions"]),
    )

    resp, ok = api.get(f"/returns/receipt-notes/{note_id}")
    check(f"[{label}] note detail grouped by SKU", ok and bool(resp.json()["groups"]))
    resp, ok = api.get(f"/returns/receipt-notes/{note_id}/slip")
    check(f"[{label}] return slip generated", ok and bool(resp.json()["slip_no"]))

    if not approve:
        return {"registration_id": reg_id, "note_id": note_id}

    resp, ok = api.post(
        f"/returns/receipt-notes/{note_id}/approve",
        {"note": "Damaged unit accepted for quarantine"},
    )
    check(f"[{label}] approve note", ok)
    if not ok:
        return {"registration_id": reg_id, "note_id": note_id}

    resp, ok = api.post(
        f"/returns/receipt-notes/{note_id}/generate-put-away", {"note": "One worker"}
    )
    if check(f"[{label}] generate put-away", ok):
        out = resp.json()
        check(
            f"[{label}] put-away list created for the good line",
            len(out["put_away_lists"]) >= 1,
            str(out),
        )
        check(
            f"[{label}] damaged line reported as segregated",
            out["segregated_lines"] >= 1,
            str(out["segregated_lines"]),
        )
    _, ok = api.post(
        f"/returns/receipt-notes/{note_id}/generate-put-away", {}, expect=(409,)
    )
    check(f"[{label}] repeat put-away refused (409)", ok)

    resp, ok = api.get(f"/returns/receipt-notes/{note_id}/slip")
    check(
        f"[{label}] slip records the approver",
        ok and resp.json()["approved_by"] is not None,
    )
    return {"registration_id": reg_id, "note_id": note_id}


def purge_stale_dispatches(db):
    """Drop dispatch documents left by earlier seed runs.

    Those predate org-scoping and were written under the system org, so the
    reference lookup (which is org-scoped) cannot see them.
    """
    stale = db.query(DeliveryNote).filter(DeliveryNote.remarks == "SEED-RETURNS").all()
    stale += (
        db.query(DeliveryNote).filter(DeliveryNote.remarks.like("SEED-RETURNS %")).all()
    )
    stale += (
        db.query(DeliveryNote).filter(DeliveryNote.remarks.like("SEED-RETURNS%")).all()
    )
    seen = {}
    for note in stale:
        seen[note.id] = note
    for note in seen.values():
        db.query(DeliveryNoteItem).filter(
            DeliveryNoteItem.delivery_note_id == note.id
        ).delete()
        db.delete(note)
    db.commit()
    return len(seen)


def ensure_customers(db, org_id):
    """Return dealers for this org, creating demo ones when it has none.

    The restored dataset only carries customers for the system org, and a
    delivery note needs a real customer row to reference.
    """
    existing = (
        db.query(Customer).filter(Customer.organization_id == org_id).limit(5).all()
    )
    if existing:
        return existing

    wanted = [
        ("DMO-DLR-001", "Prestige Traders"),
        ("DMO-DLR-002", "Sri Balaji Distributors"),
    ]
    created = []
    for code, name in wanted:
        customer = (
            db.query(Customer)
            .filter(Customer.organization_id == org_id, Customer.customer_code == code)
            .first()
        )
        if customer is None:
            customer = Customer(
                organization_id=org_id,
                customer_name=name,
                customer_code=code,
                status="active",
            )
            db.add(customer)
            db.flush()
        created.append(customer)
    db.commit()
    return created


def main() -> int:  # noqa: C901
    token = login()
    api = Api(token)
    org_id = organization_id(token)
    print(f"logged in as {EMAIL} (org {org_id})")

    db = SessionLocal()
    try:
        purged = purge_stale_dispatches(db)
        if purged:
            print(f"purged {purged} stale seed dispatch document(s)")
        # Scope to the signed-in tenant: the local DB holds more than one org
        # and the API correctly refuses SKUs that belong to another one.
        items = (
            db.query(Item)
            .filter(Item.organization_id == org_id, Item.sku.isnot(None))
            .limit(10)
            .all()
        )
        customers = ensure_customers(db, org_id)
        if len(items) < 3 or not customers:
            print(f"not enough data: {len(items)} items, {len(customers)} customers")
            return 1
        customer = customers[0]

        for index, (label, warehouse_id) in enumerate(WAREHOUSES):
            tag = f"{label.split()[0][:2].upper()}{index}"
            warehouse = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
            if warehouse is None:
                print(f"warehouse {label} ({warehouse_id}) not found")
                continue
            print(f"\n=== {label} ({warehouse_id}) ===")

            # A) receivable registration the dock can start
            item_a = items[index % len(items)]
            serials_a = [f"RET{tag}A{n}" for n in range(2)]
            dn_a = make_dispatch(
                db, warehouse_id, label, "A", item_a, 2, serials_a, "BT-A", customer
            )
            reg_a = register(
                api,
                warehouse_id,
                dn_a,
                item_a.sku,
                2,
                serials_a,
                f"{tag}/A",
                f"Awaiting dock - {label}",
            )
            if reg_a:
                check(
                    f"[{tag}/A] registration is receivable",
                    reg_a["status"] == "ready",
                    reg_a["status"],
                )
                resp, ok = api.get(
                    f"/returns/references?invoice_no={dn_a.delivery_note_no}"
                )
                if check(f"[{tag}/A] reference lookup resolves", ok):
                    body = resp.json()
                    check(
                        f"[{tag}/A] reference identified as a delivery note",
                        body["invoice"]["invoice_type"] == "delivery_note",
                    )
                    check(
                        f"[{tag}/A] already-returned qty reported",
                        body["lines"][0]["already_returned_qty"] >= 2,
                        str(body["lines"][0]),
                    )

            # B) full handheld flow, left for supervisor approval
            item_b = items[(index + 1) % len(items)]
            serials_b = [f"RET{tag}B{n}" for n in range(3)]
            dn_b = make_dispatch(
                db, warehouse_id, label, "B", item_b, 3, serials_b, "BT-B", customer
            )
            reg_b = register(
                api,
                warehouse_id,
                dn_b,
                item_b.sku,
                3,
                serials_b,
                f"{tag}/B",
                "Supervisor review",
            )
            if reg_b:
                run_session(
                    api, f"{tag}/B", reg_b, item_b.sku, serials_b, "BT-B", approve=False
                )

            # C) approved + put-away (Ecity only)
            if "Ecity" in label:
                item_c = items[(index + 2) % len(items)]
                serials_c = [f"RET{tag}C{n}" for n in range(2)]
                dn_c = make_dispatch(
                    db, warehouse_id, label, "C", item_c, 2, serials_c, "BT-C", customer
                )
                reg_c = register(
                    api,
                    warehouse_id,
                    dn_c,
                    item_c.sku,
                    2,
                    serials_c,
                    f"{tag}/C",
                    "Approved demo",
                )
                if reg_c:
                    run_session(
                        api,
                        f"{tag}/C",
                        reg_c,
                        item_c.sku,
                        serials_c,
                        "BT-C",
                        approve=True,
                    )

        print("\n=== queues ===")
        for status_value in ("ready", "received", "pending_approval", "approved"):
            if status_value in ("pending_approval", "approved"):
                resp, ok = api.get(f"/returns/receipt-notes?status={status_value}")
            else:
                resp, ok = api.get(f"/returns/registrations?status={status_value}")
            if ok:
                print(f"  {status_value:18} -> {resp.json()['total_items']} row(s)")

        resp, ok = api.get("/returns/receipt-notes?status=pending_approval")
        if ok:
            check(
                "supervisor queue has notes awaiting approval",
                resp.json()["total_items"] >= 2,
                str(resp.json()["total_items"]),
            )

        resp, ok = api.get("/returns/registrations")
        if ok:
            check(
                "both warehouses have registrations",
                resp.json()["total_items"] >= 2,
                str(resp.json()["total_items"]),
            )
    finally:
        db.close()

    print("\n" + "=" * 70)
    print(f"PASSED {len(PASSED)}   FAILED {len(FAILED)}")
    for failure in FAILED:
        print(f"  FAILED: {failure}")
    return 0 if not FAILED else 1


if __name__ == "__main__":
    sys.exit(main())
