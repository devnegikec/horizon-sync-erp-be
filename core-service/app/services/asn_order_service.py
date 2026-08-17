"""ASN Order service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
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

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        warehouse_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "order_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_asn_orders(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status,
            warehouse_id=warehouse_id,
            search=search,
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

    def update(
        self, asn_order_id: UUID, data: dict, organization_id: UUID, user_id: UUID
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
                }
                grand_total += item_payload["qty"]
                self.db.add(AsnOrderItem(**item_payload))

            payload["grand_total"] = grand_total

        self.repo.update(asn_order, payload)
        self.db.refresh(asn_order)

        # Emit notifications when status changes via the general update endpoint
        new_status = asn_order.status
        if old_status != new_status:
            if new_status == AsnOrderStatus.CONFIRMED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="asn_confirmed",
                    title="ASN Confirmed",
                    message=f"ASN {asn_order.asn_order_no} has been confirmed and is ready for fulfillment.",
                    warehouse_id=asn_order.warehouse_id_from,
                    sender_id=user_id,
                )
            elif new_status == AsnOrderStatus.PARTIALLY_DELIVERED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="fulfillment_partially_completed",
                    title="ASN Partially Delivered",
                    message=f"ASN {asn_order.asn_order_no} has been partially delivered.",
                    warehouse_id=asn_order.warehouse_id_from,
                    sender_id=user_id,
                )
            elif new_status == AsnOrderStatus.DELIVERED:
                self._emit_asn_notification(
                    asn_order=asn_order,
                    notif_type="fulfillment_completed",
                    title="ASN Fully Delivered",
                    message=f"ASN {asn_order.asn_order_no} has been fully delivered.",
                    warehouse_id=asn_order.warehouse_id_from,
                    sender_id=user_id,
                )
                self._create_delivery_stock_entry(asn_order, organization_id, user_id)
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

        # Emit notifications based on status change
        if new_status_enum == AsnOrderStatus.CONFIRMED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="asn_confirmed",
                title="ASN Confirmed",
                message=f"ASN {asn_order.asn_order_no} has been confirmed and is ready for fulfillment.",
                warehouse_id=asn_order.warehouse_id_from,
                sender_id=user_id,
            )
        elif new_status_enum == AsnOrderStatus.PARTIALLY_DELIVERED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="fulfillment_partially_completed",
                title="ASN Partially Delivered",
                message=f"ASN {asn_order.asn_order_no} has been partially delivered.",
                warehouse_id=asn_order.warehouse_id_from,
                sender_id=user_id,
            )
        elif new_status_enum == AsnOrderStatus.DELIVERED:
            self._emit_asn_notification(
                asn_order=asn_order,
                notif_type="fulfillment_completed",
                title="ASN Fully Delivered",
                message=f"ASN {asn_order.asn_order_no} has been fully delivered.",
                warehouse_id=asn_order.warehouse_id_from,
                sender_id=user_id,
            )
            self._create_delivery_stock_entry(asn_order, organization_id, user_id)
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

    # ── notification helpers ─────────────────────────────────────────

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

    # ── stock entry on delivery ─────────────────────────────────────────

    def _create_delivery_stock_entry(
        self,
        asn_order: AsnOrder,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        """Create + submit a material_receipt stock entry when an ASN is delivered.

        Guardrails so stock is never double-counted:
        - Skip when a stock entry already references this ASN.
        - Skip when stock was already received via approved receiving slips
          (receiving + put-away already update stock levels).
        """
        import logging
        from datetime import UTC, datetime

        from app.models.receiving_slip import ReceivingSlip
        from app.models.stock_entry import StockEntry
        from app.schemas.stock_entry import StockEntryCreate, StockEntryItemCreate
        from app.services.stock_entry_service import StockEntryService

        logger = logging.getLogger(__name__)

        # Idempotency: one stock entry per ASN.
        existing = (
            self.db.query(StockEntry)
            .filter(
                StockEntry.organization_id == organization_id,
                StockEntry.reference_type == "asn_order",
                StockEntry.reference_id == asn_order.id,
            )
            .first()
        )
        if existing:
            logger.info(
                "Stock entry already exists for ASN %s (%s) — skipping.",
                asn_order.asn_order_no,
                existing.stock_entry_no,
            )
            return

        # Receiving slips already approved? Then receiving/put-away has already
        # booked the stock at bin + warehouse level — avoid a duplicate receipt.
        received = (
            self.db.query(ReceivingSlip.id)
            .filter(
                ReceivingSlip.asn_order_id == asn_order.id,
                ReceivingSlip.organization_id == organization_id,
                ReceivingSlip.status.in_(["pending_putaway", "putaway_complete"]),
            )
            .first()
        )
        if received:
            logger.info(
                "ASN %s has approved receiving slips — stock already accounted via receiving/put-away; skipping stock entry.",
                asn_order.asn_order_no,
            )
            return

        if not asn_order.warehouse_id_to:
            logger.warning(
                "ASN %s delivered but has no receiving warehouse (warehouse_id_to); skipping stock entry.",
                asn_order.asn_order_no,
            )
            return

        items = [
            StockEntryItemCreate(
                item_id=item.item_id,
                qty=Decimal(str(item.qty or 0)),
                uom=item.uom or "pcs",
            )
            for item in asn_order.items
            if item.item_id and Decimal(str(item.qty or 0)) > 0
        ]
        if not items:
            logger.warning(
                "ASN %s delivered but has no line items; skipping stock entry.",
                asn_order.asn_order_no,
            )
            return

        try:
            svc = StockEntryService(self.db)
            entry = svc.create(
                StockEntryCreate(
                    stock_entry_type="material_receipt",
                    to_warehouse_id=asn_order.warehouse_id_to,
                    posting_date=datetime.now(UTC),
                    reference_type="asn_order",
                    reference_id=asn_order.id,
                    remarks=f"Auto-generated from ASN {asn_order.asn_order_no}",
                    items=items,
                ),
                organization_id,
                user_id,
            )
            svc.submit(entry.id, organization_id, user_id)
            logger.info(
                "Created stock entry %s for ASN %s.",
                entry.stock_entry_no,
                asn_order.asn_order_no,
            )
        except Exception as exc:
            logger.error(
                "Failed to create stock entry for ASN %s: %s",
                asn_order.asn_order_no,
                exc,
                exc_info=True,
            )

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
                "item_name": item.item.item_name if item.item else None,
                "qty": float(item.qty) if item.qty else 0,
                "uom": item.uom,
                "sort_order": item.sort_order,
                "delivered_qty": float(item.delivered_qty) if item.delivered_qty else 0,
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
            "remarks": asn_order.remarks,
            "submitted_at": asn_order.submitted_at,
            "created_by": asn_order.created_by,
            "updated_by": asn_order.updated_by,
            "created_at": asn_order.created_at,
            "updated_at": asn_order.updated_at,
            "from_warehouse": from_warehouse,
            "to_warehouse": to_warehouse,
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
            "from_warehouse": from_warehouse,
            "to_warehouse": to_warehouse,
            "created_at": asn_order.created_at,
        }
