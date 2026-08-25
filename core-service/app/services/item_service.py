"""Item service with business logic"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateItemCodeException,
    ItemNotFoundException,
    ValidationError,
)
from app.events.publisher import get_event_publisher
from app.models.base import ItemStatus, ItemType, ValuationMethod
from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.uom import UOM
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

    def _resolve_uom_id(self, uom_str: str, organization_id: UUID) -> UUID | None:
        """Resolve a legacy UOM string to a uoms.id (abbreviation, then name)."""
        uom = (
            self.db.query(UOM)
            .filter(
                UOM.organization_id == organization_id,
                func.upper(UOM.abbreviation) == uom_str.upper(),
                UOM.deleted_at.is_(None),
            )
            .first()
        )
        if uom is None:
            uom = (
                self.db.query(UOM)
                .filter(
                    UOM.organization_id == organization_id,
                    func.upper(UOM.name) == uom_str.upper(),
                    UOM.deleted_at.is_(None),
                )
                .first()
            )
        return uom.id if uom else None

    def _sync_variant_attributes_from_sku(
        self, item: Item, organization_id: UUID
    ) -> None:
        """One-way sync: derive item.variant_attributes from the linked ProductSKU."""
        if not item.product_sku_id:
            return
        from app.models.product_sku import ProductSKU

        sku = self.db.get(ProductSKU, item.product_sku_id)
        if not sku or sku.organization_id != organization_id:
            return
        attrs: dict = {}
        for link in sku.sku_attribute_values:
            av = link.attribute_value
            if av and av.attribute:
                attrs[av.attribute.name.lower()] = av.display_value or av.value
        if attrs:
            item.variant_attributes = attrs

    def _ensure_product_sku(
        self, item: Item, organization_id: UUID, user_id: UUID
    ) -> None:
        """Auto-create/link a ProductSKU for a concrete variant item (guarded).

        Only runs when structured-variant mode is enabled AND
        ``auto_create_sku_on_item`` is enabled. Applies to child variant items
        (``variant_of`` is set), never the ``has_variants`` template parent.
        """
        import uuid as _uuid

        from app.core.constants import (
            AUTO_CREATE_SKU_ON_ITEM,
            AUTO_CREATE_VARIANT_AXES,
            VARIANT_STRUCTURED_ENABLED,
        )
        from app.models.product_sku import ProductSKU
        from app.models.sku_variant_attribute import (
            ProductSKUAttributeValue,
            VariantAttribute,
            VariantAttributeValue,
        )
        from app.services.feature_flag_service import is_feature_enabled_for_org

        if not is_feature_enabled_for_org(
            VARIANT_STRUCTURED_ENABLED, self.db, organization_id
        ):
            return
        if not is_feature_enabled_for_org(
            AUTO_CREATE_SKU_ON_ITEM, self.db, organization_id
        ):
            return
        # Only concrete variants, not the template parent, and not already linked.
        if item.variant_of is None or item.product_sku_id is not None:
            return
        if not item.qr_product_id or not item.variant_attributes:
            return

        auto_axes = is_feature_enabled_for_org(
            AUTO_CREATE_VARIANT_AXES, self.db, organization_id
        )

        # Reuse an existing SKU with the same code (idempotent).
        existing_sku = (
            self.db.query(ProductSKU)
            .filter(
                ProductSKU.organization_id == organization_id,
                ProductSKU.sku_code == item.sku,
                ProductSKU.deleted_at.is_(None),
            )
            .first()
        )
        if existing_sku:
            item.product_sku_id = existing_sku.id
            self.db.flush()
            return

        # Resolve or create attribute values from the JSONB variant_attributes.
        value_ids: list[UUID] = []
        for axis_name, axis_value in item.variant_attributes.items():
            if not axis_value:
                continue
            attr = (
                self.db.query(VariantAttribute)
                .filter(
                    VariantAttribute.organization_id == organization_id,
                    func.lower(VariantAttribute.name) == str(axis_name).lower(),
                )
                .first()
            )
            if attr is None:
                if not auto_axes:
                    continue
                attr = VariantAttribute(
                    organization_id=organization_id,
                    name=str(axis_name),
                    created_by=user_id,
                    updated_by=user_id,
                )
                self.db.add(attr)
                self.db.flush()

            value_str = str(axis_value)
            av = (
                self.db.query(VariantAttributeValue)
                .filter(
                    VariantAttributeValue.attribute_id == attr.id,
                    VariantAttributeValue.value == value_str,
                )
                .first()
            )
            if av is None:
                av = VariantAttributeValue(
                    attribute_id=attr.id,
                    value=value_str,
                    display_value=value_str,
                    sort_order=0,
                    created_by=user_id,
                )
                self.db.add(av)
                self.db.flush()
            value_ids.append(av.id)

        if not value_ids:
            return

        sku_code = item.sku or f"{item.item_code or 'item'}-{_uuid.uuid4().hex[:8]}"
        sku = ProductSKU(
            organization_id=organization_id,
            product_id=item.qr_product_id,
            sku_code=sku_code,
            name=item.item_name,
            gtin=item.gtin,
            is_active=True,
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(sku)
        self.db.flush()

        for vid in value_ids:
            self.db.add(
                ProductSKUAttributeValue(
                    sku_id=sku.id, attribute_value_id=vid, created_by=user_id
                )
            )
        self.db.flush()

        item.product_sku_id = sku.id
        self.db.flush()

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

        # Resolve base_uom_id from the legacy uom string when not supplied.
        if not item_dict.get("base_uom_id") and item_dict.get("uom"):
            item_dict["base_uom_id"] = self._resolve_uom_id(
                str(item_dict["uom"]), organization_id
            )

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

        # Approval workflow: flag-based default when status not explicitly set.
        if "status" not in item_data.model_fields_set:
            from app.core.constants import (
                AUTO_APPROVE_SINGLE_CREATE,
                REQUIRE_ITEM_APPROVAL,
            )
            from app.services.feature_flag_service import is_feature_enabled_for_org

            require_approval = is_feature_enabled_for_org(
                REQUIRE_ITEM_APPROVAL, self.db, organization_id
            )
            auto_approve = is_feature_enabled_for_org(
                AUTO_APPROVE_SINGLE_CREATE, self.db, organization_id
            )
            if require_approval and not auto_approve:
                item_dict["status"] = ItemStatus.PENDING_APPROVAL

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

        # Variant handling: auto-create/link SKU (guarded), then one-way sync.
        self._ensure_product_sku(item, organization_id, user_id)
        self._sync_variant_attributes_from_sku(item, organization_id)
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

        # ── Auto-create a linked QR product (backward compatibility) ──
        # NOTE: field-level sync (product_item_sync_service) was removed in Phase 4.
        if not item.qr_product_id:
            try:
                from app.models.qr_product import QRProduct

                product = QRProduct(
                    organization_id=organization_id,
                    name=item.item_name,
                    sku=item.sku or item.item_code,
                    gtin=item.barcode,
                    image_url=item.image_url,
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

        # One-way sync: variant_attributes ← linked ProductSKU (Phase 3).
        self._sync_variant_attributes_from_sku(updated_item, organization_id)

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

        # ── Auto-create a linked QR product (backward compatibility) ──
        # NOTE: field-level sync (product_item_sync_service) was removed in Phase 4.
        if not updated_item.qr_product_id:
            try:
                from app.models.qr_product import QRProduct

                product = QRProduct(
                    organization_id=organization_id,
                    name=updated_item.item_name,
                    sku=updated_item.sku or updated_item.item_code,
                    gtin=updated_item.barcode,
                    image_url=updated_item.image_url,
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

        return updated_item

    def submit_for_approval(
        self, item_id: UUID, organization_id: UUID, user_id: UUID
    ) -> Item:
        """Submit an item for approval (DRAFT/INACTIVE → PENDING_APPROVAL)."""
        item = self.get_item_by_id(item_id, organization_id)
        if item.status not in (ItemStatus.DRAFT, ItemStatus.INACTIVE):
            raise ValidationError(
                f"Cannot submit item with status '{item.status.value}' for approval"
            )
        item.status = ItemStatus.PENDING_APPROVAL
        item.submitted_by = user_id
        item.submitted_at = datetime.now(UTC)
        item.rejection_reason = None
        self.db.commit()
        self.db.refresh(item)
        return item

    def approve_item(
        self, item_id: UUID, organization_id: UUID, user_id: UUID
    ) -> Item:
        """Approve a pending item (PENDING_APPROVAL → ACTIVE)."""
        item = self.get_item_by_id(item_id, organization_id)
        if item.status != ItemStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"Cannot approve item with status '{item.status.value}'"
            )
        item.status = ItemStatus.ACTIVE
        item.approved_by = user_id
        item.approved_at = datetime.now(UTC)
        item.rejection_reason = None
        self.db.commit()
        self.db.refresh(item)
        return item

    def reject_item(
        self,
        item_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        reason: str,
    ) -> Item:
        """Reject a pending item (PENDING_APPROVAL → DRAFT) with a reason."""
        item = self.get_item_by_id(item_id, organization_id)
        if item.status != ItemStatus.PENDING_APPROVAL:
            raise ValidationError(
                f"Cannot reject item with status '{item.status.value}'"
            )
        item.status = ItemStatus.DRAFT
        item.rejection_reason = reason
        self.db.commit()
        self.db.refresh(item)
        return item

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
                    items_per_master_pack=getattr(
                        packaging_details, "items_per_master_pack", None
                    ),
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
        if hasattr(packaging_details, "items_per_master_pack"):
            base.items_per_master_pack = packaging_details.items_per_master_pack
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
