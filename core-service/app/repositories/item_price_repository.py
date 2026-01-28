"""Item Price repository for database operations"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, desc, or_
from sqlalchemy.orm import Session, joinedload

from app.models.item_price import ItemPrice


class ItemPriceRepository:
    """Repository for ItemPrice database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_item_price(self, item_price_data: dict) -> ItemPrice:
        """
        Create a new item price.

        Args:
            item_price_data: Dictionary containing item price data

        Returns:
            Created ItemPrice object
        """
        item_price = ItemPrice(**item_price_data)
        self.db.add(item_price)
        self.db.commit()
        self.db.refresh(item_price)
        return item_price

    def get_item_price_by_id(
        self, item_price_id: UUID, organization_id: UUID, include_item: bool = False
    ) -> ItemPrice | None:
        """
        Get item price by ID.

        Args:
            item_price_id: ItemPrice UUID
            organization_id: Organization UUID
            include_item: Whether to include item details

        Returns:
            ItemPrice object or None if not found
        """
        query = self.db.query(ItemPrice).filter(
            and_(
                ItemPrice.id == item_price_id,
                ItemPrice.organization_id == organization_id,
            )
        )

        if include_item:
            query = query.options(joinedload(ItemPrice.item))

        return query.first()

    def get_item_prices(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        item_id: UUID | None = None,
        price_list_id: UUID | None = None,
        currency: str | None = None,
        valid_on: datetime | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_item: bool = False,
    ) -> tuple[list[ItemPrice], dict]:
        """
        Get paginated list of item prices with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Items per page
            item_id: Filter by item ID
            price_list_id: Filter by price list ID
            currency: Filter by currency
            valid_on: Filter by validity date
            search: Search term for item code/name
            sort_by: Field to sort by
            sort_order: Sort order (asc/desc)
            include_item: Whether to include item details

        Returns:
            Tuple of (item_prices_list, pagination_info)
        """
        query = self.db.query(ItemPrice).filter(
            ItemPrice.organization_id == organization_id
        )

        # Apply filters
        if item_id:
            query = query.filter(ItemPrice.item_id == item_id)

        if price_list_id:
            query = query.filter(ItemPrice.price_list_id == price_list_id)

        if currency:
            query = query.filter(ItemPrice.currency.ilike(f"%{currency}%"))

        if valid_on:
            query = query.filter(
                or_(
                    ItemPrice.valid_from.is_(None),
                    ItemPrice.valid_from <= valid_on,
                )
            ).filter(
                or_(
                    ItemPrice.valid_upto.is_(None),
                    ItemPrice.valid_upto >= valid_on,
                )
            )

        if search:
            # Join with item table for searching
            from app.models.item import Item

            query = query.join(Item).filter(
                or_(
                    Item.item_code.ilike(f"%{search}%"),
                    Item.item_name.ilike(f"%{search}%"),
                )
            )

        # Include item details if requested
        if include_item:
            query = query.options(joinedload(ItemPrice.item))

        # Get total count before pagination
        total_items = query.count()

        # Apply sorting
        if hasattr(ItemPrice, sort_by):
            sort_column = getattr(ItemPrice, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(desc(sort_column))
            else:
                query = query.order_by(sort_column)

        # Apply pagination
        offset = (page - 1) * page_size
        item_prices = query.offset(offset).limit(page_size).all()

        # Calculate pagination info
        total_pages = (total_items + page_size - 1) // page_size
        pagination_info = {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return item_prices, pagination_info

    def update_item_price(self, item_price: ItemPrice, update_data: dict) -> ItemPrice:
        """
        Update an item price.

        Args:
            item_price: ItemPrice object to update
            update_data: Dictionary containing update data

        Returns:
            Updated ItemPrice object
        """
        for key, value in update_data.items():
            if hasattr(item_price, key):
                setattr(item_price, key, value)

        self.db.commit()
        self.db.refresh(item_price)
        return item_price

    def delete_item_price(self, item_price: ItemPrice) -> None:
        """
        Delete an item price.

        Args:
            item_price: ItemPrice object to delete
        """
        self.db.delete(item_price)
        self.db.commit()

    def get_item_prices_by_item(
        self, item_id: UUID, organization_id: UUID, valid_on: datetime | None = None
    ) -> list[ItemPrice]:
        """
        Get all item prices for a specific item.

        Args:
            item_id: Item UUID
            organization_id: Organization UUID
            valid_on: Filter by validity date

        Returns:
            List of ItemPrice objects
        """
        query = self.db.query(ItemPrice).filter(
            and_(
                ItemPrice.item_id == item_id,
                ItemPrice.organization_id == organization_id,
            )
        )

        if valid_on:
            query = query.filter(
                or_(
                    ItemPrice.valid_from.is_(None),
                    ItemPrice.valid_from <= valid_on,
                )
            ).filter(
                or_(
                    ItemPrice.valid_upto.is_(None),
                    ItemPrice.valid_upto >= valid_on,
                )
            )

        return query.order_by(desc(ItemPrice.created_at)).all()

    def check_duplicate_price(
        self,
        item_id: UUID,
        organization_id: UUID,
        price_list_id: UUID | None = None,
        min_qty: int | None = None,
        valid_from: datetime | None = None,
        valid_upto: datetime | None = None,
        exclude_id: UUID | None = None,
    ) -> bool:
        """
        Check if a duplicate price exists for the same conditions.

        Args:
            item_id: Item UUID
            organization_id: Organization UUID
            price_list_id: Price list UUID
            min_qty: Minimum quantity
            valid_from: Valid from date
            valid_upto: Valid until date
            exclude_id: ItemPrice ID to exclude from check (for updates)

        Returns:
            True if duplicate exists, False otherwise
        """
        query = self.db.query(ItemPrice).filter(
            and_(
                ItemPrice.item_id == item_id,
                ItemPrice.organization_id == organization_id,
                ItemPrice.price_list_id == price_list_id,
                ItemPrice.min_qty == min_qty,
            )
        )

        if exclude_id:
            query = query.filter(ItemPrice.id != exclude_id)

        # Check for overlapping date ranges
        if valid_from or valid_upto:
            # Complex date range overlap logic
            date_conditions = []

            if valid_from and valid_upto:
                # New range has both start and end
                date_conditions.extend(
                    [
                        # Existing range overlaps with new range
                        and_(
                            or_(
                                ItemPrice.valid_from.is_(None),
                                ItemPrice.valid_from <= valid_upto,
                            ),
                            or_(
                                ItemPrice.valid_upto.is_(None),
                                ItemPrice.valid_upto >= valid_from,
                            ),
                        )
                    ]
                )
            elif valid_from:
                # New range has only start date (open-ended)
                date_conditions.extend(
                    [
                        or_(
                            ItemPrice.valid_upto.is_(None),
                            ItemPrice.valid_upto >= valid_from,
                        )
                    ]
                )
            elif valid_upto:
                # New range has only end date
                date_conditions.extend(
                    [
                        or_(
                            ItemPrice.valid_from.is_(None),
                            ItemPrice.valid_from <= valid_upto,
                        )
                    ]
                )

            if date_conditions:
                query = query.filter(or_(*date_conditions))

        return query.first() is not None

    def bulk_create_item_prices(self, item_prices_data: list[dict]) -> list[ItemPrice]:
        """
        Bulk create item prices.

        Args:
            item_prices_data: List of dictionaries containing item price data

        Returns:
            List of created ItemPrice objects
        """
        item_prices = [ItemPrice(**data) for data in item_prices_data]
        self.db.add_all(item_prices)
        self.db.commit()

        # Refresh all objects
        for item_price in item_prices:
            self.db.refresh(item_price)

        return item_prices
