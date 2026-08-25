"""Catalog import service — one engine, three modes.

Modes:
- ``product_only``            → upsert ``products`` only.
- ``product_with_items``      → upsert ``products`` + ``items``.
- ``item_with_auto_product``  → upsert ``items`` + auto-upsert 1:1 ``products``.

Idempotent on the natural key ``(organization_id, sku)`` with fallback
``(organization_id, gtin)`` — re-running updates, never duplicates.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.products import Product
from app.schemas.catalog_import import CatalogImportRow


class CatalogImportService:
    def __init__(self, db: Session):
        self.db = db

    def import_catalog(
        self,
        organization_id: UUID,
        user_id: UUID,
        mode: str,
        rows: list[CatalogImportRow],
    ) -> dict:
        created = 0
        updated = 0
        deleted = 0
        errors: list[dict] = []

        for idx, row in enumerate(rows, start=1):
            try:
                outcome = self._process_row(organization_id, user_id, mode, row)
                if outcome == "created":
                    created += 1
                elif outcome == "updated":
                    updated += 1
                elif outcome == "deleted":
                    deleted += 1
                # "skipped" is intentionally silent
            except ValueError as exc:
                errors.append({"row": idx, "error": str(exc)})
            except Exception as exc:  # noqa: BLE001 — surface per-row, don't abort
                errors.append({"row": idx, "error": str(exc)})

        self.db.commit()
        return {
            "created": created,
            "updated": updated,
            "deleted": deleted,
            "errors": errors,
        }

    # ------------------------------------------------------------------

    def _process_row(
        self, organization_id: UUID, user_id: UUID, mode: str, row: CatalogImportRow
    ) -> str:
        action = (row.action or "").strip().lower() or "create"
        if action == "delete":
            return self._delete_row(organization_id, user_id, mode, row)
        if action == "create":
            return self._create_row(organization_id, user_id, mode, row)
        if action == "modify":
            return self._modify_row(organization_id, user_id, mode, row)
        return self._upsert_row(organization_id, user_id, mode, row)

    def _create_row(
        self, organization_id: UUID, user_id: UUID, mode: str, row: CatalogImportRow
    ) -> str:
        """Create-only: if it already exists, silently do nothing."""
        name = (row.name or "").strip()
        sku = (row.sku or "").strip() or None
        gtin = (row.gtin or "").strip() or None
        if not name:
            raise ValueError("name is required")
        if not sku and not gtin:
            raise ValueError("sku or gtin is required")

        product = self._find_product(organization_id, sku, gtin)
        item = (
            self._find_item(organization_id, row, sku)
            if mode != "product_only"
            else None
        )
        if product is not None or item is not None:
            return "skipped"
        return self._upsert_row(organization_id, user_id, mode, row)

    def _modify_row(
        self, organization_id: UUID, user_id: UUID, mode: str, row: CatalogImportRow
    ) -> str:
        """Modify-only: update existing records; skip if none exist."""
        name = (row.name or "").strip()
        sku = (row.sku or "").strip() or None
        gtin = (row.gtin or "").strip() or None
        if not name:
            raise ValueError("name is required")
        if not sku and not gtin:
            raise ValueError("sku or gtin is required")

        product = self._find_product(organization_id, sku, gtin)
        item = (
            self._find_item(organization_id, row, sku)
            if mode != "product_only"
            else None
        )
        if product is None and item is None:
            return "skipped"

        if product is not None:
            product.name = name
            product.gtin = gtin or product.gtin
            product.description = row.description or product.description
            product.updated_by = user_id
        if item is not None:
            item.item_name = name
            item.sku = sku or item.sku
            item.gtin = gtin or item.gtin
            item.uom = row.uom or item.uom
            item.updated_by = user_id
        return "updated"

    def _delete_row(
        self, organization_id: UUID, user_id: UUID, mode: str, row: CatalogImportRow
    ) -> str:
        """Deactivate (soft) the item/product; skip silently if missing."""
        sku = (row.sku or "").strip() or None
        gtin = (row.gtin or "").strip() or None
        changed = False

        if mode != "product_only":
            item = self._find_item(organization_id, row, sku)
            if item is not None:
                item.status = "inactive"
                item.updated_by = user_id
                changed = True

        product = self._find_product(organization_id, sku, gtin)
        if product is not None:
            product.is_active = False
            product.updated_by = user_id
            changed = True

        return "deleted" if changed else "skipped"

    # ------------------------------------------------------------------

    def _upsert_row(
        self, organization_id: UUID, user_id: UUID, mode: str, row: CatalogImportRow
    ) -> str:
        name = (row.name or "").strip()
        sku = (row.sku or "").strip() or None
        gtin = (row.gtin or "").strip() or None

        if not name:
            raise ValueError("name is required")
        if not sku and not gtin:
            raise ValueError("sku or gtin is required")

        product = self._find_product(organization_id, sku, gtin)
        if product is None:
            product = Product(
                organization_id=organization_id,
                name=name,
                sku=sku,
                gtin=gtin,
                description=row.description,
                brand_id=row.brand_id,
                category_id=row.category_id,
                product_type="both" if mode != "product_only" else "qseal",
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(product)
            self.db.flush()
            outcome = "created"
        else:
            product.name = name
            product.gtin = gtin or product.gtin
            product.description = row.description or product.description
            product.updated_by = user_id
            outcome = "updated"

        if mode == "product_only":
            return outcome

        item = self._find_item(organization_id, row, sku)
        if item is None:
            item = Item(
                organization_id=organization_id,
                product_id=product.id,
                item_name=name,
                item_code=row.item_code or sku or gtin,
                sku=sku,
                uom=row.uom or "Nos",
                gtin=gtin,
                brand_id=row.brand_id,
                item_group_id=row.item_group_id,
                has_batch_no=row.has_batch_no,
                has_serial_no=row.has_serial_no,
                variant_of=row.variant_of,
                variant_attributes=row.variant_attributes,
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(item)
            self.db.flush()
        else:
            item.item_name = name
            item.sku = sku or item.sku
            item.gtin = gtin or item.gtin
            item.uom = row.uom or item.uom
            item.updated_by = user_id

        return outcome

    def _find_product(self, org: UUID, sku: str | None, gtin: str | None) -> Product | None:
        q = self.db.query(Product).filter(
            Product.organization_id == org, Product.deleted_at.is_(None)
        )
        if sku:
            found = q.filter(Product.sku == sku).first()
            if found:
                return found
        if gtin:
            found = q.filter(Product.gtin == gtin).first()
            if found:
                return found
        return None

    def _find_item(self, org: UUID, row: CatalogImportRow, sku: str | None) -> Item | None:
        q = self.db.query(Item).filter(
            Item.organization_id == org, Item.deleted_at.is_(None)
        )
        if row.item_id:
            found = q.filter(Item.id == row.item_id).first()
            if found:
                return found
        if sku:
            found = q.filter(Item.sku == sku).first()
            if found:
                return found
        if row.item_code:
            found = q.filter(Item.item_code == row.item_code).first()
            if found:
                return found
        return None
