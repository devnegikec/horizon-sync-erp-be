"""Order import service for parsing PDF/CSV order files and generating pick lists.

Handles:
- PDF parsing: extracts items, quantities, invoice references from packing slips
- CSV parsing: imports structured order data
- Pick list generation: creates pick lists from parsed order data using existing
  PickListService.create_from_invoice() workflow
"""

import csv
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID

from PyPDF2 import PdfReader

from app.core.exceptions import ValidationError
from app.services.pick_list_service import (
    PickListService,
    SAPInvoiceItem,
    SAPInvoicePayload,
)


@dataclass
class ParsedOrderItem:
    """A single line item extracted from an order document."""

    sku: str = ""
    description: str = ""
    quantity: Decimal = Decimal("0")
    uom: str = "pcs"
    per_case_qty: Decimal | None = None
    case_qty: Decimal | None = None
    loose_qty: Decimal | None = None
    batch_no: str | None = None


@dataclass
class ParsedOrder:
    """Full order extracted from a document."""

    invoice_reference: str = ""
    items: list[ParsedOrderItem] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class ImportResult:
    """Result of an order import operation."""

    pick_lists_created: int = 0
    total_items: int = 0
    errors: list[str] = field(default_factory=list)
    parsed_orders: list[ParsedOrder] = field(default_factory=list)


class OrderImportService:
    """Service for importing orders from PDF and CSV files."""

    # Regex patterns for extracting data from PDF text
    INVOICE_NO_PATTERN = re.compile(
        r'Invoice\s*No[:\s]*([\w][\w/-]*)', re.IGNORECASE
    )
    DOC_NUMBER_PATTERN = re.compile(
        r'Doc\.?\s*Number\s*:\s*([\w][\w/-]*)', re.IGNORECASE
    )
    INVOICE_NOS_PATTERN = re.compile(
        r'Invoice\s*Nos?\s*:\s*([\w][\w/,-]*)', re.IGNORECASE
    )

    # Packing-slip numeric tail: UOM INV_QTY PER_CASE_QTY NO_OF_CASES
    # CASE_QTY LOOSE_QTY LOOSE_BOXES BATCH_NUMBER
    PACKING_NUMERIC_TAIL = re.compile(
        r'(NOS|PCS|EA|EACH)?\s*'
        r'(?P<inv>\d+)\s+'
        r'(?P<per_case>\d+)\s+'
        r'(?P<no_cases>\d+)\s+'
        r'(?P<case_qty>\d+)\s+'
        r'(?P<loose_qty>\d+)\s+'
        r'(?P<loose_boxes>\d+)\s+'
        r'(?P<batch>[A-Za-z0-9-]{3,})'
    )

    # Item line: starts with row number then code, then description, then qty UOM
    # Examples: "1SVACHH-SS-POP-2L Svachh SS Popular 2L Pressure Cooker 2 Nos"
    #           "2SVACHH-SS-POP-1.5L Svachh SS Popular 1.5L Pressure Cooker 3 Nos"
    ITEM_LINE_PATTERN = re.compile(
        r'^\d+'                           # leading row number (discard)
        r'([A-Za-z][\w/.-]{2,})'          # SKU/code (letters, digits, hyphens, dots, slashes)
        r'\s+(.+?)'                       # description (non-greedy)
        r'\s+(\d+)\s*'                    # quantity
        r'(Nos|pcs|PCS|NOS|Ream|Piece)?'  # optional UOM
        r'\s*$',
    )

    def __init__(self, db):
        self.db = db
        self.pick_list_service = PickListService(db)

    # ------------------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------------------

    def import_file(
        self,
        file_content: bytes,
        filename: str,
        org_id: UUID,
        warehouse_id: UUID,
    ) -> ImportResult:
        """Import an order file (PDF or CSV) and generate pick lists.

        Args:
            file_content: Raw bytes of the uploaded file.
            filename: Original filename (used to detect format).
            org_id: Organization UUID.
            warehouse_id: Warehouse UUID to create pick lists for.

        Returns:
            ImportResult with counts and any errors.
        """
        if filename.lower().endswith('.pdf'):
            return self._import_pdf(file_content, org_id, warehouse_id)
        elif filename.lower().endswith('.csv'):
            return self._import_csv(file_content, org_id, warehouse_id)
        else:
            raise ValidationError(
                "Unsupported file format. Please upload a PDF or CSV file."
            )

    # ------------------------------------------------------------------
    # PDF IMPORT
    # ------------------------------------------------------------------

    def _import_pdf(
        self,
        content: bytes,
        org_id: UUID,
        warehouse_id: UUID,
    ) -> ImportResult:
        """Parse a PDF packing slip and create pick lists."""
        result = ImportResult()

        try:
            reader = PdfReader(io.BytesIO(content))
            full_text = ""
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"
        except Exception as e:
            raise ValidationError(f"Failed to read PDF: {str(e)}")

        if not full_text.strip():
            raise ValidationError("PDF appears to be empty or contains no extractable text.")

        # Try to split into multiple orders (multiple packing slips in one PDF)
        # Packing slips are usually separated by page breaks or clear demarcation
        if self._is_packing_slip(full_text):
            orders = self._parse_packing_slip_text(full_text)
        else:
            orders = self._extract_orders_from_text(full_text)

        if not orders:
            raise ValidationError(
                "Could not identify any order/invoice data in the PDF. "
                "Ensure the PDF contains machine-readable text."
            )

        result.parsed_orders = orders

        # Create pick lists for each parsed order
        overwritten_count = 0
        skipped_count = 0
        for order in orders:
            if order.errors:
                result.errors.extend(
                    [f"Order {order.invoice_reference}: {e}" for e in order.errors]
                )
                continue

            if not order.items:
                result.errors.append(
                    f"Order {order.invoice_reference}: no items found"
                )
                continue

            try:
                action = self._create_pick_list_from_order(order, org_id, warehouse_id)
                if action == "created":
                    result.pick_lists_created += 1
                    result.total_items += len(order.items)
                elif action == "overwritten":
                    overwritten_count += 1
                    result.total_items += len(order.items)
                elif action == "skipped":
                    skipped_count += 1
            except Exception as e:
                result.errors.append(
                    f"Order {order.invoice_reference}: {str(e)}"
                )

        if overwritten_count:
            result.errors.append(
                f"{overwritten_count} existing draft pick list(s) were overwritten with new data."
            )
        if skipped_count:
            result.errors.append(
                f"{skipped_count} order(s) skipped — pick list already exists in non-draft status."
            )

        return result

    def _extract_orders_from_text(self, text: str) -> list[ParsedOrder]:
        """Extract individual orders from concatenated PDF text."""
        orders: list[ParsedOrder] = []
        lines = text.split('\n')

        current_order: ParsedOrder | None = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for invoice number on this line
            m = self.INVOICE_NO_PATTERN.search(line)
            if m:
                invoice_no = m.group(1).strip()
                # Save previous order if it has items
                if current_order and current_order.items:
                    orders.append(current_order)
                # Start new order
                current_order = ParsedOrder(invoice_reference=invoice_no)
                continue

            if current_order is None:
                continue

            # Try to parse as an item line
            item = self._parse_item_line(line)
            if item and item.quantity > 0:
                current_order.items.append(item)

        # Don't forget the last order
        if current_order and current_order.items:
            orders.append(current_order)

        return orders

    def _extract_invoice_no(self, text: str) -> str:
        """Extract invoice number from a line of text."""
        m = self.INVOICE_NO_PATTERN.search(text)
        return m.group(1).strip() if m else ""

    def _parse_item_line(self, line: str) -> ParsedOrderItem | None:
        """Attempt to parse a line as an order item."""
        # Skip header/title/footer lines
        if any(kw in line.lower() for kw in ['#', 'item code', 'total', 'grand', 'freight', 'page']):
            return None

        m = self.ITEM_LINE_PATTERN.match(line)
        if m:
            return ParsedOrderItem(
                sku=m.group(1).strip(),
                description=m.group(2).strip(),
                quantity=Decimal(m.group(3)),
                uom=m.group(4) or 'pcs',
            )

        return None

    def _is_packing_slip(self, text: str) -> bool:
        """Detect the extended packing-slip layout (per-case/loose/batch columns)."""
        up = text.upper()
        return ('PER CASE QTY' in up) or ('BATCH NUMBER' in up and 'LOOSE QTY' in up)

    def _parse_packing_slip_text(self, text: str) -> list[ParsedOrder]:
        """Parse an extended packing slip with case/loose/batch columns.

        Handles rows where the item description wraps onto a second line and
        the numeric tail (INV QTY, PER CASE QTY, NO OF CASES, CASE QTY,
        LOOSE QTY, LOOSE BOXES, BATCH NUMBER) sits at the end of a line.
        """
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        doc_ref = ""
        for line in lines:
            m = self.DOC_NUMBER_PATTERN.search(line)
            if m:
                doc_ref = m.group(1).strip()
                break
        if not doc_ref:
            m = self.INVOICE_NOS_PATTERN.search(text)
            if m:
                doc_ref = m.group(1).split(',')[0].strip()

        order = ParsedOrder(invoice_reference=doc_ref or 'PACKING-SLIP')

        header_seen = False
        pending: ParsedOrderItem | None = None

        for line in lines:
            up = line.upper()

            if 'PER CASE' in up or 'BATCH NUMBER' in up or 'LOOSE QTY' in up:
                header_seen = True
                continue

            if not header_seen:
                continue

            # Stop at totals / footer sections
            if (
                up.startswith('GRAND TOTAL')
                or 'TOTAL PRODUCT GROSS' in up
                or 'FREIGHT DETAILS' in up
                or 'BEFORE TAKING DELIVERY' in up
            ):
                break

            if re.match(
                r'^(Invoice|Doc|Dealer|SL\.?|SL\s+NO|Particulars)', line, re.IGNORECASE
            ):
                continue

            code = None
            cm = re.search(r'\(([A-Za-z0-9][A-Za-z0-9./_-]*)\)', line)
            if cm:
                code = cm.group(1)

            num = self.PACKING_NUMERIC_TAIL.search(line)

            if code is not None and num is not None:
                # Complete row on a single line
                order.items.append(
                    ParsedOrderItem(
                        sku=code,
                        description=self._packing_desc(line, code),
                        quantity=Decimal(num.group('inv')),
                        uom=num.group(1) or 'pcs',
                        per_case_qty=Decimal(num.group('per_case')),
                        case_qty=Decimal(num.group('no_cases')),
                        loose_qty=Decimal(num.group('loose_qty')),
                        batch_no=num.group('batch'),
                    )
                )
                pending = None
            elif num is not None and pending is not None:
                # Numeric tail on a continuation line
                pending.quantity = Decimal(num.group('inv'))
                pending.uom = num.group(1) or 'pcs'
                pending.per_case_qty = Decimal(num.group('per_case'))
                pending.case_qty = Decimal(num.group('no_cases'))
                pending.loose_qty = Decimal(num.group('loose_qty'))
                pending.batch_no = num.group('batch')
                order.items.append(pending)
                pending = None
            elif code is not None:
                # New item start — description may wrap
                pending = ParsedOrderItem(
                    sku=code,
                    description=self._packing_desc(line, code),
                    quantity=Decimal('0'),
                    uom='pcs',
                )
            elif pending is not None:
                # Description continuation line
                continuation = re.sub(r'\s+', ' ', line).strip()
                if continuation:
                    pending.description = (
                        f"{pending.description} {continuation}".strip()
                    )

        # Keep only items with a positive quantity
        order.items = [i for i in order.items if i.quantity > 0]

        return [order] if order.items else []

    @staticmethod
    def _packing_desc(line: str, code: str) -> str:
        """Extract the item description from a packing-slip row."""
        s = re.sub(r'^\d+\s*', '', line)
        s = s.replace(f'({code})', '', 1)
        s = OrderImportService.PACKING_NUMERIC_TAIL.sub('', s)
        s = re.sub(r'\b(NOS|PCS|EA|EACH)\s*$', '', s, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', s).strip()

    @staticmethod
    def _to_decimal(value: str | None) -> Decimal | None:
        """Parse an optional decimal from a string, returning None if empty."""
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        try:
            return Decimal(value)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # CSV IMPORT
    # ------------------------------------------------------------------

    def _import_csv(
        self,
        content: bytes,
        org_id: UUID,
        warehouse_id: UUID,
    ) -> ImportResult:
        """Parse a CSV order file and create pick lists."""
        result = ImportResult()

        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except Exception as e:
                raise ValidationError(f"Failed to decode CSV file: {str(e)}")

        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames:
            raise ValidationError("CSV file appears to be empty or has no headers.")

        # Normalize header names
        headers = [h.strip().lower() for h in reader.fieldnames]

        # Detect column mapping
        invoice_col = self._find_column(headers, ['invoice', 'invoice_no', 'invoice_reference', 'order_no', 'order_id'])
        sku_col = self._find_column(headers, ['sku', 'item_code', 'item_id', 'product_code', 'code'])
        desc_col = self._find_column(headers, ['description', 'item_name', 'product_name', 'name', 'desc'])
        qty_col = self._find_column(headers, ['quantity', 'qty', 'qty_ordered'])
        uom_col = self._find_column(headers, ['uom', 'unit', 'unit_of_measure'])
        per_case_col = self._find_column(headers, ['per_case_qty', 'per_case', 'case_per_qty', 'pieces_per_case'])
        case_col = self._find_column(headers, ['case_qty', 'no_of_cases', 'cases', 'boxes', 'case_count'])
        loose_col = self._find_column(headers, ['loose_qty', 'loose', 'loose_pieces'])
        batch_col = self._find_column(headers, ['batch_no', 'batch_number', 'batch', 'serial_no', 'serial_number'])

        if not sku_col:
            raise ValidationError(
                "CSV must have a column for item code/SKU. "
                f"Found columns: {', '.join(headers)}"
            )

        # Group rows by invoice
        orders_by_invoice: dict[str, ParsedOrder] = {}
        row_idx = 0

        for row in reader:
            row_idx += 1
            invoice_ref = (row.get(invoice_col, '') if invoice_col else '').strip()
            sku = (row.get(sku_col, '') if sku_col else '').strip()
            qty_str = (row.get(qty_col, '1') if qty_col else '1').strip()
            desc = (row.get(desc_col, '') if desc_col else '').strip()
            uom = (row.get(uom_col, 'pcs') if uom_col else 'pcs').strip()
            per_case_qty = self._to_decimal(row.get(per_case_col, '') if per_case_col else None)
            case_qty = self._to_decimal(row.get(case_col, '') if case_col else None)
            loose_qty = self._to_decimal(row.get(loose_col, '') if loose_col else None)
            batch_no = (row.get(batch_col, '') if batch_col else '').strip() or None

            if not sku:
                continue

            try:
                qty = Decimal(qty_str) if qty_str else Decimal('1')
            except Exception:
                result.errors.append(f"Row {row_idx}: invalid quantity '{qty_str}'")
                continue

            if not invoice_ref:
                invoice_ref = f"ORDER-IMPORT-{row_idx}"

            if invoice_ref not in orders_by_invoice:
                orders_by_invoice[invoice_ref] = ParsedOrder(
                    invoice_reference=invoice_ref,
                )

            orders_by_invoice[invoice_ref].items.append(
                ParsedOrderItem(
                    sku=sku,
                    description=desc,
                    quantity=qty,
                    uom=uom,
                    per_case_qty=per_case_qty,
                    case_qty=case_qty,
                    loose_qty=loose_qty,
                    batch_no=batch_no,
                )
            )

        result.parsed_orders = list(orders_by_invoice.values())

        overwritten_count = 0
        skipped_count = 0
        for order in result.parsed_orders:
            if not order.items:
                result.errors.append(f"Order {order.invoice_reference}: no items found")
                continue

            try:
                action = self._create_pick_list_from_order(order, org_id, warehouse_id)
                if action == "created":
                    result.pick_lists_created += 1
                    result.total_items += len(order.items)
                elif action == "overwritten":
                    overwritten_count += 1
                    result.total_items += len(order.items)
                elif action == "skipped":
                    skipped_count += 1
            except Exception as e:
                result.errors.append(f"Order {order.invoice_reference}: {str(e)}")

        if overwritten_count:
            result.errors.append(
                f"{overwritten_count} existing draft pick list(s) were overwritten."
            )
        if skipped_count:
            result.errors.append(
                f"{skipped_count} order(s) skipped — pick list already exists in non-draft status."
            )

        return result

    # ------------------------------------------------------------------
    # PICK LIST CREATION
    # ------------------------------------------------------------------

    def _create_pick_list_from_order(
        self,
        order: ParsedOrder,
        org_id: UUID,
        warehouse_id: UUID,
    ) -> str:
        """Create or overwrite a pick list from a parsed order. Returns action: created/overwritten/skipped."""
        from sqlalchemy import text

        # Check for existing pick list with same invoice reference
        from app.models.pick_list import PickList
        from app.models.base import PickListStatus

        existing = (
            self.db.query(PickList)
            .filter(
                PickList.organization_id == org_id,
                PickList.invoice_reference == order.invoice_reference,
            )
            .order_by(PickList.created_at.desc())
            .first()
        )

        if existing:
            if existing.status == PickListStatus.DRAFT:
                # Overwrite the existing draft pick list
                self._update_pick_list_items(existing, order, org_id, warehouse_id)
                return "overwritten"
            else:
                # Non-draft exists — skip
                return "skipped"

        # Create new pick list
        sap_items: list[SAPInvoiceItem] = []
        unresolved: list[str] = []

        for item in order.items:
            item_row = self.db.execute(
                text(
                    "SELECT id FROM items "
                    "WHERE (sku = :sku OR item_code = :sku) "
                    "AND organization_id = :org_id "
                    "LIMIT 1"
                ),
                {"sku": item.sku, "org_id": str(org_id)},
            ).fetchone()

            if item_row:
                raw_id = item_row[0]
                item_uuid = raw_id if isinstance(raw_id, UUID) else UUID(raw_id)
                sap_items.append(
                    SAPInvoiceItem(
                        item_id=item_uuid,
                        sku=item.sku,
                        quantity=item.quantity,
                        uom=item.uom or 'pcs',
                        per_case_qty=item.per_case_qty,
                        case_qty=item.case_qty,
                        loose_qty=item.loose_qty,
                        batch_no=item.batch_no,
                    )
                )
            else:
                unresolved.append(item.sku)

        if unresolved:
            raise ValidationError(
                f"Items not found in item master: {', '.join(unresolved[:5])}"
                f"{'...' if len(unresolved) > 5 else ''}. "
                f"Import the items CSV first."
            )

        payload = SAPInvoicePayload(
            invoice_reference=order.invoice_reference,
            warehouse_id=warehouse_id,
            items=sap_items,
        )

        self.pick_list_service.create_from_invoice(payload, org_id)
        return "created"

    def _update_pick_list_items(
        self,
        pick_list,
        order: ParsedOrder,
        org_id: UUID,
        warehouse_id: UUID,
    ) -> None:
        """Replace items on an existing draft pick list with new order data."""
        from sqlalchemy import text
        from app.models.pick_list import PickListItem

        # Remove existing items
        self.db.query(PickListItem).filter(
            PickListItem.pick_list_id == pick_list.id
        ).delete()

        # Add new items
        for item in order.items:
            item_row = self.db.execute(
                text(
                    "SELECT id FROM items "
                    "WHERE (sku = :sku OR item_code = :sku) "
                    "AND organization_id = :org_id "
                    "LIMIT 1"
                ),
                {"sku": item.sku, "org_id": str(org_id)},
            ).fetchone()

            if not item_row:
                continue

            raw_id = item_row[0]
            item_uuid = raw_id if isinstance(raw_id, UUID) else UUID(raw_id)

            pl_item = PickListItem(
                organization_id=org_id,
                pick_list_id=pick_list.id,
                item_id=item_uuid,
                warehouse_id=warehouse_id,
                qty=item.quantity,
                picked_qty=Decimal("0"),
                uom=item.uom or 'pcs',
                per_case_qty=item.per_case_qty,
                case_qty=item.case_qty,
                loose_qty=item.loose_qty,
                batch_no=item.batch_no,
                sort_order=0,
            )
            self.db.add(pl_item)

        self.db.commit()

        # Re-resolve bin locations
        from app.models.pick_list import PickList as PL
        pick_list = self.db.query(PL).filter(PL.id == pick_list.id).first()
        if pick_list:
            self.pick_list_service.resolve_bin_locations(pick_list.id, org_id)

    @staticmethod
    def _find_column(headers: list[str], candidates: list[str]) -> str:
        """Find the best matching column name from a list of candidates."""
        for candidate in candidates:
            if candidate in headers:
                return candidate
        # Try partial matches
        for header in headers:
            for candidate in candidates:
                if candidate in header:
                    return header
        return ""
