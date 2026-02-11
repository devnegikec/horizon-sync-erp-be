"""Quotation service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import QuotationStatus
from app.models.quotation import QuotationItem
from app.repositories.quotation_repository import QuotationRepository


class QuotationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QuotationRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        
        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = QuotationStatus(payload["status"])
        
        # Extract items and calculate grand_total
        items_data = payload.pop("items", [])
        grand_total = self._calculate_grand_total(items_data)
        payload["grand_total"] = grand_total
        
        # Create quotation
        quotation = self.repo.create(payload)
        
        # Create quotation items
        for item_data in items_data:
            item_payload = dict(item_data)
            item_payload["organization_id"] = organization_id
            item_payload["quotation_id"] = quotation.id
            # Calculate amount as qty * rate
            item_payload["amount"] = Decimal(str(item_payload["qty"])) * Decimal(str(item_payload["rate"]))
            item = QuotationItem(**item_payload)
            self.db.add(item)
        
        self.db.commit()
        self.db.refresh(quotation)
        return self._to_response(quotation)

    def get_by_id(self, quotation_id: UUID, organization_id: UUID) -> dict:
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")
        return self._to_response(quotation)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "quotation_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_quotations(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            status=status,
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
        self, quotation_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")
        
        # Prevent line item modifications when status is SENT
        if "items" in data and quotation.status == QuotationStatus.SENT:
            raise ValueError(
                "Cannot modify line items when quotation status is SENT"
            )
        
        payload = {k: v for k, v in data.items() if v is not None and k != "items"}
        
        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = QuotationStatus(payload["status"])
        
        payload["updated_by"] = user_id
        
        # Handle items update if provided
        if "items" in data:
            items_data = data["items"]
            
            # Delete existing items
            for item in quotation.items:
                self.db.delete(item)
            
            # Create new items
            for item_data in items_data:
                item_payload = dict(item_data)
                item_payload["organization_id"] = organization_id
                item_payload["quotation_id"] = quotation.id
                # Calculate amount as qty * rate
                item_payload["amount"] = Decimal(str(item_payload["qty"])) * Decimal(str(item_payload["rate"]))
                item = QuotationItem(**item_payload)
                self.db.add(item)
            
            # Recalculate grand_total
            payload["grand_total"] = self._calculate_grand_total(items_data)
        
        self.repo.update(quotation, payload)
        self.db.refresh(quotation)
        return self._to_response(quotation)

    def delete(self, quotation_id: UUID, organization_id: UUID) -> None:
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")
        self.repo.delete(quotation)

    def update_status(
        self, quotation_id: UUID, new_status: str, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Update quotation status with validation.

        Args:
            quotation_id: ID of the quotation to update
            new_status: New status value (string)
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Updated quotation as dict

        Raises:
            ResourceNotFoundException: If quotation not found
            ValueError: If status transition is invalid
        """
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")

        # Convert string to enum
        new_status_enum = QuotationStatus(new_status)

        # Validate status transition
        self._validate_status_transition(quotation.status, new_status_enum)

        # Prepare update payload
        payload = {
            "status": new_status_enum,
            "updated_by": user_id,
        }

        # Set submitted_at when status changes to SENT
        if new_status_enum == QuotationStatus.SENT and quotation.submitted_at is None:
            from datetime import UTC, datetime
            payload["submitted_at"] = datetime.now(UTC)

        # Update quotation
        self.repo.update(quotation, payload)
        self.db.refresh(quotation)
        return self._to_response(quotation)

    def _calculate_grand_total(self, items: list[dict]) -> Decimal:
        """Calculate grand total from line items"""
        total = Decimal("0")
        for item in items:
            qty = Decimal(str(item.get("qty", 0)))
            rate = Decimal(str(item.get("rate", 0)))
            total += qty * rate
        return total
    def convert_to_sales_order(
        self, quotation_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Convert an accepted quotation to a sales order.

        Args:
            quotation_id: ID of the quotation to convert
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Created sales order as dict

        Raises:
            ResourceNotFoundException: If quotation not found
            ValueError: If quotation status is not ACCEPTED
        """
        from datetime import UTC, datetime
        from app.services.sales_order_service import SalesOrderService
        
        # Get the quotation
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")
        
        # Validate quotation status is ACCEPTED
        if quotation.status != QuotationStatus.ACCEPTED:
            raise ValueError(
                f"Cannot convert quotation with status {quotation.status.value}. "
                "Only ACCEPTED quotations can be converted to sales orders."
            )
        
        # Use database transaction for atomicity
        try:
            # Generate sales order number from quotation number
            # Replace QTN prefix with SO prefix, or generate new number
            if quotation.quotation_no.startswith("QTN"):
                sales_order_no = quotation.quotation_no.replace("QTN", "SO", 1)
            else:
                # Fallback: generate based on timestamp
                timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
                sales_order_no = f"SO-{timestamp}"
            
            # Prepare sales order data
            sales_order_data = {
                "sales_order_no": sales_order_no,
                "customer_id": quotation.customer_id,
                "order_date": datetime.now(UTC),
                "delivery_date": None,
                "currency": quotation.currency,
                "reference_type": "Quotation",
                "reference_id": quotation.id,
                "remarks": quotation.remarks,
                "items": [
                    {
                        "item_id": item.item_id,
                        "qty": item.qty,
                        "uom": item.uom,
                        "rate": item.rate,
                        "amount": item.amount,
                        "sort_order": item.sort_order,
                    }
                    for item in quotation.items
                ],
            }
            
            # Create sales order using SalesOrderService
            sales_order_service = SalesOrderService(self.db)
            sales_order = sales_order_service.create(
                sales_order_data, organization_id, user_id
            )
            
            return sales_order
            
        except Exception as e:
            # Rollback is handled by the session
            self.db.rollback()
            raise e

    def _validate_status_transition(
        self, current_status: QuotationStatus, new_status: QuotationStatus
    ) -> None:
        """
        Validate quotation status transitions.

        Valid workflow: DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED
        Terminal states (ACCEPTED, REJECTED, EXPIRED) cannot transition further.

        Args:
            current_status: Current quotation status
            new_status: Requested new status

        Raises:
            ValueError: If the status transition is invalid
        """
        # Terminal states cannot transition
        terminal_states = {
            QuotationStatus.ACCEPTED,
            QuotationStatus.REJECTED,
            QuotationStatus.EXPIRED,
        }
        if current_status in terminal_states:
            raise ValueError(
                f"Cannot change status from terminal state {current_status.value}"
            )

        # Define valid transitions
        valid_transitions = {
            QuotationStatus.DRAFT: {QuotationStatus.SENT},
            QuotationStatus.SENT: {
                QuotationStatus.ACCEPTED,
                QuotationStatus.REJECTED,
                QuotationStatus.EXPIRED,
            },
        }

        # Check if transition is valid
        allowed_next_states = valid_transitions.get(current_status, set())
        if new_status not in allowed_next_states:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}. "
                f"Allowed transitions: {', '.join(s.value for s in allowed_next_states)}"
            )


    @staticmethod
    def _to_response(quotation) -> dict:
        return {
            "id": quotation.id,
            "organization_id": quotation.organization_id,
            "quotation_no": quotation.quotation_no,
            "customer_id": quotation.customer_id,
            "quotation_date": quotation.quotation_date,
            "valid_until": quotation.valid_until,
            "status": quotation.status.value if quotation.status else None,
            "grand_total": quotation.grand_total,
            "currency": quotation.currency,
            "remarks": quotation.remarks,
            "submitted_at": quotation.submitted_at,
            "extra_data": quotation.extra_data,
            "created_by": quotation.created_by,
            "updated_by": quotation.updated_by,
            "created_at": quotation.created_at,
            "updated_at": quotation.updated_at,
            "items": [
                {
                    "id": item.id,
                    "item_id": item.item_id,
                    "qty": item.qty,
                    "uom": item.uom,
                    "rate": item.rate,
                    "amount": item.amount,
                    "sort_order": item.sort_order,
                    "extra_data": item.extra_data,
                }
                for item in quotation.items
            ],
        }

    @staticmethod
    def _to_list_item(quotation) -> dict:
        return {
            "id": quotation.id,
            "organization_id": quotation.organization_id,
            "quotation_no": quotation.quotation_no,
            "customer_id": quotation.customer_id,
            "quotation_date": quotation.quotation_date,
            "status": quotation.status.value if quotation.status else None,
            "grand_total": quotation.grand_total,
            "currency": quotation.currency,
            "created_at": quotation.created_at,
        }
