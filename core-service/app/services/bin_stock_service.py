"""Bin stock service for tracking stock at the bin level and maintaining consistency
with warehouse-level stock.

Handles:
- Adding stock to bins with capacity checks
- Removing stock from bins with on-hand validation
- Syncing bin-level changes to warehouse-level stock_levels
- Triggering capacity rollup on stock changes
- Rejecting operations on deactivated locations

Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 18.1, 18.2
"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.base import MovementType
from app.models.bin_stock_level import (
    BinStockLevel,
    InventoryStatus,
    can_transition_inventory_status,
)
from app.models.status_transition import StatusTransition
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_capacity_service import BinCapacityService
from app.services.capacity_service import CapacityService


class BinStockService:
    """Service for managing bin-level stock with capacity enforcement and rollup."""

    def __init__(self, db: Session):
        self.db = db
        self.capacity_service = CapacityService(db)

    def add_stock(
        self,
        bin_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        org_id: UUID,
        batch_number: str | None = None,
        *,
        commit: bool = True,
    ) -> BinStockLevel:
        """Add stock to a bin location.

        Validates:
        - Bin exists and belongs to the organization
        - Bin is active (not deactivated)
        - Bin is of type 'bin'
        - Adding quantity won't exceed bin capacity

        After adding:
        - Creates or updates the BinStockLevel record
        - Syncs the warehouse-level stock_levels record
        - Triggers capacity rollup via CapacityService

        Args:
            bin_id: The bin location ID to add stock to.
            item_id: The item being stocked.
            quantity: The quantity to add (must be positive).
            org_id: Organization ID for scoping.
            batch_number: Optional batch number for the stock.

        Returns:
            The created or updated BinStockLevel record.

        Raises:
            ValidationError: If quantity is invalid or capacity would be exceeded.
            NotFoundError: If bin location is not found.
            StateError: If bin is deactivated.
        """
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        # Get and validate the bin location
        bin_location = self._get_active_bin(bin_id, org_id)

        # Check capacity won't be exceeded (skip if capacity is 0 = unlimited)
        bin_capacity = Decimal(str(bin_location.capacity or 0))
        current_stock_in_bin = Decimal("0")
        if bin_capacity > 0:
            current_stock_in_bin = self._get_total_stock_in_bin(bin_id)
            available_capacity = bin_capacity - current_stock_in_bin
            if quantity > available_capacity:
                raise ValidationError(
                    f"Cannot add {quantity} to bin '{bin_location.full_path}'. "
                    f"Available capacity is {available_capacity} "
                    f"(total capacity: {bin_capacity}, current stock: {current_stock_in_bin})"
                )

        # Create or update the BinStockLevel record
        bin_stock = self._get_or_create_bin_stock(
            bin_id=bin_id,
            item_id=item_id,
            org_id=org_id,
            batch_number=batch_number,
        )
        bin_stock.quantity_on_hand = (
            Decimal(str(bin_stock.quantity_on_hand or 0)) + quantity
        )
        self.db.flush()

        # Update the bin's own available_capacity (recalculate_ancestors only walks up)
        if bin_capacity > 0:
            bin_location.available_capacity = bin_capacity - (
                current_stock_in_bin + quantity
            )
        bin_location.version = (bin_location.version or 1) + 1
        self.db.flush()

        # Sync warehouse-level stock_levels
        self._sync_warehouse_stock(
            item_id=item_id,
            warehouse_id=bin_location.warehouse_id,
            org_id=org_id,
            quantity_delta=quantity,
            quantity_available_delta=quantity
            if bin_location.is_pickable
            else Decimal("0"),
        )

        # Trigger capacity rollup
        self.capacity_service.recalculate_ancestors(bin_id)
        # Refresh bin volume/weight capacity + 3-D state (mobile-app trigger point)
        BinCapacityService(self.db).refresh_bin(bin_id, org_id)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(bin_stock)
        return bin_stock

    def bulk_add_stock(
        self,
        bin_id: UUID,
        items: list[dict],
        org_id: UUID,
    ) -> dict:
        """Add multiple items to a single bin in one transaction.

        Each item dict must have:
            - item_id (UUID)
            - quantity (Decimal)
            - batch_number (str | None, optional)

        Each item is processed independently — a failure for one item does not
        roll back successful items. The response includes per-item status.

        Args:
            bin_id: The bin location ID to add stock to.
            items: List of item dicts with item_id, quantity, batch_number.
            org_id: Organization ID for scoping.

        Returns:
            dict with keys:
                - bin_id: UUID of the bin
                - added: count of successfully added items
                - errors: count of failed items
                - items: list of per-item results (status, error, bin_stock_level)
        """
        # Validate the bin once upfront
        try:
            bin_location = self._get_active_bin(bin_id, org_id)
        except (NotFoundError, StateError, ValidationError) as e:
            # Bin itself is invalid — fail all items
            return {
                "bin_id": bin_id,
                "added": 0,
                "errors": len(items),
                "items": [
                    {
                        "item_id": item["item_id"],
                        "quantity": item["quantity"],
                        "batch_number": item.get("batch_number"),
                        "status": "error",
                        "error": str(e.detail if hasattr(e, "detail") else str(e)),
                        "bin_stock_level": None,
                    }
                    for item in items
                ],
            }

        bin_capacity = Decimal(str(bin_location.capacity or 0))
        current_stock_in_bin = self._get_total_stock_in_bin(bin_id)

        results = []
        added_count = 0
        error_count = 0

        for item in items:
            item_id = item["item_id"]
            quantity = Decimal(str(item["quantity"]))
            batch_number = item.get("batch_number")

            try:
                # Validate quantity
                if quantity <= 0:
                    raise ValidationError("Quantity must be positive")

                # Check capacity (cumulative across items in this batch)
                if bin_capacity > 0:
                    available = bin_capacity - current_stock_in_bin
                    if quantity > available:
                        raise ValidationError(
                            f"Cannot add {quantity}. Available capacity: {available} "
                            f"(total: {bin_capacity}, current: {current_stock_in_bin})"
                        )

                # Create or update the BinStockLevel record
                bin_stock = self._get_or_create_bin_stock(
                    bin_id=bin_id,
                    item_id=item_id,
                    org_id=org_id,
                    batch_number=batch_number,
                )
                bin_stock.quantity_on_hand = (
                    Decimal(str(bin_stock.quantity_on_hand or 0)) + quantity
                )
                self.db.flush()

                # Track cumulative stock for capacity checks
                current_stock_in_bin += quantity

                # Sync warehouse-level stock
                self._sync_warehouse_stock(
                    item_id=item_id,
                    warehouse_id=bin_location.warehouse_id,
                    org_id=org_id,
                    quantity_delta=quantity,
                )

                self.db.refresh(bin_stock)
                results.append(
                    {
                        "item_id": item_id,
                        "quantity": quantity,
                        "batch_number": batch_number,
                        "status": "added",
                        "error": None,
                        "bin_stock_level": bin_stock,
                    }
                )
                added_count += 1

            except (ValidationError, NotFoundError) as e:
                self.db.rollback()
                error_msg = e.detail if hasattr(e, "detail") else str(e)
                results.append(
                    {
                        "item_id": item_id,
                        "quantity": quantity,
                        "batch_number": batch_number,
                        "status": "error",
                        "error": error_msg,
                        "bin_stock_level": None,
                    }
                )
                error_count += 1

        # Update bin's available_capacity and version
        bin_location.available_capacity = (
            bin_capacity - current_stock_in_bin if bin_capacity > 0 else Decimal("0")
        )
        bin_location.version = (bin_location.version or 1) + 1
        self.db.flush()

        # Trigger capacity rollup for ancestors (once for all items)
        if added_count > 0:
            self.capacity_service.recalculate_ancestors(bin_id)
            BinCapacityService(self.db).refresh_bin(bin_id, org_id)

        self.db.commit()

        return {
            "bin_id": bin_id,
            "added": added_count,
            "errors": error_count,
            "items": results,
        }

    def remove_stock(
        self,
        bin_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        org_id: UUID,
        batch_number: str | None = None,
        *,
        commit: bool = True,
    ) -> BinStockLevel:
        """Remove stock from a bin location.

        Validates:
        - Bin exists and belongs to the organization
        - Bin is active (not deactivated)
        - Sufficient on-hand quantity exists for the item in the bin

        After removing:
        - Decrements the BinStockLevel record
        - Syncs the warehouse-level stock_levels record
        - Triggers capacity rollup via CapacityService

        Args:
            bin_id: The bin location ID to remove stock from.
            item_id: The item being removed.
            quantity: The quantity to remove (must be positive).
            org_id: Organization ID for scoping.
            batch_number: Optional batch number for the stock.

        Returns:
            The updated BinStockLevel record.

        Raises:
            ValidationError: If quantity is invalid or insufficient stock.
            NotFoundError: If bin location or stock record is not found.
            StateError: If bin is deactivated.
        """
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")

        # Get and validate the bin location
        bin_location = self._get_active_bin(bin_id, org_id)

        # Find the bin stock record
        bin_stock = self._get_bin_stock_record(
            bin_id=bin_id,
            item_id=item_id,
            org_id=org_id,
            batch_number=batch_number,
        )

        if bin_stock is None:
            raise NotFoundError(
                f"No stock record found for item in bin '{bin_location.full_path}'",
                entity_type="BinStockLevel",
                entity_id=f"bin={bin_id}, item={item_id}",
            )

        current_qty = Decimal(str(bin_stock.quantity_on_hand or 0))
        if quantity > current_qty:
            raise ValidationError(
                f"Cannot remove {quantity} from bin '{bin_location.full_path}'. "
                f"Only {current_qty} on hand for this item."
            )

        # Decrement the stock
        bin_stock.quantity_on_hand = current_qty - quantity
        self.db.flush()

        # Update the bin's own available_capacity (recalculate_ancestors only walks up)
        bin_capacity = Decimal(str(bin_location.capacity or 0))
        bin_location.available_capacity = bin_capacity - (current_qty - quantity)
        bin_location.version = (bin_location.version or 1) + 1
        self.db.flush()

        # Sync warehouse-level stock_levels (negative delta)
        self._sync_warehouse_stock(
            item_id=item_id,
            warehouse_id=bin_location.warehouse_id,
            org_id=org_id,
            quantity_delta=-quantity,
            quantity_available_delta=-quantity
            if bin_location.is_pickable
            else Decimal("0"),
        )

        # Trigger capacity rollup
        self.capacity_service.recalculate_ancestors(bin_id)
        # Refresh bin volume/weight capacity + 3-D state (mobile-app trigger point)
        BinCapacityService(self.db).refresh_bin(bin_id, org_id)

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        self.db.refresh(bin_stock)
        return bin_stock

    def transition_status(
        self,
        bin_stock: BinStockLevel,
        new_status: str,
        *,
        user_id: UUID | None = None,
        commit: bool = True,
    ) -> BinStockLevel:
        """Advance a bin stock record through the pick status machine.

        Validates ``available → picked → in_transit_to_stage`` (WF-016 / T-09).
        A same-status call is a no-op (replay-safe). Every actual transition is
        audited via a ``StatusTransition`` row.

        Raises:
            ValidationError: if ``current → new_status`` is not allowed.
        """
        current = bin_stock.inventory_status or InventoryStatus.AVAILABLE.value
        if current == new_status:
            return bin_stock  # idempotent no-op

        if not can_transition_inventory_status(current, new_status):
            raise ValidationError(
                f"Invalid inventory status transition: '{current}' -> '{new_status}'"
            )

        bin_stock.inventory_status = new_status
        if user_id is not None:
            self.db.add(
                StatusTransition(
                    entity_type="bin_stock_level",
                    entity_id=bin_stock.id,
                    previous_status=current,
                    new_status=new_status,
                    user_id=user_id,
                )
            )

        if commit:
            self.db.commit()
        else:
            self.db.flush()
        return bin_stock

    def record_pick_movement(
        self,
        *,
        org_id: UUID,
        product_id: UUID,
        warehouse_id: UUID,
        quantity: Decimal,
        reference_type: str,
        reference_id: UUID,
        performed_by: UUID | None = None,
        notes: str | None = None,
    ) -> StockMovement | None:
        """Post an idempotent OUT movement ledger entry for a pick (WF-016).

        A movement is only written once per (reference_type, reference_id);
        a replay returns ``None`` without double-posting.
        """
        existing = (
            self.db.query(StockMovement)
            .filter(
                StockMovement.organization_id == org_id,
                StockMovement.reference_type == reference_type,
                StockMovement.reference_id == reference_id,
            )
            .first()
        )
        if existing is not None:
            return None

        movement = StockMovement(
            organization_id=org_id,
            product_id=product_id,
            warehouse_id=warehouse_id,
            movement_type=MovementType.OUT,
            quantity=int(quantity),
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            performed_by=performed_by,
        )
        self.db.add(movement)
        self.db.flush()
        return movement

    def transfer_stock(
        self,
        *,
        from_bin_id: UUID,
        to_bin_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        org_id: UUID,
        batch_number: str | None = None,
    ) -> BinStockLevel:
        """Atomically move physical stock between bins without changing on-hand.

        Availability changes only when the source and destination have different
        pickability. This is the receiving-stage → storage and hold/quarantine
        → receiving-stage primitive used by inbound exception disposition.
        """
        if from_bin_id == to_bin_id:
            existing = self._get_bin_stock_record(
                from_bin_id, item_id, org_id, batch_number
            )
            if existing is None:
                raise NotFoundError(
                    "No stock record found for source bin",
                    entity_type="BinStockLevel",
                    entity_id=f"bin={from_bin_id}, item={item_id}",
                )
            return existing

        source = self._get_active_bin(from_bin_id, org_id)
        target = self._get_active_bin(to_bin_id, org_id)
        if source.warehouse_id != target.warehouse_id:
            raise ValidationError(
                "Stock transfers must remain within the same warehouse"
            )

        try:
            self.remove_stock(
                from_bin_id, item_id, quantity, org_id, batch_number, commit=False
            )
            moved = self.add_stock(
                to_bin_id, item_id, quantity, org_id, batch_number, commit=False
            )
            self.db.commit()
            self.db.refresh(moved)
            return moved
        except Exception:
            self.db.rollback()
            raise

    def get_bins_for_item(
        self,
        item_id: UUID,
        org_id: UUID,
    ) -> list[dict]:
        """Return all bins containing a specific item with quantities and available capacity.

        Args:
            item_id: The item to search for.
            org_id: Organization ID for scoping.

        Returns:
            List of dicts with bin info, quantity, and available capacity.
        """
        bin_stocks = (
            self.db.query(BinStockLevel)
            .filter(
                BinStockLevel.item_id == item_id,
                BinStockLevel.organization_id == org_id,
                BinStockLevel.quantity_on_hand > 0,
            )
            .all()
        )

        results = []
        for bs in bin_stocks:
            bin_location = (
                self.db.query(WarehouseLocation)
                .filter(WarehouseLocation.id == bs.bin_location_id)
                .first()
            )
            if bin_location is None:
                continue

            total_stock_in_bin = self._get_total_stock_in_bin(bs.bin_location_id)
            bin_capacity = Decimal(str(bin_location.capacity or 0))
            available_capacity = bin_capacity - total_stock_in_bin

            results.append(
                {
                    "bin_location_id": bs.bin_location_id,
                    "bin_code": bin_location.full_path,
                    "bin_name": bin_location.name,
                    "warehouse_id": bin_location.warehouse_id,
                    "item_id": bs.item_id,
                    "quantity_on_hand": bs.quantity_on_hand,
                    "inventory_status": bs.inventory_status,
                    "batch_number": bs.batch_number,
                    "bin_capacity": bin_capacity,
                    "available_capacity": available_capacity,
                    "is_active": bin_location.is_active,
                    "created_at": bs.created_at,
                }
            )

        return results

    def get_bin_stock(
        self,
        bin_id: UUID,
        org_id: UUID,
    ) -> list[BinStockLevel]:
        """Return all stock records for a specific bin.

        Args:
            bin_id: The bin location to query.
            org_id: Organization ID for scoping.

        Returns:
            List of BinStockLevel records for the bin.

        Raises:
            NotFoundError: If bin location is not found.
        """
        # Validate the bin exists
        bin_location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == bin_id,
                WarehouseLocation.organization_id == org_id,
            )
            .first()
        )

        if bin_location is None:
            raise NotFoundError(
                f"Bin location with ID '{bin_id}' not found",
                entity_type="WarehouseLocation",
                entity_id=str(bin_id),
            )

        return (
            self.db.query(BinStockLevel)
            .options(joinedload(BinStockLevel.item))
            .filter(
                BinStockLevel.bin_location_id == bin_id,
                BinStockLevel.organization_id == org_id,
            )
            .all()
        )

    def get_parent_boxes(self, bin_id: UUID, org_id: UUID) -> list[dict]:
        """Return the parent (master-pack) boxes present in a bin, with children.

        Child units are stored in ``bin_stock_levels`` with ``batch_number`` set
        to the child serial. Each child links to its parent box through
        ``qseal_parameters.parent_id`` → ``qseal_tracks``. Children are grouped
        under their parent so the warehouse manager gets a box-level view with
        the individual child units nested inside.
        """
        from app.models.qseal import QSealParameters, QSealTrack

        # Validate the bin exists for this organization.
        bin_location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == bin_id,
                WarehouseLocation.organization_id == org_id,
            )
            .first()
        )
        if bin_location is None:
            raise NotFoundError(
                f"Bin location with ID '{bin_id}' not found",
                entity_type="WarehouseLocation",
                entity_id=str(bin_id),
            )

        rows = (
            self.db.query(
                QSealTrack.id,
                QSealTrack.serial_number,
                QSealTrack.name,
                QSealTrack.capacity,
                QSealParameters.serial_number,
                QSealParameters.manufacturing_date,
                QSealParameters.expiry_date,
                QSealParameters.dispatch_batch,
                BinStockLevel.item_id,
                BinStockLevel.quantity_on_hand,
                BinStockLevel.inventory_status,
                BinStockLevel.batch_number,
            )
            .join(QSealParameters, QSealParameters.parent_id == QSealTrack.id)
            .join(
                BinStockLevel,
                BinStockLevel.batch_number == QSealParameters.serial_number,
            )
            .filter(
                BinStockLevel.bin_location_id == bin_id,
                BinStockLevel.organization_id == org_id,
                BinStockLevel.quantity_on_hand > 0,
                QSealParameters.organization_id == org_id,
                QSealTrack.organization_id == org_id,
            )
            .order_by(
                QSealTrack.name,
                QSealTrack.serial_number,
                QSealParameters.serial_number,
            )
            .all()
        )

        parents: dict[UUID, dict] = {}
        for row in rows:
            parent_id = row[0]
            parent = parents.get(parent_id)
            if parent is None:
                parent = {
                    "parent_id": row[0],
                    "parent_serial": row[1],
                    "parent_name": row[2],
                    "capacity": row[3],
                    "quantity_on_hand": Decimal("0"),
                    "children": [],
                }
                parents[parent_id] = parent

            qty = Decimal(str(row[9])) if row[9] is not None else Decimal("0")
            parent["quantity_on_hand"] += qty
            parent["children"].append(
                {
                    "serial_number": row[4],
                    "manufacturing_date": row[5],
                    "expiry_date": row[6],
                    "dispatch_batch": row[7],
                    "item_id": row[8],
                    "quantity_on_hand": qty,
                    "inventory_status": row[10],
                    "batch_number": row[11],
                }
            )

        result = []
        for parent in parents.values():
            parent["child_units_in_bin"] = len(parent["children"])
            result.append(parent)
        return result

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _get_active_bin(self, bin_id: UUID, org_id: UUID) -> WarehouseLocation:
        """Get a bin location, validating it exists, is active, and is type 'bin'.

        Raises:
            NotFoundError: If bin not found.
            StateError: If bin is deactivated.
            ValidationError: If location is not of type 'bin'.
        """
        bin_location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == bin_id,
                WarehouseLocation.organization_id == org_id,
            )
            .first()
        )

        if bin_location is None:
            raise NotFoundError(
                f"Bin location with ID '{bin_id}' not found",
                entity_type="WarehouseLocation",
                entity_id=str(bin_id),
            )

        if not bin_location.is_active:
            raise StateError(
                f"Cannot perform stock operations on deactivated location "
                f"'{bin_location.full_path}'. Reactivate the location first.",
                current_state="deactivated",
                required_state=["active"],
            )

        if bin_location.location_type != "bin":
            raise ValidationError(
                f"Location '{bin_location.full_path}' is of type "
                f"'{bin_location.location_type}', not 'bin'. "
                f"Stock can only be added to bin-level locations."
            )

        return bin_location

    def _get_total_stock_in_bin(self, bin_id: UUID) -> Decimal:
        """Get the total quantity of all items currently in a bin."""
        total = (
            self.db.query(
                func.coalesce(func.sum(BinStockLevel.quantity_on_hand), Decimal("0"))
            )
            .filter(BinStockLevel.bin_location_id == bin_id)
            .scalar()
        ) or Decimal("0")
        return Decimal(str(total))

    def _get_or_create_bin_stock(
        self,
        bin_id: UUID,
        item_id: UUID,
        org_id: UUID,
        batch_number: str | None = None,
    ) -> BinStockLevel:
        """Get an existing BinStockLevel or create a new one."""
        query = self.db.query(BinStockLevel).filter(
            BinStockLevel.bin_location_id == bin_id,
            BinStockLevel.item_id == item_id,
            BinStockLevel.organization_id == org_id,
        )

        if batch_number is not None:
            query = query.filter(BinStockLevel.batch_number == batch_number)
        else:
            query = query.filter(BinStockLevel.batch_number.is_(None))

        bin_stock = query.first()

        if bin_stock is None:
            bin_stock = BinStockLevel(
                bin_location_id=bin_id,
                item_id=item_id,
                organization_id=org_id,
                batch_number=batch_number,
                quantity_on_hand=Decimal("0"),
                inventory_status=InventoryStatus.AVAILABLE.value,
            )
            self.db.add(bin_stock)
            self.db.flush()

        return bin_stock

    def _get_bin_stock_record(
        self,
        bin_id: UUID,
        item_id: UUID,
        org_id: UUID,
        batch_number: str | None = None,
    ) -> BinStockLevel | None:
        """Get a specific BinStockLevel record."""
        query = self.db.query(BinStockLevel).filter(
            BinStockLevel.bin_location_id == bin_id,
            BinStockLevel.item_id == item_id,
            BinStockLevel.organization_id == org_id,
        )

        if batch_number is not None:
            query = query.filter(BinStockLevel.batch_number == batch_number)
        else:
            query = query.filter(BinStockLevel.batch_number.is_(None))

        return query.first()

    def _sync_warehouse_stock(
        self,
        item_id: UUID,
        warehouse_id: UUID,
        org_id: UUID,
        quantity_delta: Decimal,
        quantity_available_delta: Decimal | None = None,
    ) -> None:
        """Sync bin-level stock change to the warehouse-level stock_levels table.

        Creates the stock_levels record if it doesn't exist, then adjusts
        quantity_on_hand and quantity_available by the delta.

        Args:
            item_id: The item whose stock changed.
            warehouse_id: The warehouse containing the bin.
            org_id: Organization ID.
        quantity_delta: Positive for additions, negative for removals.
        quantity_available_delta: Availability impact. Stock in non-pickable
            bins changes on-hand but not ATP.
        """
        # Get or create the warehouse-level stock record
        stock_level = (
            self.db.query(StockLevel)
            .filter(
                StockLevel.product_id == item_id,
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.organization_id == org_id,
            )
            .first()
        )

        if stock_level is None:
            stock_level = StockLevel(
                organization_id=org_id,
                product_id=item_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                quantity_available=0,
            )
            self.db.add(stock_level)
            self.db.flush()

        # Apply the delta
        int_delta = int(quantity_delta)
        current_on_hand = stock_level.quantity_on_hand or 0

        new_on_hand = current_on_hand + int_delta
        available_delta = int(
            quantity_available_delta
            if quantity_available_delta is not None
            else quantity_delta
        )
        current_available = stock_level.quantity_available or 0
        new_available = max(0, current_available + available_delta)

        stock_level.quantity_on_hand = new_on_hand
        stock_level.quantity_available = new_available
        self.db.flush()
