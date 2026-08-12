"""Product ↔ Item bidirectional sync service.

Item is the primary source of truth. When Item changes, Product is updated.
When Product changes, all linked Items are updated.

=== DEPRECATION PATH (future: Item-only, remove QRProduct) ===

When QRProduct is deprecated and Item becomes the sole source of truth:

1. DELETE this entire file: app/services/product_item_sync_service.py

2. REMOVE sync calls from item_service.py:
   - Search for "Sync to linked QRProduct" in create_item() and update_item()
   - Delete the try/except blocks (lines ~120-128 and ~230-238)

3. REMOVE sync calls from qr_product_service.py:
   - Search for "Sync Product → linked Items" in create_product() and update_product()
   - Delete the try/except blocks

4. REMOVE Product-sourced columns from Item model (item.py):
   - brand_id, gtin, industry, landing_page, warranty_period_months,
     qr_type, activation_method, sr_number_type
   - Create a migration to drop these columns

5. REMOVE QRProduct model and all related services/endpoints

6. KEEP Item-sourced columns that were synced TO Product:
   - item_code, description, uom, rates, weight, barcode, etc.
   - These already exist on Item — no migration needed
========================================================================
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.qr_product import QRProduct


class ProductItemSyncService:
    """Bidirectional sync between Item and QRProduct.

    Rules:
    - Item is the primary source of truth (wins on conflict).
    - All synced fields are optional — only populated fields are pushed.
    """

    # ── Fields synced FROM Item TO Product ──
    ITEM_TO_PRODUCT_FIELDS = [
        "item_code",
        "item_name",   # → product.name
        "description",
        "sku",
        "uom",
        "standard_rate",
        "valuation_rate",
        "weight_per_unit",
        "weight_uom",
        "barcode",
        "maintain_stock",
        "has_batch_no",
        "has_serial_no",
        "image_url",
    ]

    # ── Fields synced FROM Product TO Item ──
    PRODUCT_TO_ITEM_FIELDS = [
        "name",        # → item.item_name (only if item_name is empty)
        "sku",
        "gtin",
        "industry",
        "landing_page",
        "image_url",
        "warranty_period_months",
        "qr_type",
        "activation_method",
        "sr_number_type",
        "brand_id",
    ]

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # ITEM → PRODUCT (Item wins)
    # ------------------------------------------------------------------

    def sync_item_to_product(self, item: Item) -> QRProduct | None:
        """Push Item changes to the linked QRProduct.

        Called after Item create/update when qr_product_id is set.
        """
        if not item.qr_product_id:
            return None

        product = (
            self.db.query(QRProduct)
            .filter(QRProduct.id == item.qr_product_id)
            .first()
        )
        if not product:
            return None

        changed = False

        # Direct field mappings (Item field → Product field, same name)
        _copy_if_set(product, item, "sku")
        _copy_if_set(product, item, "item_code")
        _copy_if_set(product, item, "description")
        _copy_if_set(product, item, "uom")
        _copy_if_set(product, item, "standard_rate")
        _copy_if_set(product, item, "valuation_rate")
        _copy_if_set(product, item, "weight_per_unit")
        _copy_if_set(product, item, "weight_uom")
        _copy_if_set(product, item, "barcode")
        _copy_if_set(product, item, "maintain_stock")
        _copy_if_set(product, item, "has_batch_no")
        _copy_if_set(product, item, "has_serial_no")
        _copy_if_set(product, item, "image_url")
        _copy_if_set(product, item, "industry")
        _copy_if_set(product, item, "qr_type")
        _copy_if_set(product, item, "warranty_period_months")
        _copy_if_set(product, item, "activation_method")
        _copy_if_set(product, item, "sr_number_type")
        _copy_if_set(product, item, "landing_page")
        _copy_if_set(product, item, "brand_id")
        _copy_if_set(product, item, "gtin")

        # item_name → product.name (not the reverse, Item wins)
        if item.item_name and item.item_name != product.name:
            product.name = item.item_name
            changed = True

        if changed:
            self.db.flush()

        return product

    # ------------------------------------------------------------------
    # PRODUCT → ITEM (push to all linked Items)
    # ------------------------------------------------------------------

    def sync_product_to_items(self, product: QRProduct) -> list[Item]:
        """Push Product changes to all linked Items.

        Called after Product create/update.
        Item is still the primary source — only push fields
        that Item doesn't already have set.
        """
        linked_items = (
            self.db.query(Item)
            .filter(
                Item.qr_product_id == product.id,
                Item.deleted_at.is_(None),
            )
            .all()
        )

        for item in linked_items:
            self._sync_product_fields_to_item(product, item)

        if linked_items:
            self.db.flush()

        return linked_items

    def _sync_product_fields_to_item(self, product: QRProduct, item: Item) -> None:
        """Push individual Product fields to an Item (Item wins on conflict)."""
        _copy_if_not_set(item, product, "gtin")
        _copy_if_not_set(item, product, "industry")
        _copy_if_not_set(item, product, "landing_page")
        _copy_if_not_set(item, product, "warranty_period_months")
        _copy_if_not_set(item, product, "qr_type")
        _copy_if_not_set(item, product, "activation_method")
        _copy_if_not_set(item, product, "sr_number_type")
        _copy_if_not_set(item, product, "brand_id")
        _copy_if_not_set(item, product, "image_url")

        # sku: Product → Item only if Item.sku is empty
        if product.sku and not item.sku:
            item.sku = product.sku


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _copy_if_set(target, source, field: str) -> bool:
    """Copy field from source to target if source value is not None."""
    val = getattr(source, field, None)
    if val is not None:
        setattr(target, field, val)
        return True
    return False


def _copy_if_not_set(target, source, field: str) -> bool:
    """Copy field from source to target only if target doesn't have a value."""
    existing = getattr(target, field, None)
    val = getattr(source, field, None)
    if val is not None and existing is None:
        setattr(target, field, val)
        return True
    return False
