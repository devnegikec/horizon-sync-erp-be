"""Service layer for Cascade module"""

import logging
from uuid import UUID


import logging





from openpyxl import Workbook
from openpyxl.drawing.image import Image
from io import BytesIO
import qrcode

#import validators
import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from urllib.parse import urlparse
from app.models.qr_activation import QRTypeEnum

from app.config import settings
from app.repositories.cascade_repository import (
    CascadeActivationRepository,
    ProductItemCascadeRepository,
    QRActivationTrackRepository,
)
from app.schemas.cascade import (
    ChildQRRequest,
    QRScanCascadeRequest,
    QRTrackCreate,
    QRTrackUpdate,
    ParentQRCreate,
)
from app.utils.serial_generators import build_qr_url, sign_qr_item,build_long_qr_url,resolve_serial_from_short_url
from app.services.key_service import KeyService
from app.config import settings

logger = logging.getLogger(__name__)


class CascadeService:
    def __init__(self, db: Session):
        self.db = db
        self.track_repo = QRActivationTrackRepository(db)
        self.activation_repo = CascadeActivationRepository(db)
        self.item_repo = ProductItemCascadeRepository(db)
        self.key_service = (KeyService(settings.brand_key_encryption_secret)
            if settings.brand_key_encryption_secret else None)

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
         #   "parent_id": node.parent_id,
         #   "parent_app_id": node.parent_app_id,
            "children_count": self.track_repo.count_children(node.id),
            "created_at": node.created_at,
        }

    def _build_pagination(
        self, total: int, page: int, page_size: int
    ) -> dict:
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
        self, data: ParentQRCreate, organization_id: UUID, user_id: UUID
    ): 
        print("Creating parent QR track with data:", data)
        serial = self.track_repo.generate_serial(prefix="PAR")[:10]
        payload = data.model_dump(exclude={"extra_data"})
      
        
        payload["organization_id"] = organization_id
        payload["serial_number"] = serial
     
        payload["qr_code_link"] = self.generate_qr_url(serial,organization_id,data.qr_type)
    
        payload["created_by"] = user_id
        node = self.track_repo.create_node(payload)
        logger.info("[CASCADE] parent created id=%s serial=%s org=%s", node.id, serial, organization_id)
        return node
    
    
    def list_parents(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qr_type: str | None = None,
    ):
        items, total = self.track_repo.list_roots(organization_id, page, page_size, qr_type)
        return {
            "nodes": [self._to_response_dict(n) for n in items],
            "pagination": self._build_pagination(total, page, page_size),
        }


    

    def list_history(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        qr_type: str | None = None,
    ) -> tuple[list, dict]:
        items, total = self.track_repo.list_history(
            organization_id, page, page_size, qr_type
        )
        return {
            "nodes": [self._to_response_dict(n) for n in items],
            "pagination": self._build_pagination(total, page, page_size),
        }
       # return items, self._build_pagination(total, page, page_size)

    def update_track(
        self,
        track_id: UUID,
        data: QRTrackUpdate,
        organization_id: UUID,
    ):
        track = self.track_repo.get_by_id(track_id, organization_id)
        if not track:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR track not found",
            )
        return self.track_repo.update(track, data.model_dump(exclude_unset=True))

    # ── QR Scan Cascade ───────────────────────────────────────────────────────

    async def scan_cascade(
        self,
        req: QRScanCascadeRequest,
        organization_id: UUID,
    ) -> str:
        sr_number = await resolve_serial_from_short_url(req.url)
     
        # Check product item activation status
        item = self.item_repo.get_by_serial(sr_number, organization_id)
        if item and item.qr_deactive and item.qr_deactive_unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR code not Activated",
            )

        # Look up in track first, then activation params
        parent = self.track_repo.get_by_serial(
            sr_number, organization_id
        ) or self.activation_repo.get_by_serial(sr_number, organization_id)

        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR code not found",
            )
        if parent.parent_app_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This QR code already cascade.",
            )

        return sr_number

    # ── Child QR ──────────────────────────────────────────────────────────────

    async def get_children(
        self,
        req: ChildQRRequest,
        organization_id: UUID,
    ) -> dict:
        serial_list = [s.strip() for s in req.srnumber.split(",") if s.strip()]
        if not serial_list:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Children list empty. Collect children items by scanning them in the Read tab.",
            )

        # Resolve parent
        if req.parent_srnumber:
            parent = self.track_repo.get_by_serial(
                req.parent_srnumber, organization_id
            )
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent QR code not found.",
                )
        elif req.url:
            sr_number = await resolve_serial_from_short_url(req.url)
            print("Resolved serial from URL:", sr_number)
            parent = self.track_repo.get_by_serial(sr_number, organization_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent QR code not found.",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Provide parent_srnumber or url.",
            )

        # Filter children based on parent qr_type hierarchy
        # shipper → uses QRActivationParameters
        # pallet  → uses QRActivationTrack with type=shipper
        # default → uses QRActivationTrack with type=pallet
        print("Parent QR type:", parent.qr_type)
        if parent.qr_type == QRTypeEnum.shipper:
            filtered = self.activation_repo.get_children_by_serials(
                serial_list, organization_id
            )
        elif parent.qr_type == QRTypeEnum.pallet:
            print("Filtering children for pallet type parent...")
            filtered = self.track_repo.get_children_by_serials_and_type(
                serial_list, "shipper", organization_id
            )
        else:
            filtered = self.track_repo.get_children_by_serials_and_type(
                serial_list, "pallet", organization_id
            )
        print("Filtered children:", filtered)

        return {"total_capacity": parent.capacity, "children": filtered}

    # ── Mapping ───────────────────────────────────────────────────────────────

    def map_children(
        self,
        parent_srnumber: str,
        serial_numbers: list[str],
        organization_id: UUID,
    ) -> None:
        if not serial_numbers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Serial number(s) required",
            )

        parent = self.track_repo.get_by_serial(parent_srnumber, organization_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent QR not found.",
            )
        if not parent.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please set the capacity of the parent box.",
            )
        if len(serial_numbers) > parent.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quantity exceeds box capacity. Capacity: {parent.capacity}, provided: {len(serial_numbers)}.",
            )
        if parent.app_cascade_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This parent QR code has already been cascaded. Please select a different parent.",
            )

        # Map children — shipper type maps via activation params, others via track
        if parent.qr_type == QRTypeEnum.shipper:
            self.activation_repo.map_children_to_parent(
                serial_numbers, parent.id, organization_id
            )
        else:
            self.track_repo.map_children_to_parent(
                serial_numbers, parent.id, organization_id
            )

        self.track_repo.mark_cascade_mapped(parent)
        self.db.commit()

        logger.info(
            "Cascade mapped: parent=%s org=%s children=%d",
            parent_srnumber,
            organization_id,
            len(serial_numbers),
        )

    # ── Label Download ────────────────────────────────────────────────────────

    def get_label_download_url(
        self, parent_srnumber: str, organization_id: UUID
    ) -> str:
        if not parent_srnumber:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please provide the QR serial number.",
            )
        track = self.track_repo.get_by_serial(parent_srnumber, organization_id)
        if not track or not track.qr_code_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR code link not found for the given serial number.",
            )
        return track.qr_code_link
    

    def get_label_stream(
        self, serial: str, organization_id: UUID
    ) -> tuple[bytes, str]:
        node = self.track_repo.get_by_serial(serial, organization_id)

        if not node or not node.qr_code_link:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR code link not found for the given serial number.",
            )

        # 🧾 Build label (PNG / PDF / Excel — your choice)
        label_bytes = self._build_label_excel(node.qr_code_link, serial)

        filename = f"qr_labels_{serial}.xlsx"

        return label_bytes, filename
    

    def _build_label_excel(self, qr_url: str, serial: str) -> bytes:
        output = BytesIO()

        workbook = Workbook()
        worksheet = workbook.active

        # Headers
        worksheet.append(["Serial Number", "QR URL", "QR Image"])

        # Data row
        worksheet.append([serial, qr_url, ""])

        # -------------------------
        # 1. Generate QR image in memory
        # -------------------------
        qr = qrcode.make(qr_url)

        img_bytes = BytesIO()
        qr.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # -------------------------
        # 2. Insert into Excel
        # -------------------------
        img = Image(img_bytes)
        img.width = 80
        img.height = 80

        # Put image into column C, row 2
        img.anchor = "C2"
        worksheet.add_image(img)

        # Optional formatting
        worksheet.row_dimensions[2].height = 80
        worksheet.column_dimensions["A"].width = 15
        worksheet.column_dimensions["B"].width = 60
        worksheet.column_dimensions["C"].width = 20

        # -------------------------
        # Save file
        # -------------------------
        workbook.save(output)
        output.seek(0)

        return output.read()
    
    
    

    def generate_qr_url(
        self,
        serial: str,
        organization_id: UUID,
        qr_type: QRTypeEnum,
    ) -> str:
        # fallback (always safe)
        gtin = qr_type.name.lower()  # cleaner
        qr_url = f"https://{settings.qr_domain}/g/{gtin}/s/{serial}/"

        if not self.key_service:
            return qr_url

        try:
            brand = self.track_repo.get_brand(organization_id)

            if not brand or not brand.private_key_encrypted:
                return qr_url

            private_key = self.key_service.decrypt_private_key(
                brand.private_key_encrypted
            )

            org_short_code = brand.short_code or ""
           

            sig, ts = sign_qr_item(self.key_service, private_key, serial)

            return build_long_qr_url(org_short_code,settings.qr_domain,gtin,
                serial,ts,sig,)

        except Exception:
            logger.exception("Failed to build signed QR URL")
            return qr_url