"""ASN Order service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.asn_order import AsnOrder, AsnOrderItem
from app.models.base import AsnOrderStatus
from app.repositories.asn_order_repository import AsnOrderRepository


class AsnOrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AsnOrderRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id

        # Auto-generate asn_order_no if not provided
        if not payload.get("asn_order_no"):
            from app.services.document_numbering_service import DocumentNumberingService

            payload["asn_order_no"] = DocumentNumberingService(self.db).get_next_number(
                organization_id, "asn_order"
            )

        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = AsnOrderStatus(payload["status"])

        # Default ASN type; internal transfers require a source warehouse.
        if not payload.get("asn_type"):
            payload["asn_type"] = "purchase"

        # Stock Receipt ASNs arrive from manufacturing units (which are not
        # warehouses in the system), so they only carry a target warehouse.
        if payload["asn_type"] == "stock_receipt":
            payload["warehouse_id_from"] = None
            if not payload.get("warehouse_id_to"):
                raise ValueError(
                    "warehouse_id_to (target warehouse) is required for a "
                    "stock receipt ASN"
                )
        elif payload["asn_type"] == "internal_transfer" and not payload.get(
            "warehouse_id_from"
        ):
            raise ValueError(
                "warehouse_id_from (source warehouse) is required for an "
                "internal transfer ASN"
            )

        # Extract items
        items_data = payload.pop("items", [])

        # Validate warehouse_id_from belongs to same organization
        if "warehouse_id_from" in payload and payload["warehouse_id_from"]:
            self._validate_warehouse_organization(
                payload["warehouse_id_from"], organization_id
            )

        if "warehouse_id_to" in payload and payload["warehouse_id_to"]:
            self._validate_warehouse_organization(
                payload["warehouse_id_to"], organization_id
            )

        # Validate item_ids in line items belong to same organization
        for item_data in items_data:
            if "item_id" in item_data:
                self._validate_item_organization(item_data["item_id"], organization_id)

        # Create ASN order first (need asn_order.id for item payloads)
        asn_order = self.repo.create(payload)

        # Create line items and compute grand_total (sum of qtys)
        grand_total = Decimal("0")
        for item_data in items_data:
            item_payload = {
                "organization_id": organization_id,
                "asn_order_id": asn_order.id,
                "item_id": item_data["item_id"],
                "qty": Decimal(str(item_data["qty"])),
                "uom": item_data.get("uom", "pcs"),
                "sort_order": item_data.get("sort_order", 0),
                "serial_nos": item_data.get("serial_nos") or None,
                "shipped_qty": Decimal(str(item_data.get("shipped_qty") or 0)),
                "received_qty": Decimal(str(item_data.get("received_qty") or 0)),
            }
            grand_total += item_payload["qty"]
            self.db.add(AsnOrderItem(**item_payload))

        # Update grand_total
        self.repo.update(asn_order, {"grand_total": grand_total})
        self.db.refresh(asn_order)

        # Emit notification to receiving warehouse users
        self._emit_asn_notification(
            asn_order=asn_order,
            notif_type="asn_created",
            title="New ASN Order",
            message=f"ASN {asn_order.asn_order_no} has been created for your warehouse.",
            warehouse_id=asn_order.warehouse_id_to,
            sender_id=user_id,
        )

        return self._to_response(asn_order)

    def get_by_id(self, asn_order_id: UUID, organization_id: UUID) -> dict:
        asn_order = self.repo.get_by_id_with_items(asn_order_id, organization_id)
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")
        return self._to_response(asn_order)

    def get_serial_lines(self, asn_order_id: UUID, organization_id: UUID) -> dict:
        """Return unit-level serial lines for an internal-transfer ASN.

        Includes received/not-received counts for in-transit visibility.
        """
        from app.models.asn_order import AsnOrder, AsnOrderSerialLine

        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")

        lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(
                AsnOrderSerialLine.asn_order_id == asn_order_id,
                AsnOrderSerialLine.organization_id == organization_id,
            )
            .order_by(AsnOrderSerialLine.created_at.asc())
            .all()
        )
        received = sum(1 for line in lines if line.received)
        return {
            "asn_order_id": str(asn_order_id),
            "asn_order_no": asn_order.asn_order_no,
            "asn_type": asn_order.asn_type or "purchase",
            "status": asn_order.status.value if asn_order.status else "draft",
            "total_serials": len(lines),
            "received_serials": received,
            "in_transit_serials": len(lines) - received,
            "serials": [
                {
                    "id": str(line.id),
                    "item_id": str(line.item_id),
                    "serial_no": line.serial_no,
                    "bin_location_id": str(line.bin_location_id)
                    if line.bin_location_id
                    else None,
                    "received": bool(line.received),
                    "received_at": line.received_at,
                    "received_by": str(line.received_by) if line.received_by else None,
                }
                for line in lines
            ],
        }

    def serialized_asn_856(self, asn_order_id: UUID, organization_id: UUID) -> dict:
        """EDI-856-style serialized ASN export (SKU + unit-level serials + SSCC)."""
        from app.models.asn_order import AsnOrder, AsnOrderSerialLine
        from app.services.gs1_service import generate_sscc

        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")

        serial_lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn_order_id)
            .all()
        )
        serials_by_item: dict[str, list[str]] = {}
        for line in serial_lines:
            serials_by_item.setdefault(str(line.item_id), []).append(line.serial_no)

        items = []
        for item in asn_order.items:
            serials = serials_by_item.get(str(item.item_id), [])
            items.append(
                {
                    "sku": (item.item.sku or item.item.item_code)
                    if item.item
                    else None,
                    "gtin": item.item.gtin if item.item else None,
                    "description": item.item.item_name if item.item else None,
                    "quantity": float(item.shipped_qty or item.qty),
                    "uom": item.uom,
                    "serial_numbers": serials,
                }
            )

        # One SSCC per shipment (logistics unit), derived from the ASN id.
        # The serial reference must fit the 17-digit SSCC body given the
        # default 7-digit company prefix: 17 - 1 (extension) - 7 = 9 digits.
        serial_ref = (
            str(asn_order.id.int % 1_000_000_000).rjust(9, "0")
            if getattr(asn_order.id, "int", None)
            else "1"
        )
        sscc = generate_sscc(serial_ref)

        return {
            "transaction_set": "856",
            "asn_number": asn_order.asn_order_no,
            "asn_type": asn_order.asn_type or "purchase",
            "ship_from": (
                asn_order.from_warehouse.name if asn_order.from_warehouse else None
            ),
            "ship_to": (
                asn_order.to_warehouse.name if asn_order.to_warehouse else None
            ),
            "order_date": asn_order.order_date,
            "delivery_date": asn_order.delivery_date,
            "sscc": sscc,
            "items": items,
        }

    def epcis_events(self, asn_order_id: UUID, organization_id: UUID) -> dict:
        """EPCIS 2.0-style event stream for a transfer ASN's serials."""
        from app.models.asn_order import AsnOrder, AsnOrderSerialLine
        from app.models.serial_no import SerialNo, SerialNoHistory
        from app.services.epcis_service import build_events_for_serial

        asn_order = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")

        serial_lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn_order_id)
            .all()
        )
        serial_nos = [line.serial_no for line in serial_lines]

        histories = (
            self.db.query(SerialNoHistory)
            .filter(
                SerialNoHistory.organization_id == organization_id,
                SerialNoHistory.transaction_id == asn_order_id,
            )
            .order_by(SerialNoHistory.transaction_date.asc())
            .all()
        )

        serial_map: dict = {}
        serial_ids = {h.serial_no_id for h in histories}
        if serial_ids:
            serial_map = {
                s.id: s.serial_no
                for s in self.db.query(SerialNo)
                .filter(SerialNo.id.in_(serial_ids))
                .all()
            }

        by_serial: dict[str, list] = {}
        for h in histories:
            sn = serial_map.get(h.serial_no_id)
            if sn is None:
                continue
            by_serial.setdefault(sn, []).append(h)

        events: list[dict] = []
        for sn in serial_nos:
            events.extend(build_events_for_serial(sn, by_serial.get(sn, [])))

        return {
            "context": {
                "schema": "EPCIS 2.0 (simplified JSON)",
                "asn_number": asn_order.asn_order_no,
            },
            "events": events,
        }

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        warehouse_id: UUID | None = None,
        source_warehouse_id: UUID | None = None,
        delivery_date_from=None,
        delivery_date_to=None,
        vehicle_no: str | None = None,
        search: str | None = None,
        asn_type: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_asn_orders(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status,
            warehouse_id=warehouse_id,
            source_warehouse_id=source_warehouse_id,
            delivery_date_from=delivery_date_from,
            delivery_date_to=delivery_date_to,
            vehicle_no=vehicle_no,
            search=search,
            asn_type=asn_type,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(x) for x in items], pagination

    def update(  # noqa: C901
        self,
        asn_order_id: UUID,
        data: dict,
        organization_id: UUID,
        user_id: UUID,
        user_type: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict:
        asn_order = self.repo.get_by_id_with_items(asn_order_id, organization_id)
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")

        payload = {k: v for k, v in data.items() if v is not None and k != "items"}

        # Capture old status to detect changes
        old_status = asn_order.status

        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = AsnOrderStatus(payload["status"])

        payload["updated_by"] = user_id

        # Validate warehouse changes
        if "warehouse_id_from" in payload and payload["warehouse_id_from"]:
            self._validate_warehouse_organization(
                payload["warehouse_id_from"], organization_id
            )
        if "warehouse_id_to" in payload and payload["warehouse_id_to"]:
            self._validate_warehouse_organization(
                payload["warehouse_id_to"], organization_id
            )

        # An internal-transfer ASN must always have a source warehouse. The
        # update may set asn_type to internal_transfer without a source, which
        # would otherwise fail later when the confirmation tries to create the
        # source pick list.
        effective_asn_type = payload.get("asn_type", asn_order.asn_type)
        effective_from = payload.get("warehouse_id_from", asn_order.warehouse_id_from)

        # Stock Receipt ASNs never carry a source warehouse (stock arrives from
        # manufacturing units, not another warehouse), but they always need a
        # target (mother) warehouse.
        if effective_asn_type == "stock_receipt":
            payload["warehouse_id_from"] = None
            effective_to = payload.get("warehouse_id_to", asn_order.warehouse_id_to)
            if not effective_to:
                raise ValidationError(
                    message=(
                        "warehouse_id_to (target warehouse) is required for a "
                        "stock receipt ASN"
                    ),
                    details=[
                        {
                            "field": "warehouse_id_to",
                            "reason": (
                                "A target warehouse is required when asn_type "
                                "is stock_receipt"
                            ),
                        }
                    ],
                )

        if effective_asn_type == "internal_transfer" and not effective_from:
            raise ValidationError(
                message=(
                    "warehouse_id_from (source warehouse) is required for an "
                    "internal transfer ASN"
                ),
                details=[
                    {
                        "field": "warehouse_id_from",
                        "reason": (
                            "A source warehouse is required when asn_type is "
                            "internal_transfer"
                        ),
                    }
                ],
            )

        # Handle items update if provided
        if "items" in data:
            items_data = data["items"]

            for item_data in items_data:
                if "item_id" in item_data:
                    self._validate_item_organization(
                        item_data["item_id"], organization_id
                    )

            # Delete existing items
            for item in asn_order.items:
                self.db.delete(item)

            # Create new items
            grand_total = Decimal("0")
            for item_data in items_data:
                item_payload = {
                    "organization_id": organization_id,
                    "asn_order_id": asn_order.id,
                    "item_id": item_data["item_id"],
                    "qty": Decimal(str(item_data["qty"])),
                    "uom": item_data.get("uom", "pcs"),
                    "sort_order": item_data.get("sort_order", 0),
                    "serial_nos": item_data.get("serial_nos") or None,
                    "shipped_qty": Decimal(str(item_data.get("shipped_qty") or 0)),
                    "received_qty": Decimal(str(item_data.get("received_qty") or 0)),
                }
                grand_total += item_payload["qty"]
                self.db.add(AsnOrderItem(**item_payload))

            payload["grand_total"] = grand_total

        self.repo.update(asn_order, payload)
        self.db.refresh(asn_order)

        # Emit notifications when status changes via the general update endpoint
        new_status = asn_order.status
        if old_status != new_status:
            # Internal transfer side-effects (the dialog confirms through this
            # endpoint, not the dedicated status endpoint).
            if (
                new_status == AsnOrderStatus.CONFIRMED
                and asn_order.asn_type == "internal_transfer"
            ):
                created_pick_list = self._create_transfer_pick_list(asn_order, user_id)
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="transfer_pick_created",
                    title="Transfer Pick List Created",
                    message=(
                        f"Pick list {created_pick_list.get('pick_list_no')} was "
                        f"created at the source warehouse for ASN "
                        f"{asn_order.asn_order_no}."
                    ),
                    warehouse_id=asn_order.warehouse_id_to,
                    sender_id=user_id,
                )
            elif (
                new_status == AsnOrderStatus.CANCELLED
                and asn_order.asn_type == "internal_transfer"
            ):
                self._reverse_transfer(asn_order)

            if new_status == AsnOrderStatus.CONFIRMED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="asn_confirmed",
                    title="ASN Confirmed",
                    message=f"ASN {asn_order.asn_order_no} has been confirmed and is ready for fulfillment.",
                    warehouse_id=self._fulfillment_warehouse(asn_order),
                    sender_id=user_id,
                )
            elif new_status == AsnOrderStatus.PARTIALLY_DELIVERED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="fulfillment_partially_completed",
                    title="ASN Partially Delivered",
                    message=f"ASN {asn_order.asn_order_no} has been partially delivered.",
                    warehouse_id=self._fulfillment_warehouse(asn_order),
                    sender_id=user_id,
                )
            elif new_status == AsnOrderStatus.DELIVERED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="fulfillment_completed",
                    title="ASN Fully Delivered",
                    message=f"ASN {asn_order.asn_order_no} has been fully delivered.",
                    warehouse_id=self._fulfillment_warehouse(asn_order),
                    sender_id=user_id,
                )
            elif new_status == AsnOrderStatus.CANCELLED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="asn_cancelled",
                    title="ASN Cancelled",
                    message=f"ASN {asn_order.asn_order_no} has been cancelled.",
                    warehouse_id=asn_order.warehouse_id_to,
                    sender_id=user_id,
                )

        return self._to_response(asn_order)

    def delete(self, asn_order_id: UUID, organization_id: UUID) -> None:
        asn_order = self.repo.get_by_id(asn_order_id, organization_id)
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")
        self.repo.delete(asn_order)

    def update_status(
        self,
        asn_order_id: UUID,
        new_status: str,
        organization_id: UUID,
        user_id: UUID,
        user_type: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict:
        asn_order = self.repo.get_by_id_with_items(asn_order_id, organization_id)
        if not asn_order:
            raise ResourceNotFoundException(f"ASN Order {asn_order_id} not found")

        new_status_enum = AsnOrderStatus(new_status)
        self._validate_status_transition(asn_order.status, new_status_enum)

        payload = {
            "status": new_status_enum,
            "updated_by": user_id,
        }

        # Set submitted_at when status changes to CONFIRMED
        if (
            new_status_enum == AsnOrderStatus.CONFIRMED
            and asn_order.submitted_at is None
        ):
            from datetime import UTC, datetime

            payload["submitted_at"] = datetime.now(UTC)

        self.repo.update(asn_order, payload)
        self.db.refresh(asn_order)

        # Internal transfer: confirming the ASN drives the source pick list.
        if (
            new_status_enum == AsnOrderStatus.CONFIRMED
            and asn_order.asn_type == "internal_transfer"
        ):
            created_pick_list = self._create_transfer_pick_list(asn_order, user_id)
            # Notify the destination (creation side) that fulfilment started.
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="transfer_pick_created",
                title="Transfer Pick List Created",
                message=(
                    f"Pick list {created_pick_list.get('pick_list_no')} was created "
                    f"at the source warehouse for ASN {asn_order.asn_order_no}."
                ),
                warehouse_id=asn_order.warehouse_id_to,
                sender_id=user_id,
            )

        # Internal transfer: cancelling reverses in-transit serials + pick list.
        if (
            new_status_enum == AsnOrderStatus.CANCELLED
            and asn_order.asn_type == "internal_transfer"
        ):
            self._reverse_transfer(asn_order)

        # Emit notifications based on status change
        if new_status_enum == AsnOrderStatus.CONFIRMED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="asn_confirmed",
                title="ASN Confirmed",
                message=f"ASN {asn_order.asn_order_no} has been confirmed and is ready for fulfillment.",
                warehouse_id=self._fulfillment_warehouse(asn_order),
                sender_id=user_id,
            )
        elif new_status_enum == AsnOrderStatus.PARTIALLY_DELIVERED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="fulfillment_partially_completed",
                title="ASN Partially Delivered",
                message=f"ASN {asn_order.asn_order_no} has been partially delivered.",
                warehouse_id=self._fulfillment_warehouse(asn_order),
                sender_id=user_id,
            )
        elif new_status_enum == AsnOrderStatus.DELIVERED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="fulfillment_completed",
                title="ASN Fully Delivered",
                message=f"ASN {asn_order.asn_order_no} has been fully delivered.",
                warehouse_id=self._fulfillment_warehouse(asn_order),
                sender_id=user_id,
            )
        elif new_status_enum == AsnOrderStatus.CANCELLED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="asn_cancelled",
                title="ASN Cancelled",
                message=f"ASN {asn_order.asn_order_no} has been cancelled.",
                warehouse_id=asn_order.warehouse_id_to,
                sender_id=user_id,
            )

        return self._to_response(asn_order)

    # ── internal-transfer fulfilment ──────────────────────────────────

    def _create_transfer_pick_list(self, asn_order: AsnOrder, user_id: UUID) -> dict:
        """Auto-create the source warehouse's pick list for an internal transfer.

        Mirrors each ASN line into a pick list at ``warehouse_id_from`` with
        ``reference_type='asn_order'`` so the normal outbound flow can fulfil it.
        Returns the created pick list dict and links it back onto the ASN.
        """
        import logging

        logger = logging.getLogger(__name__)

        # Serialize concurrent confirmations: take a row lock on the ASN so two
        # simultaneous confirms cannot both observe a missing linked pick list
        # and create duplicate pick lists. (FOR UPDATE is a no-op on SQLite.)
        linked_pick_list_id = (
            self.db.query(AsnOrder.linked_pick_list_id)
            .filter(AsnOrder.id == asn_order.id)
            .with_for_update()
            .scalar()
        )

        # Idempotency: never create a second pick list for the same ASN.
        if linked_pick_list_id:
            from app.models.pick_list import PickList

            existing = self.db.get(PickList, linked_pick_list_id)
            if existing:
                return {"id": existing.id, "pick_list_no": existing.pick_list_no}

        if not asn_order.warehouse_id_from:
            raise ValueError("Source warehouse is required to create a pick list")

        if not asn_order.items:
            raise ValueError("Internal transfer ASN has no line items to pick")

        from app.services.pick_list_service import PickListService

        items = [
            {
                "item_id": item.item_id,
                "warehouse_id": asn_order.warehouse_id_from,
                "qty": float(item.qty),
                "uom": item.uom,
                "sort_order": item.sort_order or 0,
            }
            for item in asn_order.items
        ]

        created = PickListService(self.db).create(
            {
                "warehouse_id": asn_order.warehouse_id_from,
                "status": "draft",
                "reference_type": "asn_order",
                "reference_id": str(asn_order.id),
                "remarks": (f"Internal transfer from ASN {asn_order.asn_order_no}"),
                "items": items,
            },
            asn_order.organization_id,
            user_id,
        )

        asn_order.linked_pick_list_id = created.get("id")
        self.db.flush()
        self.db.commit()

        logger.info(
            "Created source pick list '%s' for internal transfer ASN '%s'",
            created.get("pick_list_no"),
            asn_order.asn_order_no,
        )
        return created

    def _reverse_transfer(self, asn_order: AsnOrder) -> None:
        """Reverse an internal transfer on cancel.

        Restores not-yet-received serials to the source warehouse (``in_stock``)
        with a ``transfer_cancelled`` history row, and cancels the linked pick
        list if it hasn't been dispatched yet.
        """
        import logging

        logger = logging.getLogger(__name__)

        from app.models.asn_order import AsnOrderSerialLine
        from app.models.pick_list import PickList, PickListStatus
        from app.models.serial_no import SerialNo, SerialNoHistory

        lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn_order.id)
            .all()
        )
        for line in lines:
            if line.received:
                continue
            serial_row = (
                self.db.query(SerialNo)
                .filter(
                    SerialNo.organization_id == asn_order.organization_id,
                    SerialNo.serial_no == line.serial_no,
                    SerialNo.item_id == line.item_id,
                )
                .first()
            )
            if serial_row is not None:
                serial_row.warehouse_id = asn_order.warehouse_id_from
                serial_row.status = "in_stock"
                self.db.add(
                    SerialNoHistory(
                        organization_id=asn_order.organization_id,
                        serial_no_id=serial_row.id,
                        transaction_type="transfer_cancelled",
                        transaction_id=asn_order.id,
                        from_warehouse_id=asn_order.warehouse_id_to,
                        to_warehouse_id=asn_order.warehouse_id_from,
                        remarks=f"Cancelled transfer ASN {asn_order.asn_order_no}",
                    )
                )

        pick_list = (
            self.db.query(PickList)
            .filter(
                PickList.organization_id == asn_order.organization_id,
                PickList.reference_type == "asn_order",
                PickList.reference_id == asn_order.id,
            )
            .first()
        )
        if (
            pick_list is not None
            and pick_list.status
            not in (PickListStatus.COMPLETED, PickListStatus.CANCELLED)
            and pick_list.dispatch_record_id is None
        ):
            pick_list.status = PickListStatus.CANCELLED

        logger.info(
            "Reversed in-transit serials for cancelled transfer ASN '%s'",
            asn_order.asn_order_no,
        )

    # ── notification helpers ─────────────────────────────────────────

    def _fulfillment_warehouse(self, asn_order: AsnOrder) -> UUID | None:
        """Warehouse to notify for fulfilment progress.

        Stock receipts have no source warehouse (manufacturing units are not
        warehouses), so fall back to the target warehouse instead of passing
        ``None`` — which broadcasts to every org user.
        """
        return asn_order.warehouse_id_from or asn_order.warehouse_id_to

    def _emit_asn_notification(
        self,
        asn_order: AsnOrder,
        notif_type: str,
        title: str,
        message: str,
        warehouse_id: UUID | None,
        sender_id: UUID | None,
    ) -> None:
        """Emit an in-app notification to users assigned to the target warehouse.

        If no users are assigned to the target warehouse, falls back to notifying
        all WMS Supervisors in the organization so the ASN never goes unnoticed.
        """
        import logging

        logger = logging.getLogger(__name__)
        try:
            from app.services.notification_service import NotificationService

            notif_svc = NotificationService(self.db)
            created = notif_svc.create_for_warehouse_users(
                organization_id=asn_order.organization_id,
                warehouse_id=warehouse_id,
                type=notif_type,
                title=title,
                message=message,
                entity_type="asn_order",
                entity_id=asn_order.id,
                entity_no=asn_order.asn_order_no,
                sender_id=sender_id,
                exclude_user_id=sender_id,
            )
            logger.warning(
                "ASN notification %s for order %s: created %s notification(s) for warehouse %s",
                notif_type,
                asn_order.asn_order_no,
                len(created),
                warehouse_id,
            )

            # Fallback: if no users assigned to this warehouse, notify supervisors
            if not created:
                fallback = notif_svc.create_for_role_users(
                    organization_id=asn_order.organization_id,
                    role="supervisor",
                    type=notif_type,
                    title=f"{title} (unassigned warehouse)",
                    message=message,
                    entity_type="asn_order",
                    entity_id=asn_order.id,
                    entity_no=asn_order.asn_order_no,
                    sender_id=sender_id,
                    exclude_user_id=sender_id,
                )
                logger.warning(
                    "ASN notification %s fallback: created %s supervisor notification(s)",
                    notif_type,
                    len(fallback),
                )
        except Exception as exc:
            # Notifications are best-effort; don't fail the ASN operation
            logger.error(
                "Failed to emit ASN notification %s for order %s: %s",
                notif_type,
                asn_order.asn_order_no,
                exc,
                exc_info=True,
            )
            # A failed notification flush leaves the session in a
            # rolled-back state, which would poison any subsequent reads
            # (e.g. _to_response) with a 503. Discard the broken transaction.
            try:
                self.db.rollback()
            except Exception:
                pass

    # ── validation helpers ─────────────────────────────────────────────

    def _validate_warehouse_organization(
        self, warehouse_id: UUID, organization_id: UUID
    ) -> None:
        from app.models.warehouse import Warehouse

        wh = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
            .first()
        )
        if not wh:
            raise ResourceNotFoundException(
                f"Warehouse {warehouse_id} not found in organization"
            )

    def _validate_item_organization(self, item_id: UUID, organization_id: UUID) -> None:
        from app.models.item import Item

        item = (
            self.db.query(Item)
            .filter(
                Item.id == item_id,
                Item.organization_id == organization_id,
            )
            .first()
        )
        if not item:
            raise ResourceNotFoundException(f"Item {item_id} not found in organization")

    def _validate_status_transition(
        self,
        current_status: AsnOrderStatus,
        new_status: AsnOrderStatus,
    ) -> None:
        if current_status == new_status:
            return

        if new_status == AsnOrderStatus.CANCELLED:
            if current_status == AsnOrderStatus.CLOSED:
                raise ValueError("Cannot cancel an ASN order that is already CLOSED")
            return

        if current_status in (AsnOrderStatus.CANCELLED, AsnOrderStatus.CLOSED):
            raise ValueError(
                f"Cannot transition from {current_status.value} to {new_status.value}"
            )

        allowed_transitions = {
            AsnOrderStatus.DRAFT: [
                AsnOrderStatus.CONFIRMED,
                AsnOrderStatus.CANCELLED,
            ],
            AsnOrderStatus.CONFIRMED: [
                AsnOrderStatus.PARTIALLY_DELIVERED,
                AsnOrderStatus.DELIVERED,
                AsnOrderStatus.CANCELLED,
            ],
            AsnOrderStatus.PARTIALLY_DELIVERED: [
                AsnOrderStatus.DELIVERED,
                AsnOrderStatus.CANCELLED,
            ],
            AsnOrderStatus.DELIVERED: [
                AsnOrderStatus.CLOSED,
                AsnOrderStatus.CANCELLED,
            ],
        }

        allowed = allowed_transitions.get(current_status, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}"
            )

    # ── serialization helpers ──────────────────────────────────────────

    @staticmethod
    def _vehicle_arrivals_for_response(asn_order: AsnOrder) -> list[dict]:
        return [
            {
                "id": arrival.id,
                "vehicle_no": arrival.vehicle.vehicle_no if arrival.vehicle else None,
                "driver_name": arrival.vehicle.driver_name if arrival.vehicle else None,
                "driver_contact": (
                    arrival.vehicle.driver_contact if arrival.vehicle else None
                ),
                "transporter": arrival.vehicle.transporter if arrival.vehicle else None,
                "dock": arrival.dock,
                "status": arrival.status,
                "arrived_at": arrival.arrived_at,
            }
            for arrival in asn_order.vehicle_arrivals
        ]

    def _linked_pick_list_no(self, asn_order: AsnOrder) -> str | None:
        """Resolve the linked pick list number (if any) for the ASN."""
        if not asn_order.linked_pick_list_id:
            return None
        from app.models.pick_list import PickList

        pl = self.db.get(PickList, asn_order.linked_pick_list_id)
        return pl.pick_list_no if pl else None

    def _transfer_progress(self, asn_order: AsnOrder) -> dict | None:
        """Serial-level transfer progress for internal-transfer ASNs."""
        if asn_order.asn_type != "internal_transfer":
            return None
        from app.models.asn_order import AsnOrderSerialLine

        lines = (
            self.db.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn_order.id)
            .all()
        )
        received = sum(1 for line in lines if line.received)
        return {
            "total_serials": len(lines),
            "received_serials": received,
            "in_transit_serials": len(lines) - received,
        }

    def _to_response(self, asn_order: AsnOrder) -> dict:
        from_warehouse = None
        if asn_order.from_warehouse:
            from_warehouse = {
                "id": asn_order.from_warehouse.id,
                "name": asn_order.from_warehouse.name,
                "code": asn_order.from_warehouse.code,
            }

        to_warehouse = None
        if asn_order.to_warehouse:
            to_warehouse = {
                "id": asn_order.to_warehouse.id,
                "name": asn_order.to_warehouse.name,
                "code": asn_order.to_warehouse.code,
            }

        items = []
        for item in asn_order.items:
            item_dict = {
                "id": item.id,
                "organization_id": item.organization_id,
                "asn_order_id": item.asn_order_id,
                "item_id": item.item_id,
                "item_code": item.item.item_code if item.item else None,
                "sku": (item.item.sku or item.item.item_code) if item.item else None,
                "item_name": item.item.item_name if item.item else None,
                "qty": float(item.qty) if item.qty else 0,
                "uom": item.uom,
                "sort_order": item.sort_order,
                "delivered_qty": float(item.delivered_qty) if item.delivered_qty else 0,
                "serial_nos": item.serial_nos or [],
                "shipped_qty": float(item.shipped_qty) if item.shipped_qty else 0,
                "received_qty": float(item.received_qty) if item.received_qty else 0,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
            items.append(item_dict)

        return {
            "id": asn_order.id,
            "organization_id": asn_order.organization_id,
            "asn_order_no": asn_order.asn_order_no,
            "warehouse_id_from": asn_order.warehouse_id_from,
            "warehouse_id_to": asn_order.warehouse_id_to,
            "order_date": asn_order.order_date,
            "delivery_date": asn_order.delivery_date,
            "status": asn_order.status.value if asn_order.status else "draft",
            "grand_total": float(asn_order.grand_total) if asn_order.grand_total else 0,
            "reference_type": asn_order.reference_type,
            "reference_id": asn_order.reference_id,
            "reference_no": asn_order.reference_no,
            "asn_type": asn_order.asn_type or "purchase",
            "linked_pick_list_id": (
                str(asn_order.linked_pick_list_id)
                if asn_order.linked_pick_list_id
                else None
            ),
            "linked_pick_list_no": self._linked_pick_list_no(asn_order),
            "transfer_progress": self._transfer_progress(asn_order),
            "remarks": asn_order.remarks,
            "submitted_at": asn_order.submitted_at,
            "created_by": asn_order.created_by,
            "updated_by": asn_order.updated_by,
            "created_at": asn_order.created_at,
            "updated_at": asn_order.updated_at,
            "from_warehouse": from_warehouse,
            "to_warehouse": to_warehouse,
            "vehicle_arrivals": self._vehicle_arrivals_for_response(asn_order),
            "items": items,
        }

    def _to_list_item(self, asn_order: AsnOrder) -> dict:
        from_warehouse = None
        if asn_order.from_warehouse:
            from_warehouse = {
                "id": asn_order.from_warehouse.id,
                "name": asn_order.from_warehouse.name,
                "code": asn_order.from_warehouse.code,
            }

        to_warehouse = None
        if asn_order.to_warehouse:
            to_warehouse = {
                "id": asn_order.to_warehouse.id,
                "name": asn_order.to_warehouse.name,
                "code": asn_order.to_warehouse.code,
            }

        return {
            "id": asn_order.id,
            "organization_id": asn_order.organization_id,
            "asn_order_no": asn_order.asn_order_no,
            "status": asn_order.status.value if asn_order.status else "draft",
            "order_date": asn_order.order_date,
            "delivery_date": asn_order.delivery_date,
            "grand_total": float(asn_order.grand_total) if asn_order.grand_total else 0,
            "asn_type": asn_order.asn_type or "purchase",
            "linked_pick_list_id": (
                str(asn_order.linked_pick_list_id)
                if asn_order.linked_pick_list_id
                else None
            ),
            "from_warehouse": from_warehouse,
            "to_warehouse": to_warehouse,
            "vehicle_arrivals": self._vehicle_arrivals_for_response(asn_order),
            "created_at": asn_order.created_at,
        }
