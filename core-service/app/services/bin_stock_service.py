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
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.bin_stock_level import BinStockLevel
from app.models.stock_level import StockLevel
from app.models.warehouse_location import WarehouseLocation
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
        )

        # Trigger capacity rollup
        self.capacity_service.recalculate_ancestors(bin_id)

        self.db.commit()
        self.db.refresh(bin_stock)
        return bin_stock

    def remove_stock(
        self,
        bin_id: UUID,
        item_id: UUID,
        quantity: Decimal,
        org_id: UUID,
        batch_number: str | None = None,
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
        )

        # Trigger capacity rollup
        self.capacity_service.recalculate_ancestors(bin_id)

        self.db.commit()
        self.db.refresh(bin_stock)
        return bin_stock

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
            .filter(
                BinStockLevel.bin_location_id == bin_id,
                BinStockLevel.organization_id == org_id,
            )
            .all()
        )

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
    ) -> None:
        """Sync bin-level stock change to the warehouse-level stock_levels table.

        Creates the stock_levels record if it doesn't exist, then adjusts
        quantity_on_hand and quantity_available by the delta.

        Args:
            item_id: The item whose stock changed.
            warehouse_id: The warehouse containing the bin.
            org_id: Organization ID.
            quantity_delta: Positive for additions, negative for removals.
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
        current_reserved = stock_level.quantity_reserved or 0

        new_on_hand = current_on_hand + int_delta
        new_available = max(0, new_on_hand - current_reserved)

        stock_level.quantity_on_hand = new_on_hand
        stock_level.quantity_available = new_available
        self.db.flush()
