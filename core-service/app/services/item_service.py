"""Item service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateItemCodeException, ItemNotFoundException
from app.events.publisher import get_event_publisher
from app.models.base import ItemStatus, ItemType, ValuationMethod
from app.models.item import Item
from app.repositories.item_repository import ItemRepository
from app.schemas.item import ItemCreate, ItemUpdate

logger = logging.getLogger(__name__)


class ItemService:
    """Service for item operations"""

    def __init__(self, db: Session):
        self.db = db
        self.item_repo = ItemRepository(db)

    def create_item(
        self,
        item_data: ItemCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Item:
        """
        Create a new item.

        Args:
            item_data: Item creation data
            organization_id: Organization UUID
            user_id: User UUID creating the item

        Returns:
            Created Item object

        Raises:
            DuplicateItemCodeException: If item code already exists
        """
        # Check if item code already exists
        if self.item_repo.item_code_exists(item_data.item_code, organization_id):
            raise DuplicateItemCodeException(
                f"Item with code '{item_data.item_code}' already exists"
            )

        # Convert enum strings to enum values
        item_dict = item_data.model_dump()
        item_dict["organization_id"] = organization_id
        item_dict["created_by"] = user_id
        item_dict["updated_by"] = user_id

        # Convert string enums to actual enums (case-insensitive)
        if item_dict.get("item_type"):
            try:
                # Normalize to uppercase for enum lookup
                item_type_str = str(item_dict["item_type"]).upper()
                item_dict["item_type"] = ItemType(item_type_str)
            except (ValueError, KeyError):
                item_dict["item_type"] = ItemType.STOCK

        if item_dict.get("status"):
            try:
                # Normalize to uppercase for enum lookup
                status_str = str(item_dict["status"]).upper()
                item_dict["status"] = ItemStatus(status_str)
            except (ValueError, KeyError):
                item_dict["status"] = ItemStatus.ACTIVE

        if item_dict.get("valuation_method"):
            try:
                valuation_method_str = str(item_dict["valuation_method"]).lower()
                item_dict["valuation_method"] = ValuationMethod(valuation_method_str)
            except (ValueError, KeyError):
                item_dict["valuation_method"] = ValuationMethod.FIFO

        # Create item
        item = self.item_repo.create_item(item_dict)
        
        # Publish entity created event
        try:
            event_publisher = get_event_publisher()
            # Convert SQLAlchemy model to dict
            item_data = {k: v for k, v in item.__dict__.items() if not k.startswith('_')}
            event_publisher.publish_entity_created(
                entity_type="items",
                entity_id=str(item.id),
                organization_id=str(organization_id),
                data=item_data
            )
        except Exception as e:
            logger.error(f"Failed to publish item created event: {e}")
        
        return item

    def get_item_by_id(
        self,
        item_id: UUID,
        organization_id: UUID,
        include_group: bool = True,
    ) -> Item:
        """
        Get item by ID.

        Args:
            item_id: Item UUID
            organization_id: Organization UUID
            include_group: Whether to include item_group relationship

        Returns:
            Item object

        Raises:
            ItemNotFoundException: If item not found
        """
        item = self.item_repo.get_item_by_id(
            item_id, organization_id, include_group=include_group
        )
        if not item:
            raise ItemNotFoundException(f"Item with ID {item_id} not found")
        return item

    def update_item(
        self,
        item_id: UUID,
        item_data: ItemUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Item:
        """
        Update an item.

        Args:
            item_id: Item UUID
            item_data: Item update data
            organization_id: Organization UUID
            user_id: User UUID updating the item

        Returns:
            Updated Item object

        Raises:
            ItemNotFoundException: If item not found
        """
        item = self.item_repo.get_item_by_id(item_id, organization_id)
        if not item:
            raise ItemNotFoundException(f"Item with ID {item_id} not found")

        # Prepare update data
        update_dict = item_data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = user_id

        # Convert string enums to actual enums (case-insensitive)
        if "item_type" in update_dict and update_dict["item_type"]:
            try:
                # Normalize to uppercase for enum lookup
                item_type_str = str(update_dict["item_type"]).upper()
                update_dict["item_type"] = ItemType(item_type_str)
            except (ValueError, KeyError):
                del update_dict["item_type"]

        if "status" in update_dict and update_dict["status"]:
            try:
                # Normalize to uppercase for enum lookup
                status_str = str(update_dict["status"]).upper()
                update_dict["status"] = ItemStatus(status_str)
            except (ValueError, KeyError):
                del update_dict["status"]

        if "valuation_method" in update_dict and update_dict["valuation_method"]:
            try:
                valuation_method_str = str(update_dict["valuation_method"]).lower()
                update_dict["valuation_method"] = ValuationMethod(valuation_method_str)
            except (ValueError, KeyError):
                del update_dict["valuation_method"]

        # Update item
        updated_item = self.item_repo.update_item(item, update_dict)
        
        # Publish entity updated event
        try:
            event_publisher = get_event_publisher()
            # Convert SQLAlchemy model to dict
            item_data = {k: v for k, v in updated_item.__dict__.items() if not k.startswith('_')}
            event_publisher.publish_entity_updated(
                entity_type="items",
                entity_id=str(item_id),
                organization_id=str(organization_id),
                data=item_data
            )
        except Exception as e:
            logger.error(f"Failed to publish item updated event: {e}")
        
        return updated_item

    def delete_item(
        self,
        item_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Item:
        """
        Soft delete an item.

        Args:
            item_id: Item UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the item

        Returns:
            Deleted Item object

        Raises:
            ItemNotFoundException: If item not found
        """
        item = self.item_repo.get_item_by_id(item_id, organization_id)
        if not item:
            raise ItemNotFoundException(f"Item with ID {item_id} not found")

        item.updated_by = user_id
        deleted_item = self.item_repo.soft_delete_item(item)
        
        # Publish entity deleted event
        try:
            event_publisher = get_event_publisher()
            event_publisher.publish_entity_deleted(
                entity_type="items",
                entity_id=str(item_id),
                organization_id=str(organization_id)
            )
        except Exception as e:
            logger.error(f"Failed to publish item deleted event: {e}")
        
        return deleted_item

    def get_items(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        item_type: str | None = None,
        item_group_id: UUID | None = None,
        maintain_stock: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Item], dict]:
        """
        Get paginated list of items with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by item status
            item_type: Filter by item type
            item_group_id: Filter by item group
            maintain_stock: Filter by maintain_stock flag
            search: Search term for item_code, item_name, barcode
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of items, pagination metadata)
        """
        # Validate and convert enum values (case-insensitive)
        status_enum = None
        if status:
            try:
                status_str = str(status).upper()
                status_enum = ItemStatus(status_str)
            except (ValueError, KeyError):
                pass

        item_type_enum = None
        if item_type:
            try:
                item_type_str = str(item_type).upper()
                item_type_enum = ItemType(item_type_str)
            except (ValueError, KeyError):
                pass

        # Ensure page_size doesn't exceed maximum
        page_size = min(page_size, 100)

        # Get items from repository
        items, total_count = self.item_repo.list_items(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status_enum,
            item_type=item_type_enum,
            item_group_id=item_group_id,
            maintain_stock=maintain_stock,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return items, pagination
