"""Item service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateItemCodeException, ItemNotFoundException
from app.events.publisher import get_event_publisher
from app.models.base import ItemStatus, ItemType, ValuationMethod
from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.repositories.item_repository import ItemRepository
from app.repositories.stock_level_repository import StockLevelRepository
from app.repositories.tax_template_repository import TaxTemplateRepository
from app.schemas.item import (
    ItemCreate,
    ItemPickerItem,
    ItemPickerItemGroup,
    ItemPickerStockLevels,
    ItemPickerTaxInfo,
    ItemUpdate,
    TaxBreakupItem,
)

logger = logging.getLogger(__name__)


class ItemService:
    """Service for item operations"""

    def __init__(self, db: Session):
        self.db = db
        self.item_repo = ItemRepository(db)
        self.stock_level_repo = StockLevelRepository(db)
        self.tax_template_repo = TaxTemplateRepository(db)

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
        # Auto-generate item_code if not provided
        if not item_data.item_code:
            from app.services.document_numbering_service import DocumentNumberingService

            item_data.item_code = DocumentNumberingService(self.db).get_next_number(
                organization_id, "item"
            )

        # Check if item code already exists
        if self.item_repo.item_code_exists(item_data.item_code, organization_id):
            # If caller supplied a qr_product_id, try to attach the existing
            # item to that QR product instead of failing the request. This
            # handles races where a QR product auto-created the Item first.
            try:
                existing = self.item_repo.get_item_by_code(
                    item_data.item_code, organization_id
                )
                if existing:
                    # If caller provided qr_product_id and existing item isn't
                    # linked yet, attach and return the existing item.
                    if item_data.qr_product_id:
                        if not existing.qr_product_id:
                            existing.qr_product_id = item_data.qr_product_id
                            existing.updated_by = user_id
                            self.db.add(existing)
                            self.db.commit()
                            self.db.refresh(existing)
                            return existing
                        # If already linked to the same product, return it.
                        if existing.qr_product_id == item_data.qr_product_id:
                            return existing
                    # Otherwise, treat as duplicate error
                    raise DuplicateItemCodeException(
                        f"Item with code '{item_data.item_code}' already exists"
                    )
            except DuplicateItemCodeException:
                raise
            except Exception as exc:
                # Fallback to original behavior on unexpected errors, but log
                # the real cause so failures aren't silently masked as 409s.
                logger.exception(
                    "Unexpected error while resolving duplicate item code '%s'",
                    item_data.item_code,
                )
                raise DuplicateItemCodeException(
                    f"Item with code '{item_data.item_code}' already exists"
                ) from exc

        # Convert enum strings to enum values
        item_dict = item_data.model_dump()
        # packaging_details is not an items column — handled separately below.
        item_dict.pop("packaging_details", None)
        item_dict["organization_id"] = organization_id
        item_dict["created_by"] = user_id
        item_dict["updated_by"] = user_id

        # Convert string enums to actual enums (case-insensitive)
        # ItemType and ItemStatus use lowercase values: "stock", "active", etc.
        if item_dict.get("item_type"):
            try:
                item_type_str = str(item_dict["item_type"]).lower()
                item_dict["item_type"] = ItemType(item_type_str)
            except (ValueError, KeyError):
                item_dict["item_type"] = ItemType.STOCK

        if item_dict.get("status"):
            try:
                status_str = str(item_dict["status"]).lower()
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

        # Auto-create the base packaging unit when packaging details are supplied.
        if item_data.packaging_details is not None:
            self._upsert_base_packaging_unit(
                item, item_data.packaging_details, organization_id
            )
            self.db.commit()

        # Publish entity created event
        try:
            event_publisher = get_event_publisher()
            # Convert SQLAlchemy model to dict
            item_data = {
                k: v for k, v in item.__dict__.items() if not k.startswith("_")
            }
            event_publisher.publish_entity_created(
                entity_type="items",
                entity_id=str(item.id),
                organization_id=str(organization_id),
                data=item_data,
            )
        except Exception as e:
            logger.error(f"Failed to publish item created event: {e}")

        # ── Sync to linked QRProduct (Item is primary source) ──
        # TODO(DEPRECATION): Remove this block when QRProduct is deprecated.
        # If no qr_product_id, auto-create a QR product so sync works both ways.
        if not item.qr_product_id:
            try:
                from app.models.qr_product import QRProduct

                product = QRProduct(
                    organization_id=organization_id,
                    name=item.item_name,
                    sku=item.sku or item.item_code,
                    gtin=item.barcode,
                    image_url=item.image_url,
                    industry=item.industry,
                    qr_type=item.qr_type,
                    warranty_period_months=item.warranty_period_months,
                    activation_method=item.activation_method,
                    sr_number_type=item.sr_number_type,
                    landing_page=item.landing_page,
                    brand_id=item.brand_id,
                    is_active=True,
                    created_by=user_id,
                    updated_by=user_id,
                )
                self.db.add(product)
                self.db.flush()
                item.qr_product_id = product.id
                self.db.flush()
                logger.info(
                    "Auto-created QR product '%s' for item '%s'",
                    product.name,
                    item.item_code,
                )
            except Exception as e:
                logger.error(f"Failed to auto-create QR product for item: {e}")

        if item.qr_product_id:
            try:
                from app.services.product_item_sync_service import (
                    ProductItemSyncService,
                )

                ProductItemSyncService(self.db).sync_item_to_product(item)
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to sync item→product: {e}")

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
        packaging_details_provided = "packaging_details" in update_dict
        update_dict.pop("packaging_details", None)
        update_dict["updated_by"] = user_id

        # Convert string enums to actual enums (case-insensitive)
        # ItemType and ItemStatus use lowercase values: "stock", "active", etc.
        if "item_type" in update_dict and update_dict["item_type"]:
            try:
                item_type_str = str(update_dict["item_type"]).lower()
                update_dict["item_type"] = ItemType(item_type_str)
            except (ValueError, KeyError):
                del update_dict["item_type"]

        if "status" in update_dict and update_dict["status"]:
            try:
                status_str = str(update_dict["status"]).lower()
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

        # Upsert the base packaging unit when packaging details are supplied.
        if packaging_details_provided:
            self._upsert_base_packaging_unit(
                updated_item, item_data.packaging_details, organization_id
            )
            self.db.commit()

        # Publish entity updated event
        try:
            event_publisher = get_event_publisher()
            # Convert SQLAlchemy model to dict
            item_data = {
                k: v for k, v in updated_item.__dict__.items() if not k.startswith("_")
            }
            event_publisher.publish_entity_updated(
                entity_type="items",
                entity_id=str(item_id),
                organization_id=str(organization_id),
                data=item_data,
            )
        except Exception as e:
            logger.error(f"Failed to publish item updated event: {e}")

        # ── Sync to linked QRProduct (Item is primary source) ──
        # TODO(DEPRECATION): Remove this block when QRProduct is deprecated.
        # If no qr_product_id, auto-create a QR product (covers legacy items)
        if not updated_item.qr_product_id:
            try:
                from app.models.qr_product import QRProduct

                product = QRProduct(
                    organization_id=organization_id,
                    name=updated_item.item_name,
                    sku=updated_item.sku or updated_item.item_code,
                    gtin=updated_item.barcode,
                    image_url=updated_item.image_url,
                    industry=updated_item.industry,
                    qr_type=updated_item.qr_type,
                    warranty_period_months=updated_item.warranty_period_months,
                    activation_method=updated_item.activation_method,
                    sr_number_type=updated_item.sr_number_type,
                    landing_page=updated_item.landing_page,
                    brand_id=updated_item.brand_id,
                    is_active=True,
                    created_by=user_id,
                    updated_by=user_id,
                )
                self.db.add(product)
                self.db.flush()
                updated_item.qr_product_id = product.id
                self.db.flush()
                logger.info(
                    "Auto-created QR product for legacy item '%s'",
                    updated_item.item_code,
                )
            except Exception as e:
                logger.error(f"Failed to auto-create QR product for item: {e}")

        if updated_item.qr_product_id:
            try:
                from app.services.product_item_sync_service import (
                    ProductItemSyncService,
                )

                ProductItemSyncService(self.db).sync_item_to_product(updated_item)
                self.db.commit()
            except Exception as e:
                logger.error(f"Failed to sync item→product: {e}")

        return updated_item

    def _upsert_base_packaging_unit(
        self, item: Item, packaging_details, organization_id: UUID
    ) -> None:
        """Create or update the item's base packaging unit from packaging details.

        The base unit (``is_base_unit = True``) is the physical "Each" pack level.
        If one already exists its dimensions/weight are updated in place; if a
        non-base unit already uses the same ``unit_name`` it is promoted to the
        base unit to respect the ``(item_id, unit_name)`` unique constraint.
        """
        if packaging_details is None:
            return

        unit_name = (packaging_details.unit_name or "").strip() or "Each"

        base = (
            self.db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.item_id == item.id,
                ItemPackagingUnit.is_base_unit == True,  # noqa: E712
            )
            .first()
        )

        if base is None:
            # Avoid a unique-constraint violation: reuse a unit that already
            # carries the same name for this item.
            base = (
                self.db.query(ItemPackagingUnit)
                .filter(
                    ItemPackagingUnit.item_id == item.id,
                    ItemPackagingUnit.unit_name == unit_name,
                )
                .first()
            )
            if base is None:
                base = ItemPackagingUnit(
                    organization_id=organization_id,
                    item_id=item.id,
                    unit_name=unit_name,
                    qr_identifier=None,
                    conversion_factor=packaging_details.conversion_factor,
                    length_mm=packaging_details.length_mm,
                    width_mm=packaging_details.width_mm,
                    height_mm=packaging_details.height_mm,
                    weight_grams=packaging_details.weight_grams,
                    is_base_unit=True,
                    is_active=True,
                )
                self.db.add(base)
            else:
                base.is_base_unit = True

        base.conversion_factor = packaging_details.conversion_factor
        base.length_mm = packaging_details.length_mm
        base.width_mm = packaging_details.width_mm
        base.height_mm = packaging_details.height_mm
        base.weight_grams = packaging_details.weight_grams
        self.db.flush()

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
                organization_id=str(organization_id),
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
        # ItemStatus and ItemType use lowercase values: "active", "inactive", "stock", etc.
        status_enum = None
        if status:
            try:
                status_str = str(status).lower()
                status_enum = ItemStatus(status_str)
            except (ValueError, KeyError):
                pass

        item_type_enum = None
        if item_type:
            try:
                item_type_str = str(item_type).lower()
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

    def _get_stock_by_warehouse(
        self,
        product_ids: list[UUID],
        warehouse_id: UUID,
        organization_id: UUID,
    ) -> dict:
        """Return stock levels per product scoped to a single warehouse."""
        from app.models.stock_level import StockLevel

        rows = (
            self.db.query(StockLevel)
            .filter(
                StockLevel.organization_id == organization_id,
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.product_id.in_(product_ids),
            )
            .all()
        )
        return {
            row.product_id: {
                "quantity_on_hand": int(row.quantity_on_hand or 0),
                "quantity_reserved": int(row.quantity_reserved or 0),
                "quantity_available": int(row.quantity_available or 0),
            }
            for row in rows
        }

    def get_items_for_picker(
        self,
        organization_id: UUID,
        search: str | None = None,
        limit: int = 20,
        warehouse_id: UUID | None = None,
    ) -> list[ItemPickerItem]:
        """
        Get items for picker/dropdown with stock levels, item group, and tax info.
        Searches by item name (and item_code, barcode) within the organization.
        If warehouse_id is provided, stock levels are scoped to that warehouse only.
        """
        items, _ = self.item_repo.list_items(
            organization_id=organization_id,
            page=1,
            page_size=min(limit, 50),
            status=ItemStatus.ACTIVE,
            search=search,
            sort_by="item_name",
            sort_order="asc",
        )

        if not items:
            return []

        item_ids = [item.id for item in items]

        # Warehouse-scoped or aggregated stock levels
        if warehouse_id:
            stock_agg = self._get_stock_by_warehouse(
                item_ids, warehouse_id, organization_id
            )
        else:
            stock_agg = self.stock_level_repo.get_aggregated_by_products(
                product_ids=item_ids,
                organization_id=organization_id,
            )

        result = []
        for item in items:
            stock = stock_agg.get(
                item.id,
                {
                    "quantity_on_hand": 0,
                    "quantity_reserved": 0,
                    "quantity_available": 0,
                },
            )

            item_group = None
            if item.item_group:
                item_group = ItemPickerItemGroup(
                    id=item.item_group.id,
                    name=item.item_group.name,
                    code=item.item_group.code,
                )

            tax_info = None
            tax_result = self.tax_template_repo.get_applicable_template(
                organization_id=organization_id,
                transaction_type="Sales",
                item_id=item.id,
                item_group_id=item.item_group_id,
            )
            if tax_result:
                template, _ = tax_result
                breakup = [
                    TaxBreakupItem(
                        rule_name=rule.rule_name,
                        tax_type=rule.tax_type,
                        rate=float(rule.tax_rate or 0),
                        is_compound=bool(rule.is_compound),
                    )
                    for rule in (template.tax_rules or [])
                ]
                is_compound = any(r.is_compound for r in (template.tax_rules or []))
                tax_info = ItemPickerTaxInfo(
                    id=template.id,
                    template_name=template.template_name,
                    template_code=template.template_code,
                    is_compound=is_compound,
                    breakup=breakup,
                )

            result.append(
                ItemPickerItem(
                    id=item.id,
                    item_code=item.item_code,
                    item_name=item.item_name,
                    uom=item.uom or "Nos",
                    sku=item.sku,
                    min_order_qty=item.min_order_qty or 1,
                    max_order_qty=item.max_order_qty,
                    standard_rate=item.standard_rate,
                    stock_levels=ItemPickerStockLevels(**stock),
                    item_group=item_group,
                    tax_info=tax_info,
                )
            )

        return result
