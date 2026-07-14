"""Item Price service for business logic"""

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateItemPriceException,
    ItemNotFoundException,
    ItemPriceNotFoundException,
    ValidationException,
)
from app.models.item_price import ItemPrice
from app.repositories.item_price_repository import ItemPriceRepository
from app.repositories.item_repository import ItemRepository
from app.schemas.item_price import ItemPriceBulkCreate, ItemPriceCreate, ItemPriceUpdate


class ItemPriceService:
    """Service for item price business logic"""

    def __init__(self, db: Session):
        self.db = db
        self.item_price_repo = ItemPriceRepository(db)
        self.item_repo = ItemRepository(db)

    def create_item_price(
        self,
        item_price_data: ItemPriceCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> ItemPrice:
        """
        Create a new item price.

        Args:
            item_price_data: ItemPrice creation data
            organization_id: Organization UUID
            user_id: User UUID creating the item price

        Returns:
            Created ItemPrice object

        Raises:
            ItemNotFoundException: If item not found
            DuplicateItemPriceException: If duplicate price exists
            ValidationException: If validation fails
        """
        # Verify item exists
        item = self.item_repo.get_item_by_id(item_price_data.item_id, organization_id)
        if not item:
            raise ItemNotFoundException(
                f"Item with ID {item_price_data.item_id} not found"
            )

        # Check for duplicate price
        if self.item_price_repo.check_duplicate_price(
            item_id=item_price_data.item_id,
            organization_id=organization_id,
            price_list_id=item_price_data.price_list_id,
            min_qty=item_price_data.min_qty,
            valid_from=item_price_data.valid_from,
            valid_upto=item_price_data.valid_upto,
        ):
            raise DuplicateItemPriceException(
                "A price with the same conditions already exists for this item"
            )

        # Validate date range
        if (
            item_price_data.valid_from
            and item_price_data.valid_upto
            and item_price_data.valid_from >= item_price_data.valid_upto
        ):
            raise ValidationException("valid_from must be before valid_upto")

        # Create item price
        create_data = item_price_data.model_dump()
        create_data.update(
            {
                "organization_id": organization_id,
                "created_by": user_id,
                "updated_by": user_id,
            }
        )

        return self.item_price_repo.create_item_price(create_data)

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
            page: Page number
            page_size: Items per page
            item_id: Filter by item ID
            price_list_id: Filter by price list ID
            currency: Filter by currency
            valid_on: Filter by validity date
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order
            include_item: Whether to include item details

        Returns:
            Tuple of (item_prices_list, pagination_info)
        """
        return self.item_price_repo.get_item_prices(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            item_id=item_id,
            price_list_id=price_list_id,
            currency=currency,
            valid_on=valid_on,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            include_item=include_item,
        )

    def get_item_price_by_id(
        self,
        item_price_id: UUID,
        organization_id: UUID,
        include_item: bool = False,
    ) -> ItemPrice:
        """
        Get item price by ID.

        Args:
            item_price_id: ItemPrice UUID
            organization_id: Organization UUID
            include_item: Whether to include item details

        Returns:
            ItemPrice object

        Raises:
            ItemPriceNotFoundException: If item price not found
        """
        item_price = self.item_price_repo.get_item_price_by_id(
            item_price_id, organization_id, include_item
        )
        if not item_price:
            raise ItemPriceNotFoundException(
                f"Item price with ID {item_price_id} not found"
            )
        return item_price

    def update_item_price(
        self,
        item_price_id: UUID,
        item_price_data: ItemPriceUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> ItemPrice:
        """
        Update an item price.

        Args:
            item_price_id: ItemPrice UUID
            item_price_data: Update data
            organization_id: Organization UUID
            user_id: User UUID updating the item price

        Returns:
            Updated ItemPrice object

        Raises:
            ItemPriceNotFoundException: If item price not found
            DuplicateItemPriceException: If update would create duplicate
            ValidationException: If validation fails
        """
        item_price = self.get_item_price_by_id(item_price_id, organization_id)

        # Prepare update data
        update_data = item_price_data.model_dump(exclude_unset=True)
        if not update_data:
            return item_price

        # Validate date range if both dates are being updated
        valid_from = update_data.get("valid_from", item_price.valid_from)
        valid_upto = update_data.get("valid_upto", item_price.valid_upto)
        if valid_from and valid_upto and valid_from >= valid_upto:
            raise ValidationException("valid_from must be before valid_upto")

        # Check for duplicate if relevant fields are being updated
        duplicate_check_fields = {
            "price_list_id",
            "min_qty",
            "valid_from",
            "valid_upto",
        }
        if any(field in update_data for field in duplicate_check_fields):
            # Get the values that would exist after update
            check_price_list_id = update_data.get(
                "price_list_id", item_price.price_list_id
            )
            check_min_qty = update_data.get("min_qty", item_price.min_qty)
            check_valid_from = update_data.get("valid_from", item_price.valid_from)
            check_valid_upto = update_data.get("valid_upto", item_price.valid_upto)

            if self.item_price_repo.check_duplicate_price(
                item_id=item_price.item_id,
                organization_id=organization_id,
                price_list_id=check_price_list_id,
                min_qty=check_min_qty,
                valid_from=check_valid_from,
                valid_upto=check_valid_upto,
                exclude_id=item_price_id,
            ):
                raise DuplicateItemPriceException(
                    "A price with the same conditions already exists for this item"
                )

        # Add audit fields
        update_data["updated_by"] = user_id

        return self.item_price_repo.update_item_price(item_price, update_data)

    def delete_item_price(
        self,
        item_price_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        """
        Delete an item price.

        Args:
            item_price_id: ItemPrice UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the item price

        Raises:
            ItemPriceNotFoundException: If item price not found
        """
        item_price = self.get_item_price_by_id(item_price_id, organization_id)
        self.item_price_repo.delete_item_price(item_price)

    def get_item_prices_by_item(
        self,
        item_id: UUID,
        organization_id: UUID,
        valid_on: datetime | None = None,
    ) -> list[ItemPrice]:
        """
        Get all item prices for a specific item.

        Args:
            item_id: Item UUID
            organization_id: Organization UUID
            valid_on: Filter by validity date

        Returns:
            List of ItemPrice objects

        Raises:
            ItemNotFoundException: If item not found
        """
        # Verify item exists
        item = self.item_repo.get_item_by_id(item_id, organization_id)
        if not item:
            raise ItemNotFoundException(f"Item with ID {item_id} not found")

        return self.item_price_repo.get_item_prices_by_item(
            item_id, organization_id, valid_on
        )

    def bulk_create_item_prices(
        self,
        bulk_data: ItemPriceBulkCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> tuple[list[ItemPrice], list[dict]]:
        """
        Bulk create item prices.

        Args:
            bulk_data: Bulk creation data
            organization_id: Organization UUID
            user_id: User UUID creating the item prices

        Returns:
            Tuple of (created_item_prices, errors)
        """
        created_item_prices = []
        errors = []

        for i, item_price_data in enumerate(bulk_data.item_prices):
            try:
                item_price = self.create_item_price(
                    item_price_data, organization_id, user_id
                )
                created_item_prices.append(item_price)
            except Exception as e:
                errors.append(
                    {
                        "index": i,
                        "item_id": str(item_price_data.item_id),
                        "error": str(e),
                    }
                )

        return created_item_prices, errors
