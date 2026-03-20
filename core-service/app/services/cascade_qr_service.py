"""Service layer for Cascade / Hierarchical QR module"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.cascade_qr_repository import CascadeQRRepository
from app.schemas.cascade_qr import (
    ChildQRCreate,
    MapQRRequest,
    ParentQRCreate,
    CascadeScanRequest,
)

logger = logging.getLogger(__name__)


class CascadeQRService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CascadeQRRepository(db)

    def _to_response_dict(self, node) -> dict:
        return {
            "id": node.id,
            "organization_id": node.organization_id,
            "qr_type": node.qr_type,
            "name": node.name,
            "capacity": node.capacity,
            "serial_number": node.serial_number,
            "qr_code_link": node.qr_code_link,
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

    # ── Parent QR ─────────────────────────────────────────────────────────────

    def create_parent(
        self, data: ParentQRCreate, organization_id: UUID
    ):
        serial = self.repo.generate_serial(prefix="PAR")
        payload = data.model_dump(exclude={"extra_data"})
        payload["organization_id"] = organization_id
        payload["serial_number"] = serial
        payload["qr_code_link"] = f"/qr/cascade/{serial}"
        node = self.repo.create_node(payload)
        logger.info("[CASCADE] parent created id=%s serial=%s org=%s", node.id, serial, organization_id)
        return self._to_response_dict(node)

    def list_parents(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qr_type: str | None = None,
    ):
        items, total = self.repo.list_roots(organization_id, page, page_size, qr_type)
        return {
            "nodes": [self._to_response_dict(n) for n in items],
            "pagination": self._paginate(items, total, page, page_size),
        }

    def get_parent(self, node_id: UUID, organization_id: UUID):
        node = self.repo.get_by_id(node_id, organization_id)
        if not node:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="QR node not found")
        return self._to_response_dict(node)

    # ── Child QR ──────────────────────────────────────────────────────────────

    def create_child(
        self, parent_id: UUID, data: ChildQRCreate, organization_id: UUID
    ):
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Parent QR node not found")

        # Capacity check
        current_children = self.repo.count_children(parent_id)
        if parent.capacity and current_children >= parent.capacity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Parent node is at full capacity ({parent.capacity})",
            )

        serial = self.repo.generate_serial(prefix="CHD")
        payload = data.model_dump(exclude={"extra_data"})
        payload["organization_id"] = organization_id
        payload["parent_id"] = parent_id
        payload["serial_number"] = serial
        payload["qr_code_link"] = f"/qr/cascade/{serial}"
        node = self.repo.create_node(payload)
        logger.info("[CASCADE] child created id=%s parent=%s org=%s", node.id, parent_id, organization_id)
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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Parent QR node not found")
        items, total = self.repo.list_children(parent_id, organization_id, page, page_size)
        return {
            "children": [self._to_response_dict(n) for n in items],
            "pagination": self._paginate(items, total, page, page_size),
        }

    # ── Map QRs ───────────────────────────────────────────────────────────────

    def map_children(
        self, parent_id: UUID, req: MapQRRequest, organization_id: UUID
    ):
        parent = self.repo.get_by_id(parent_id, organization_id)
        if not parent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Parent QR node not found")

        current_children = self.repo.count_children(parent_id)
        if parent.capacity and (current_children + len(req.child_ids)) > parent.capacity:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Mapping would exceed parent capacity ({parent.capacity}). "
                    f"Current: {current_children}, Requested: {len(req.child_ids)}"
                ),
            )

        mapped = self.repo.map_children(parent_id, req.child_ids, organization_id)
        return {
            "parent_id": parent_id,
            "mapped_count": mapped,
            "message": f"Successfully mapped {mapped} child QR(s) to parent.",
        }

    # ── Cascade Scan ──────────────────────────────────────────────────────────

    def record_cascade_scan(
        self, req: CascadeScanRequest, organization_id: UUID
    ):
        node = self.repo.get_by_serial(req.serial_number, organization_id)
        if not node:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cascade QR node found for serial '{req.serial_number}'",
            )

        # Record in qr_scan_events for unified analytics
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
            "[CASCADE] scan recorded serial=%s node=%s org=%s",
            req.serial_number, node.id, organization_id,
        )

        return {
            "node_id": node.id,
            "serial_number": node.serial_number,
            "qr_type": node.qr_type,
            "name": node.name,
            "parent_id": node.parent_id,
            "children_count": children_count,
            "message": f"Cascade scan recorded for {node.qr_type or 'node'} '{node.name}'.",
        }

    # ── Cascade History ───────────────────────────────────────────────────────

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
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Parent QR node not found")

        # Fetch all children (no pagination — label batch)
        items, total = self.repo.list_children(parent_id, organization_id, page=1, page_size=10000)
        labels = [
            {
                "id": str(child.id),
                "serial_number": child.serial_number,
                "qr_type": child.qr_type,
                "name": child.name,
                "qr_code_link": child.qr_code_link,
                "parent_serial": parent.serial_number,
            }
            for child in items
        ]
        return {
            "parent_id": parent_id,
            "labels": labels,
            "total": total,
        }
