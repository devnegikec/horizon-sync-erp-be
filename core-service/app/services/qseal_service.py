"""Service layer for QSeal module"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.qseal_repository import QSealRepository
from app.schemas.qseal import (
    QSealChildCreate,
    QSealMapRequest,
    QSealParentCreate,
    QSealScanRequest,
)

logger = logging.getLogger(__name__)


class QSealService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QSealRepository(db)

    def _to_response_dict(self, node) -> dict:
        return {
            "id": node.id,
            "organization_id": node.organization_id,
            "qseal_type": node.qseal_type,
            "name": node.name,
            "capacity": node.capacity,
            "serial_number": node.serial_number,
            "qseal_code_link": node.qseal_code_link,
            "app_cascade_map": node.app_cascade_map,
            "parent_id": node.parent_id,
            "parent_app_id": node.parent_app_id,
            "children_count": self.repo.count_children(node.id),
            "created_at": node.created_at,
        }

    def _paginate(self, items, total, page, page_size) -> dict:
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    # ── Parent QSeal ──────────────────────────────────────────────────────────

    def create_parent(self, data: QSealParentCreate, organization_id: UUID):
        serial = self.repo.generate_serial(prefix="QSL")
        payload = data.model_dump(exclude={"extra_data"})
        payload["organization_id"] = organization_id
        payload["serial_number"] = serial
        payload["qseal_code_link"] = f"/qseal/{serial}"
        node = self.repo.create_node(payload)
        logger.info(
            "[QSEAL] parent created id=%s serial=%s org=%s",
            node.id,
            serial,
            organization_id,
        )
        return self._to_response_dict(node)

    def list_parents(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qseal_type: str | None = None,
    ):
        items, total = self.repo.list_roots(
            organization_id, page, page_size, qseal_type
        )
        return {
            "nodes": [self._to_response_dict(n) for n in items],
            "pagination": self._paginate(items, total, page, page_size),
        }

    def get_parent(self, node_id: UUID, organization_id: UUID):
        node = self.repo.get_by_id(node_id, organization_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="QSeal node not found"
            )
        return self._to_response_dict(node)

    # ── Child QSeal ───────────────────────────────────────────────────────────

    def create_child(
        self, parent_id: UUID, data: QSealChildCreate, organization_id: UUID
    ):
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent QSeal node not found",
            )

        # Capacity check
        current_children = self.repo.count_children(parent_id)
        if parent.capacity and current_children >= parent.capacity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parent node is at full capacity ({parent.capacity})",
            )

        serial = self.repo.generate_serial(prefix="QSL")
        payload = data.model_dump(exclude={"extra_data"})
        payload["organization_id"] = organization_id
        payload["parent_id"] = parent_id
        payload["serial_number"] = serial
        payload["qseal_code_link"] = f"/qseal/{serial}"
        node = self.repo.create_node(payload)
        logger.info(
            "[QSEAL] child created id=%s parent=%s org=%s",
            node.id,
            parent_id,
            organization_id,
        )
        return self._to_response_dict(node)

    def list_children(
        self,
        parent_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ):
        # Validate parent exists
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent QSeal node not found",
            )
        items, total = self.repo.list_children(
            parent_id, organization_id, page, page_size
        )
        return {
            "children": [self._to_response_dict(n) for n in items],
            "pagination": self._paginate(items, total, page, page_size),
        }

    # ── Map QSeals ────────────────────────────────────────────────────────────

    def map_children(
        self, parent_id: UUID, req: QSealMapRequest, organization_id: UUID
    ):
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent QSeal node not found",
            )

        current_children = self.repo.count_children(parent_id)
        if (
            parent.capacity
            and (current_children + len(req.child_ids)) > parent.capacity
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Mapping would exceed parent capacity ({parent.capacity}). "
                    f"Current: {current_children}, Requested: {len(req.child_ids)}"
                ),
            )

        mapped = self.repo.map_children(parent_id, req.child_ids, organization_id)
        logger.info(
            "[QSEAL] map_children parent=%s requested=%d mapped=%d ids=%s",
            parent_id,
            len(req.child_ids),
            mapped,
            req.child_ids,
        )
        return {
            "parent_id": parent_id,
            "mapped_count": mapped,
            "message": f"Successfully mapped {mapped} child QSeal(s) to parent.",
        }

    # ── QSeal Scan ────────────────────────────────────────────────────────────

    def record_scan(self, req: QSealScanRequest, organization_id: UUID):
        # 1. Try QSealTrack (parent nodes)
        node = self.repo.get_by_serial(req.serial_number, organization_id)
        is_parent = True

        # 2. Fallback: try QSealParameters (child units from ProductItems)
        if not node:
            from app.models.qseal import QSealParameters

            child = (
                self.db.query(QSealParameters)
                .filter(
                    QSealParameters.serial_number == req.serial_number,
                    QSealParameters.organization_id == organization_id,
                )
                .first()
            )
            if child:
                is_parent = False
                # Build a pseudo-node response with parent info
                parent_node = None
                parent_serial = None
                if child.parent_id:
                    parent_node = self.repo.get_by_id(child.parent_id, organization_id)
                    parent_serial = parent_node.serial_number if parent_node else None

                # Record scan event
                scan_payload = {
                    "organization_id": organization_id,
                    "serial_number": req.serial_number,
                    "scan_timestamp": datetime.now(UTC),
                    "device_type": req.device_type,
                    "os": req.os,
                    "browser": req.browser,
                    "ip_address": req.ip_address,
                    "latitude": req.latitude,
                    "longitude": req.longitude,
                    "city": req.city,
                    "state": req.state,
                    "country": req.country,
                    "extra_data": req.extra_data,
                }
                self.repo.record_scan(scan_payload)

                logger.info(
                    "[QSEAL] child scan recorded serial=%s org=%s parent=%s",
                    req.serial_number,
                    organization_id,
                    parent_serial,
                )
                return {
                    "node_id": child.id,
                    "serial_number": child.serial_number,
                    "qseal_type": "child_unit",
                    "name": f"Unit {child.serial_number or ''}",
                    "parent_id": child.parent_id,
                    "parent_serial": parent_serial,
                    "children_count": 0,
                    "message": f"Child QSeal unit scanned. Parent: {parent_serial or 'none'}.",
                }

        # 3. Not found in either table
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No QSeal node found for serial '{req.serial_number}'",
            )

        # Record scan for parent node
        scan_payload = {
            "organization_id": organization_id,
            "serial_number": req.serial_number,
            "scan_timestamp": datetime.now(UTC),
            "device_type": req.device_type,
            "os": req.os,
            "browser": req.browser,
            "ip_address": req.ip_address,
            "latitude": req.latitude,
            "longitude": req.longitude,
            "city": req.city,
            "state": req.state,
            "country": req.country,
            "extra_data": req.extra_data,
        }
        self.repo.record_scan(scan_payload)

        children_count = self.repo.count_children(node.id)
        logger.info(
            "[QSEAL] scan recorded serial=%s node=%s org=%s",
            req.serial_number,
            node.id,
            organization_id,
        )

        return {
            "node_id": node.id,
            "serial_number": node.serial_number,
            "qseal_type": node.qseal_type,
            "name": node.name,
            "parent_id": node.parent_id,
            "children_count": children_count,
            "message": f"QSeal scan recorded for {node.qseal_type or 'node'} '{node.name}'.",
        }

    # ── QSeal History ─────────────────────────────────────────────────────────

    def get_scan_history(
        self,
        organization_id: UUID,
        serial_number: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        items, total = self.repo.list_scan_history(
            organization_id, serial_number, page, page_size
        )
        return {
            "events": items,
            "pagination": self._paginate(items, total, page, page_size),
        }

    # ── Label Download ────────────────────────────────────────────────────────

    def get_labels(self, parent_id: UUID, organization_id: UUID):
        """Return all child nodes under a parent as label data for printing."""
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent QSeal node not found",
            )

        # Fetch all children (no pagination — label batch)
        items, total = self.repo.list_children(
            parent_id, organization_id, page=1, page_size=10000
        )
        labels = [
            {
                "id": str(child.id),
                "serial_number": child.serial_number,
                "qseal_type": child.qseal_type,
                "name": child.name,
                "qseal_code_link": child.qseal_code_link,
                "parent_serial": parent.serial_number,
            }
            for child in items
        ]
        return {
            "parent_id": parent_id,
            "labels": labels,
            "total": total,
        }

    # ── Parent with Linked Units (for inbound/receiving) ──────────────────────

    def get_parent_with_linked_units(
        self, parent_id: UUID, organization_id: UUID
    ) -> dict:
        """Return a parent QSeal node with all its linked QSealParameters children.

        Used by mobile app for inbound: scan parent QR → see all linked units
        → create receiving slip.
        """
        from app.models.product_item import ProductItem
        from app.models.qseal import QSealParameters

        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent QSeal node not found",
            )

        # Fetch linked QSealParameters with ProductItem join for URL/scan count
        linked = (
            self.db.query(QSealParameters, ProductItem)
            .outerjoin(
                ProductItem,
                (ProductItem.serial_number == QSealParameters.serial_number)
                & (ProductItem.organization_id == organization_id),
            )
            .filter(
                QSealParameters.parent_id == parent_id,
                QSealParameters.organization_id == organization_id,
            )
            .order_by(QSealParameters.created_at.asc())
            .all()
        )

        units = []
        for param, item in linked:
            units.append(
                {
                    "id": param.id,
                    "serial_number": param.serial_number,
                    "manufacturing_date": str(param.manufacturing_date)
                    if param.manufacturing_date
                    else None,
                    "expiry_date": str(param.expiry_date)
                    if param.expiry_date
                    else None,
                    "manufacturing_unit": param.manufacturing_unit,
                    "dispatch_batch": param.dispatch_batch,
                    "destination_market": param.destination_market,
                    "mrp": float(param.mrp) if param.mrp else None,
                    "currency": param.currency,
                    "batch_size": param.batch_size,
                    "qseal_cascade": param.qseal_cascade or False,
                    "product_item_url": item.token_id if item else None,
                    "product_item_scan_count": item.scan_count if item else 0,
                    "extra_data": param.extra_data,
                }
            )

        result = self._to_response_dict(parent)
        result["linked_units"] = units
        logger.info(
            "[QSEAL] parent detail with linked units parent=%s units=%d",
            parent_id,
            len(units),
        )
        return result

    # ── Block-based Parent QSeal ──────────────────────────────────────────────

    def get_parents_by_block(
        self,
        block_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ):
        """List all QSealTrack parent nodes created for a QR block's master packs."""
        from app.models.qr_block import QRBlock
        from app.models.qseal import QSealTrack

        # Validate block exists and belongs to org
        block = (
            self.db.query(QRBlock)
            .filter(QRBlock.id == block_id, QRBlock.organization_id == organization_id)
            .first()
        )
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR block not found",
            )

        if not block.master_pack_enabled:
            return {
                "nodes": [],
                "pagination": self._paginate([], 0, page, page_size),
                "message": "Master pack is not enabled for this block.",
            }

        # Find all distinct parent QSealTracks via QSealParameters
        from app.models.qseal import QSealParameters

        parent_ids_subq = (
            self.db.query(QSealParameters.parent_id)
            .filter(
                QSealParameters.block_id == block_id,
                QSealParameters.organization_id == organization_id,
                QSealParameters.parent_id.isnot(None),
            )
            .distinct()
            .subquery()
        )

        q = self.db.query(QSealTrack).filter(
            QSealTrack.id.in_(self.db.query(parent_ids_subq.c.parent_id))
        )

        total = q.count()
        items = (
            q.order_by(QSealTrack.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "nodes": [self._to_response_dict(n) for n in items],
            "pagination": self._paginate(items, total, page, page_size),
            "block_batch": block.batch,
        }

    def get_parents_excel(
        self, block_id: UUID, organization_id: UUID
    ) -> tuple[bytes, str]:
        """Generate an Excel file with parent QSeal QR codes for a block.

        Includes embedded QR code images for mobile app scanning.
        Returns (excel_bytes, filename).
        """
        from io import BytesIO

        import qrcode
        from openpyxl import Workbook
        from openpyxl.drawing.image import Image as XLImage
        from openpyxl.styles import Alignment, Font
        from openpyxl.utils import get_column_letter

        from app.config import settings
        from app.models.qr_block import QRBlock
        from app.models.qseal import QSealParameters, QSealTrack

        def _embed_qr(ws, url: str, row: int, col: int, size: int = 150) -> None:
            if not url:
                return
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=10,
                border=2,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            xl_img = XLImage(buf)
            xl_img.width = size
            xl_img.height = size
            cell_ref = f"{get_column_letter(col)}{row}"
            ws.add_image(xl_img, cell_ref)

        # Validate block
        block = (
            self.db.query(QRBlock)
            .filter(QRBlock.id == block_id, QRBlock.organization_id == organization_id)
            .first()
        )
        if not block:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR block not found",
            )

        if not block.master_pack_enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Master pack is not enabled for this block.",
            )

        # Get parent nodes via parameters
        parent_ids = (
            self.db.query(QSealParameters.parent_id)
            .filter(
                QSealParameters.block_id == block_id,
                QSealParameters.organization_id == organization_id,
                QSealParameters.parent_id.isnot(None),
            )
            .distinct()
            .all()
        )
        parent_id_list = [p[0] for p in parent_ids]

        if not parent_id_list:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No parent QSeal nodes found for this block.",
            )

        parents = (
            self.db.query(QSealTrack)
            .filter(QSealTrack.id.in_(parent_id_list))
            .order_by(QSealTrack.created_at.asc())
            .all()
        )

        # Build Excel with embedded QR codes
        wb = Workbook()
        ws = wb.active
        ws.title = "QSeal Parent QR Codes"

        # Headers: QR URL, QR Code image, Serial, Name, Capacity
        headers = ["QR URL", "QR Code", "Serial Number", "Name", "Capacity"]
        bold_font = Font(bold=True)
        for col_idx, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=header)
            cell.font = bold_font
            cell.alignment = Alignment(horizontal="center")

        # Column widths
        ws.column_dimensions[get_column_letter(1)].width = 55  # QR URL
        ws.column_dimensions[get_column_letter(2)].width = 24  # QR Code image
        ws.column_dimensions[get_column_letter(3)].width = 18  # Serial
        ws.column_dimensions[get_column_letter(4)].width = 25  # Name
        ws.column_dimensions[get_column_letter(5)].width = 15  # Capacity

        qr_size = 150
        base_url = settings.qr_base_url or f"https://{settings.qr_domain}"

        for row_idx, parent in enumerate(parents, 2):
            serial = parent.serial_number or ""
            qr_url = f"{base_url}/qseal/{serial}" if serial else ""

            # Row height for QR image
            ws.row_dimensions[row_idx].height = 115

            ws.cell(row=row_idx, column=1, value=qr_url)  # QR URL
            _embed_qr(ws, qr_url, row_idx, 2, qr_size)  # QR Code image
            ws.cell(row=row_idx, column=3, value=serial)  # Serial Number
            ws.cell(row=row_idx, column=4, value=parent.name or "")
            ws.cell(row=row_idx, column=5, value=parent.capacity or 0)

        # Save
        buf = BytesIO()
        wb.save(buf)
        buf.seek(0)

        filename = f"qseal_parents_{block.batch}.xlsx"
        logger.info(
            "[QSEAL] parent excel with QR images generated block=%s parents=%d",
            block_id,
            len(parents),
        )
        return buf.getvalue(), filename
