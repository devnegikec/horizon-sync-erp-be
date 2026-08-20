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

import enum

from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.qr_product import QRProduct


class ProductItemSyncService:
    """Bidirectional sync between Item and QRProduct.

    Rules:
    - Item is the primary source of truth (wins on conflict).
    - All synced fields are optional — only populated fields are pushed.
    - Empty strings are treated as "unset" and never overwrite a value on the
      other side. This prevents an untouched Item form field (sent as '') from
      wiping a value that was already set on the Product.
    """

    # ── Fields synced FROM Item TO Product (Item wins on conflict) ──
    ITEM_TO_PRODUCT_FIELDS = [
        # Item-native fields
        "item_code",
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
        "item_type",
        "valuation_method",
        "allow_negative_stock",
        "item_group_id",
        "has_variants",
        "variant_of",
        "variant_attributes",
        "batch_number_series",
        "serial_number_series",
        "enable_auto_reorder",
        "reorder_level",
        "reorder_qty",
        "min_order_qty",
        "max_order_qty",
        "inspection_required_before_purchase",
        "inspection_required_before_delivery",
        "quality_inspection_template",
        "sales_tax_template_id",
        "purchase_tax_template_id",
        "images",
        "tags",
        "custom_fields",
        # Product-native fields mirrored on Item — Item still wins.
        "image_url",
        "industry",
        "qr_type",
        "warranty_period_months",
        "activation_method",
        "sr_number_type",
        "landing_page",
        "brand_id",
        "gtin",
    ]

    # ── Fields synced FROM Product TO Item (only fill when Item is empty) ──
    PRODUCT_TO_ITEM_FIELDS = [
        "gtin",
        "industry",
        "landing_page",
        "warranty_period_months",
        "qr_type",
        "activation_method",
        "sr_number_type",
        "brand_id",
        "image_url",
        "generic_name",
        "email",
        "phone_number",
        "banner_image_url",
        "client_product_auth_url",
        "redirect_to_client",
        "is_active",
    ]

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # ITEM → PRODUCT (Item wins)
    # ------------------------------------------------------------------

    def sync_item_to_product(self, item: Item) -> QRProduct | None:
        """Push Item changes to the linked QRProduct.

        Called after Item create/update when qr_product_id is set.
        Item is the primary source of truth — its values overwrite Product's.
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
        for field in self.ITEM_TO_PRODUCT_FIELDS:
            changed = _copy_if_set(product, item, field) or changed

        # item_name → product.name (Item wins; never reversed here)
        if item.item_name and item.item_name != product.name:
            product.name = item.item_name
            changed = True

        # Merge arbitrary metadata blobs (Item wins on conflicting keys)
        changed = _merge_extra_data(product, item, source_wins=True) or changed

        # Sync the base packaging unit (stored on the Item as a separate row)
        changed = self._sync_packaging_to_product(item, product) or changed

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
        for field in self.PRODUCT_TO_ITEM_FIELDS:
            _copy_if_not_set(item, product, field)

        # name → item.item_name only if Item name is empty (fills gaps only)
        if product.name and not item.item_name:
            item.item_name = product.name

        # sku: Product → Item only if Item.sku is empty
        if product.sku and not item.sku:
            item.sku = product.sku

        # Merge arbitrary metadata blobs (Item wins — keep existing keys).
        # Skip packaging_details, which is Product-internal storage.
        _merge_extra_data(
            item, product, source_wins=False, exclude_keys={"packaging_details"}
        )

    def _sync_packaging_to_product(self, item: Item, product: QRProduct) -> bool:
        """Push the Item's base packaging unit into the Product's extra_data.

        Item packaging lives in ``item_packaging_units`` (base unit row);
        Product packaging lives in ``extra_data["packaging_details"]``.
        """
        from decimal import Decimal

        from app.models.item_packaging_unit import ItemPackagingUnit

        base = (
            self.db.query(ItemPackagingUnit)
            .filter(
                ItemPackagingUnit.item_id == item.id,
                ItemPackagingUnit.is_base_unit == True,  # noqa: E712
            )
            .first()
        )
        if base is None:
            return False

        def _num(value):
            return float(value) if isinstance(value, Decimal) else value

        packaging = {
            "unit_name": base.unit_name,
            "conversion_factor": (
                _num(base.conversion_factor)
                if base.conversion_factor is not None
                else 1.0
            ),
            "items_per_master_pack": base.items_per_master_pack,
            "length_mm": _num(base.length_mm),
            "width_mm": _num(base.width_mm),
            "height_mm": _num(base.height_mm),
            "weight_grams": _num(base.weight_grams),
        }

        extra = dict(product.extra_data or {})
        if extra.get("packaging_details") == packaging:
            return False
        extra["packaging_details"] = packaging
        product.extra_data = extra
        return True


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _copy_if_set(target, source, field: str) -> bool:
    """Copy field from source to target if source has a non-empty value.

    Empty strings are skipped so an untouched form field (sent as '') never
    wipes an existing value on the target.
    """
    val = _to_plain_value(getattr(source, field, None))
    if _has_value(val):
        setattr(target, field, val)
        return True
    return False


def _copy_if_not_set(target, source, field: str) -> bool:
    """Copy field from source to target only if target has no value yet."""
    existing = getattr(target, field, None)
    val = _to_plain_value(getattr(source, field, None))
    if _has_value(val) and not _has_value(existing):
        setattr(target, field, val)
        return True
    return False


def _to_plain_value(val):
    """Convert an enum member to its string value for storage."""
    if isinstance(val, enum.Enum):
        return val.value
    return val


def _has_value(val) -> bool:
    """A value counts as 'set' when it is not None and not an empty string."""
    if val is None:
        return False
    if isinstance(val, str) and val == "":
        return False
    return True


def _merge_extra_data(
    target,
    source,
    source_wins: bool,
    exclude_keys: set[str] | None = None,
) -> bool:
    """Merge the JSONB ``extra_data`` dictionaries.

    When ``source_wins`` is True (Item → Product), source keys overwrite target.
    When False (Product → Item), existing target keys are kept and only missing
    keys are filled in — i.e. Item remains the source of truth.
    """
    exclude_keys = exclude_keys or set()
    src = {
        key: value
        for key, value in (source.extra_data or {}).items()
        if key not in exclude_keys
    }
    tgt = target.extra_data or {}
    if not src:
        return False
    merged = {**tgt, **src} if source_wins else {**src, **tgt}
    if merged != tgt:
        target.extra_data = merged
        return True
    return False
