"""Stock reconciliation wizard service — template download, CSV upload & preview, confirm."""

from __future__ import annotations

import csv
import io
import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    StockReconciliationNotFoundException,
    ValidationError,
    WarehouseNotFoundException,
)
from app.models.base import MovementType, StockEntryStatus
from app.models.item import Item
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.stock_reconciliation import StockReconciliation, StockReconciliationItem
from app.models.warehouse import Warehouse
from app.repositories.stock_reconciliation_repository import (
    StockReconciliationRepository,
)
from app.services.document_numbering_service import DocumentNumberingService

logger = logging.getLogger(__name__)

TEMPLATE_HEADERS = ["item_code", "item_name", "uom", "system_qty", "actual_qty"]


class StockReconciliationWizardService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockReconciliationRepository(db)

    # ------------------------------------------------------------------
    # 1. Download template
    # ------------------------------------------------------------------

    def generate_template_csv(self, warehouse_id: UUID, organization_id: UUID) -> bytes:
        """Generate a CSV template pre-populated with current stock for the warehouse."""
        warehouse = self._get_warehouse(warehouse_id, organization_id)

        stock_rows = (
            self.db.query(StockLevel, Item)
            .join(Item, StockLevel.product_id == Item.id)
            .filter(
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.organization_id == organization_id,
                StockLevel.quantity_on_hand > 0,
            )
            .order_by(Item.item_code)
            .all()
        )

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(TEMPLATE_HEADERS)
        for sl, item in stock_rows:
            writer.writerow(
                [
                    item.item_code,
                    item.item_name,
                    item.uom or "Nos",
                    sl.quantity_on_hand or 0,
                    "",  # actual_qty — user fills this in
                ]
            )
        return buf.getvalue().encode("utf-8")

    # ------------------------------------------------------------------
    # 2. Upload CSV & create pending_review reconciliation
    # ------------------------------------------------------------------

    def upload_and_preview(
        self,
        warehouse_id: UUID,
        file_content: bytes,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Parse uploaded CSV, create a pending_review reconciliation, return discrepancy preview."""
        warehouse = self._get_warehouse(warehouse_id, organization_id)

        # Parse CSV
        parsed_rows = self._parse_csv(file_content)
        if not parsed_rows:
            raise ValidationError("CSV file contains no data rows.")

        # Build lookup: item_code → (Item, StockLevel)
        item_codes = [r["item_code"] for r in parsed_rows]
        stock_map = self._build_stock_map(item_codes, warehouse_id, organization_id)

        # Validate rows and build reconciliation items
        rec_items: list[dict] = []
        discrepancies: list[dict] = []
        errors: list[str] = []

        for idx, row in enumerate(parsed_rows, start=2):  # row 1 is header
            item_code = row["item_code"]
            actual_qty_str = row.get("actual_qty", "").strip()

            if not actual_qty_str:
                errors.append(
                    f"Row {idx}: actual_qty is required for item '{item_code}'."
                )
                continue

            try:
                actual_qty = int(Decimal(actual_qty_str))
            except Exception:
                errors.append(
                    f"Row {idx}: invalid actual_qty '{actual_qty_str}' for item '{item_code}'."
                )
                continue

            if item_code not in stock_map:
                errors.append(f"Row {idx}: item '{item_code}' not found in the system.")
                continue

            item, stock_level = stock_map[item_code]
            system_qty = (stock_level.quantity_on_hand or 0) if stock_level else 0
            difference = actual_qty - system_qty

            rec_items.append(
                {
                    "item_id": item.id,
                    "warehouse_id": warehouse_id,
                    "current_qty": system_qty,
                    "qty": actual_qty,
                    "qty_difference": difference,
                    "organization_id": organization_id,
                }
            )

            discrepancies.append(
                {
                    "item_id": str(item.id),
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "system_qty": system_qty,
                    "actual_qty": actual_qty,
                    "difference": difference,
                    "uom": item.uom or "Nos",
                }
            )

        if errors:
            raise ValidationError(
                f"CSV validation failed with {len(errors)} error(s).",
                details=[{"field": "csv", "reason": e} for e in errors],
            )

        # Create reconciliation in draft status (pending user review)
        rec_no = DocumentNumberingService(self.db).get_next_number(
            organization_id, "stock_reconciliation"
        )
        rec = StockReconciliation(
            organization_id=organization_id,
            reconciliation_no=rec_no,
            purpose="Stock Count",
            posting_date=datetime.now(UTC),
            status=StockEntryStatus.DRAFT,
            remarks=f"Wizard upload for warehouse {warehouse.code}",
            extra_data={"wizard_state": "pending_review"},
            created_by=user_id,
            updated_by=user_id,
        )
        self.db.add(rec)
        self.db.flush()

        for ri in rec_items:
            ri["reconciliation_id"] = rec.id
            self.db.add(StockReconciliationItem(**ri))

        self.db.commit()
        self.db.refresh(rec)

        items_with_discrepancy = sum(1 for d in discrepancies if d["difference"] != 0)

        return {
            "reconciliation_id": str(rec.id),
            "warehouse_id": str(warehouse_id),
            "status": "pending_review",
            "discrepancies": discrepancies,
            "total_items": len(discrepancies),
            "items_with_discrepancy": items_with_discrepancy,
        }

    # ------------------------------------------------------------------
    # 3. Confirm — commit stock adjustments
    # ------------------------------------------------------------------

    def confirm(
        self,
        reconciliation_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> StockReconciliation:
        """Commit the reconciliation: update stock_levels and create stock_movement audit records."""
        rec = self.repo.get_by_id(reconciliation_id, organization_id, load_items=True)
        if not rec:
            raise StockReconciliationNotFoundException(
                f"Stock reconciliation with ID {reconciliation_id} not found"
            )

        if rec.status not in (StockEntryStatus.DRAFT,):
            raise ValidationError(
                f"Reconciliation is in '{rec.status}' status. Only 'draft' reconciliations can be confirmed."
            )

        now = datetime.now(UTC)

        for item in rec.items:
            if item.qty_difference is None or item.qty_difference == 0:
                continue

            difference = int(item.qty_difference)

            # Update stock_level
            stock_level = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.product_id == item.item_id,
                    StockLevel.warehouse_id == item.warehouse_id,
                    StockLevel.organization_id == organization_id,
                )
                .with_for_update()
                .first()
            )

            if stock_level:
                stock_level.quantity_on_hand = (
                    stock_level.quantity_on_hand or 0
                ) + difference
                stock_level.quantity_available = (stock_level.quantity_on_hand or 0) - (
                    stock_level.quantity_reserved or 0
                )
                stock_level.last_counted_at = now
            else:
                # Create stock_level if it doesn't exist (edge case)
                stock_level = StockLevel(
                    organization_id=organization_id,
                    product_id=item.item_id,
                    warehouse_id=item.warehouse_id,
                    quantity_on_hand=int(item.qty),
                    quantity_reserved=0,
                    quantity_available=int(item.qty),
                    last_counted_at=now,
                )
                self.db.add(stock_level)

            # Create stock_movement audit record
            movement = StockMovement(
                organization_id=organization_id,
                product_id=item.item_id,
                warehouse_id=item.warehouse_id,
                movement_type=MovementType.ADJUSTMENT,
                quantity=difference,
                reference_type="stock_reconciliation",
                reference_id=rec.id,
                notes=f"Reconciliation {rec.reconciliation_no}: adjusted by {difference}",
                performed_by=user_id,
                performed_at=now,
            )
            self.db.add(movement)

        # Mark reconciliation as submitted (completed)
        rec.status = StockEntryStatus.SUBMITTED
        rec.extra_data = {"wizard_state": "completed"}
        rec.submitted_at = now
        rec.updated_by = user_id

        self.db.commit()
        self.db.refresh(rec)
        return rec

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_warehouse(self, warehouse_id: UUID, organization_id: UUID) -> Warehouse:
        wh = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == warehouse_id,
                Warehouse.organization_id == organization_id,
            )
            .first()
        )
        if not wh:
            raise WarehouseNotFoundException(
                f"Warehouse with ID {warehouse_id} not found."
            )
        return wh

    def _parse_csv(self, content: bytes) -> list[dict[str, str]]:
        """Parse CSV bytes into list of row dicts."""
        text = content.decode("utf-8-sig")  # handle BOM
        reader = csv.DictReader(io.StringIO(text))
        rows = []
        for row in reader:
            # Normalise keys to lowercase + underscores
            normalised = {
                k.strip().lower().replace(" ", "_"): v.strip() for k, v in row.items()
            }
            if normalised.get("item_code"):
                rows.append(normalised)
        return rows

    def _build_stock_map(
        self,
        item_codes: list[str],
        warehouse_id: UUID,
        organization_id: UUID,
    ) -> dict[str, tuple]:
        """Build a map of item_code → (Item, StockLevel|None) for the given warehouse."""
        from sqlalchemy.orm import aliased

        # Left join so items without a stock_levels row still appear (system_qty = 0)
        sl_alias = aliased(StockLevel)
        results = (
            self.db.query(Item, sl_alias)
            .outerjoin(
                sl_alias,
                (sl_alias.product_id == Item.id)
                & (sl_alias.warehouse_id == warehouse_id)
                & (sl_alias.organization_id == organization_id),
            )
            .filter(
                Item.item_code.in_(item_codes),
                Item.organization_id == organization_id,
            )
            .all()
        )
        return {item.item_code: (item, sl) for item, sl in results}
