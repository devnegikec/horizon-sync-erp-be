"""Stock entry and items service"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CannotDeleteException,
    DuplicateStockEntryNoException,
    StateError,
    StockEntryItemNotFoundException,
    StockEntryNotFoundException,
)
from app.models.base import MovementType, StockEntryStatus, StockEntryType
from app.models.stock_entry import StockEntry, StockEntryItem
from app.models.stock_level import StockLevel
from app.models.stock_movement import StockMovement
from app.models.uom_conversion import UOMConversion
from app.repositories.stock_entry_repository import StockEntryRepository
from app.schemas.stock_entry import (
    StockEntryCreate,
    StockEntryItemCreate,
    StockEntryItemUpdate,
    StockEntryUpdate,
)


def _enum(s: str | None, enum_cls, default=None):
    if not s:
        return default
    try:
        return enum_cls(str(s).lower())
    except (ValueError, KeyError):
        return default


def _item_dict(d: StockEntryItemCreate) -> dict:
    m = d.model_dump()
    br = m.get("basic_rate")
    qty = m.get("qty")
    if br is not None and qty is not None:
        m["basic_amount"] = Decimal(str(br)) * Decimal(str(qty))
    return m


class StockEntryService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockEntryRepository(db)

    def create(
        self, data: StockEntryCreate, organization_id: UUID, user_id: UUID
    ) -> StockEntry:
        # Auto-generate stock_entry_no if not provided
        if not data.stock_entry_no:
            from app.services.document_numbering_service import DocumentNumberingService
            data.stock_entry_no = DocumentNumberingService(self.db).get_next_number(
                organization_id, "stock_entry"
            )

        if self.repo.get_by_no(data.stock_entry_no, organization_id):
            raise DuplicateStockEntryNoException(
                f"Stock entry with number '{data.stock_entry_no}' already exists"
            )
        h = data.model_dump(exclude={"items"})
        h["organization_id"] = organization_id
        h["created_by"] = user_id
        h["updated_by"] = user_id
        h["stock_entry_type"] = (
            _enum(h.get("stock_entry_type"), StockEntryType)
            or StockEntryType.MATERIAL_RECEIPT
        )
        h["status"] = _enum(h.get("status"), StockEntryStatus) or StockEntryStatus.DRAFT
        items = [_item_dict(i) for i in data.items]
        return self.repo.create(h, items)

    def get_by_id(
        self, entry_id: UUID, organization_id: UUID, load_items: bool = True
    ) -> StockEntry:
        e = self.repo.get_by_id(entry_id, organization_id, load_items=load_items)
        if not e:
            raise StockEntryNotFoundException(
                f"Stock entry with ID {entry_id} not found"
            )
        return e

    def update(
        self,
        entry_id: UUID,
        data: StockEntryUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> StockEntry:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            raise StateError(
                "Only draft stock entries can be updated. "
                "Use POST /submit to confirm, or POST /cancel to cancel."
            )
        d = data.model_dump(exclude_unset=True)
        d["updated_by"] = user_id
        # Block direct status manipulation — use dedicated endpoints
        d.pop("status", None)
        if d.get("stock_entry_type"):
            d["stock_entry_type"] = _enum(d["stock_entry_type"], StockEntryType)
        return self.repo.update(e, d)

    def delete(self, entry_id: UUID, organization_id: UUID) -> None:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            raise CannotDeleteException("Only draft stock entries can be deleted")
        self.repo.delete(e)

    def get_list(
        self,
        organization_id: UUID,
        stock_entry_type: str | None = None,
        status: str | None = None,
        from_warehouse_id: UUID | None = None,
        to_warehouse_id: UUID | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[StockEntry], dict]:
        page_size = min(page_size, 100)
        type_enum = (
            _enum(stock_entry_type, StockEntryType) if stock_entry_type else None
        )
        status_enum = _enum(status, StockEntryStatus) if status else None
        items, total = self.repo.list_entries(
            organization_id=organization_id,
            stock_entry_type=type_enum,
            status=status_enum,
            from_warehouse_id=from_warehouse_id,
            to_warehouse_id=to_warehouse_id,
            search=search,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        tp = (total + page_size - 1) // page_size
        return items, {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": tp,
            "has_next": page < tp,
            "has_prev": page > 1,
        }

    def add_item(
        self,
        entry_id: UUID,
        data: StockEntryItemCreate,
        organization_id: UUID,
    ) -> StockEntryItem:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            raise CannotDeleteException(
                "Items can only be added to draft stock entries"
            )
        d = _item_dict(data)
        d["organization_id"] = organization_id
        d["stock_entry_id"] = entry_id
        return self.repo.add_item(d)

    def update_item(
        self,
        entry_id: UUID,
        item_id: UUID,
        data: StockEntryItemUpdate,
        organization_id: UUID,
    ) -> StockEntryItem:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            raise CannotDeleteException(
                "Items can only be updated in draft stock entries"
            )
        it = self.repo.get_item_by_id(item_id, organization_id)
        if not it or it.stock_entry_id != entry_id:
            raise StockEntryItemNotFoundException(
                f"Stock entry item with ID {item_id} not found"
            )
        d = data.model_dump(exclude_unset=True)
        return self.repo.update_item(it, d)

    def delete_item(self, entry_id: UUID, item_id: UUID, organization_id: UUID) -> None:
        e = self.get_by_id(entry_id, organization_id)
        if e.status != StockEntryStatus.DRAFT:
            raise CannotDeleteException(
                "Items can only be removed from draft stock entries"
            )
        it = self.repo.get_item_by_id(item_id, organization_id)
        if not it or it.stock_entry_id != entry_id:
            raise StockEntryItemNotFoundException(
                f"Stock entry item with ID {item_id} not found"
            )
        self.repo.delete_item(it)

    # ------------------------------------------------------------------
    # Submit (confirm) — updates stock levels + creates movement audit
    # ------------------------------------------------------------------

    def submit(
        self, entry_id: UUID, organization_id: UUID, user_id: UUID
    ) -> StockEntry:
        e = self.get_by_id(entry_id, organization_id)

        if e.status != StockEntryStatus.DRAFT:
            raise StateError(
                f"Stock entry is already '{e.status.value}' and cannot be submitted"
            )
        if not e.items:
            raise StateError("Cannot submit a stock entry with no line items")

        for item in e.items:
            self._process_item(e, item, organization_id, user_id)

        # Mark as submitted
        e.status = StockEntryStatus.SUBMITTED
        e.submitted_at = datetime.now(UTC)
        e.updated_by = user_id
        self.db.commit()
        self.db.refresh(e)
        return e

    def reprocess_stock_levels(
        self, entry_id: UUID, organization_id: UUID, user_id: UUID
    ) -> StockEntry:
        """Re-run stock level updates for a submitted entry that was confirmed
        without going through the /submit endpoint (e.g. via direct status update).
        Safe to call only when no stock movements exist yet for this entry.
        """
        e = self.get_by_id(entry_id, organization_id)

        if e.status != StockEntryStatus.SUBMITTED:
            raise StateError(
                f"Only submitted entries can be reprocessed (current: '{e.status.value}')"
            )

        # Check if movements already exist — avoid double-counting
        existing = (
            self.db.query(StockMovement)
            .filter(
                StockMovement.reference_type == "stock_entry",
                StockMovement.reference_id == entry_id,
                StockMovement.organization_id == organization_id,
            )
            .first()
        )
        if existing:
            raise StateError(
                "Stock movements already exist for this entry. Reprocessing would cause double-counting."
            )

        if not e.items:
            raise StateError("Stock entry has no line items to process")

        for item in e.items:
            self._process_item(e, item, organization_id, user_id)

        e.submitted_at = e.submitted_at or datetime.now(UTC)
        e.updated_by = user_id
        self.db.commit()
        self.db.refresh(e)
        return e

    def _get_conversion_factor(
        self, item_id: UUID, from_uom: str, to_uom: str, organization_id: UUID
    ) -> Decimal:
        """Return factor to convert from_uom → to_uom for this item. Falls back to 1."""
        if from_uom.upper() == to_uom.upper():
            return Decimal("1")
        conv = (
            self.db.query(UOMConversion)
            .filter(
                UOMConversion.organization_id == organization_id,
                UOMConversion.item_id == item_id,
                UOMConversion.from_uom == from_uom.upper(),
                UOMConversion.to_uom == to_uom.upper(),
                UOMConversion.deleted_at.is_(None),
            )
            .first()
        )
        return Decimal(str(conv.conversion_factor)) if conv else Decimal("1")

    def _get_item_base_uom(self, item_id: UUID) -> str | None:
        """Fetch the item's base UOM from the items table."""
        from sqlalchemy import text
        row = self.db.execute(
            text("SELECT uom FROM items WHERE id = :id"),
            {"id": str(item_id)},
        ).fetchone()
        return row.uom if row else None

    def _get_or_create_stock_level(
        self, item_id: UUID, warehouse_id: UUID, organization_id: UUID
    ) -> StockLevel:
        sl = (
            self.db.query(StockLevel)
            .filter(
                StockLevel.product_id == item_id,
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.organization_id == organization_id,
            )
            .with_for_update()
            .first()
        )
        if not sl:
            sl = StockLevel(
                organization_id=organization_id,
                product_id=item_id,
                warehouse_id=warehouse_id,
                quantity_on_hand=0,
                quantity_reserved=0,
                quantity_available=0,
            )
            self.db.add(sl)
            self.db.flush()
        return sl

    def _create_movement(
        self,
        entry: StockEntry,
        item: StockEntryItem,
        warehouse_id: UUID,
        movement_type: MovementType,
        qty_base: int,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        m = StockMovement(
            organization_id=organization_id,
            product_id=item.item_id,
            warehouse_id=warehouse_id,
            movement_type=movement_type,
            quantity=qty_base,
            unit_cost=item.valuation_rate or item.basic_rate,
            reference_type="stock_entry",
            reference_id=entry.id,
            notes=entry.remarks,
            performed_by=user_id,
            performed_at=datetime.now(UTC),
        )
        self.db.add(m)

    def _process_item(
        self,
        entry: StockEntry,
        item: StockEntryItem,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        """Apply stock level changes for one line item based on entry type."""
        entry_type = entry.stock_entry_type

        # Convert qty to base UOM
        base_uom = self._get_item_base_uom(item.item_id) or item.uom
        factor = self._get_conversion_factor(
            item.item_id, item.uom, base_uom, organization_id
        )
        qty_base = int((Decimal(str(item.qty)) * factor).to_integral_value())

        if entry_type == StockEntryType.MATERIAL_RECEIPT:
            # Stock IN → target_warehouse_id
            wh = item.target_warehouse_id or entry.to_warehouse_id
            if not wh:
                raise StateError(
                    f"Item {item.item_id}: target warehouse is required for material receipt"
                )
            sl = self._get_or_create_stock_level(item.item_id, wh, organization_id)
            sl.quantity_on_hand = (sl.quantity_on_hand or 0) + qty_base
            sl.quantity_available = max(0, (sl.quantity_on_hand or 0) - (sl.quantity_reserved or 0))
            self._create_movement(entry, item, wh, MovementType.IN, qty_base, organization_id, user_id)

        elif entry_type == StockEntryType.MATERIAL_ISSUE:
            # Stock OUT ← source_warehouse_id
            wh = item.source_warehouse_id or entry.from_warehouse_id
            if not wh:
                raise StateError(
                    f"Item {item.item_id}: source warehouse is required for material issue"
                )
            sl = self._get_or_create_stock_level(item.item_id, wh, organization_id)
            sl.quantity_on_hand = (sl.quantity_on_hand or 0) - qty_base
            sl.quantity_available = max(0, (sl.quantity_on_hand or 0) - (sl.quantity_reserved or 0))
            self._create_movement(entry, item, wh, MovementType.OUT, qty_base, organization_id, user_id)

        elif entry_type in (
            StockEntryType.MATERIAL_TRANSFER,
            StockEntryType.SEND_TO_SUBCONTRACTOR,
        ):
            # OUT from source, IN to target
            src = item.source_warehouse_id or entry.from_warehouse_id
            tgt = item.target_warehouse_id or entry.to_warehouse_id
            if not src or not tgt:
                raise StateError(
                    f"Item {item.item_id}: both source and target warehouses are required for transfer"
                )
            sl_src = self._get_or_create_stock_level(item.item_id, src, organization_id)
            sl_src.quantity_on_hand = (sl_src.quantity_on_hand or 0) - qty_base
            sl_src.quantity_available = max(0, (sl_src.quantity_on_hand or 0) - (sl_src.quantity_reserved or 0))
            self._create_movement(entry, item, src, MovementType.OUT, qty_base, organization_id, user_id)

            sl_tgt = self._get_or_create_stock_level(item.item_id, tgt, organization_id)
            sl_tgt.quantity_on_hand = (sl_tgt.quantity_on_hand or 0) + qty_base
            sl_tgt.quantity_available = max(0, (sl_tgt.quantity_on_hand or 0) - (sl_tgt.quantity_reserved or 0))
            self._create_movement(entry, item, tgt, MovementType.IN, qty_base, organization_id, user_id)

        elif entry_type in (StockEntryType.MANUFACTURE, StockEntryType.REPACK):
            # source_warehouse_id = raw material OUT, target_warehouse_id = finished goods IN
            src = item.source_warehouse_id or entry.from_warehouse_id
            tgt = item.target_warehouse_id or entry.to_warehouse_id
            if src:
                sl_src = self._get_or_create_stock_level(item.item_id, src, organization_id)
                sl_src.quantity_on_hand = (sl_src.quantity_on_hand or 0) - qty_base
                sl_src.quantity_available = max(0, (sl_src.quantity_on_hand or 0) - (sl_src.quantity_reserved or 0))
                self._create_movement(entry, item, src, MovementType.OUT, qty_base, organization_id, user_id)
            if tgt:
                sl_tgt = self._get_or_create_stock_level(item.item_id, tgt, organization_id)
                sl_tgt.quantity_on_hand = (sl_tgt.quantity_on_hand or 0) + qty_base
                sl_tgt.quantity_available = max(0, (sl_tgt.quantity_on_hand or 0) - (sl_tgt.quantity_reserved or 0))
                self._create_movement(entry, item, tgt, MovementType.IN, qty_base, organization_id, user_id)

        self.db.flush()
