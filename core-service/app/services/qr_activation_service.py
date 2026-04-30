"""Service layer for Landing / Public API module"""

import logging
from datetime import UTC, datetime
from uuid import UUID
from sqlalchemy import update
#import validators
import requests
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from urllib.parse import urlparse
from app.models.qr_product import QRProduct
from app.models.qr_activation import QRActivationParameters
from app.config import settings
from app.repositories.qr_activation_repository import (
    DestinationMarketRepository,
    ProductItemRepository,
    QRActivationRepository,
)
from app.repositories.qr_product_repository import QRProductRepository
from app.schemas.qr_activation import QRScanRequest, QRSettingsCreateRequest

logger = logging.getLogger(__name__)


class QRActivationService:
    def __init__(self, db: Session):
        self.db = db
        self.market_repo = DestinationMarketRepository(db)
        self.product_repo = QRProductRepository(db)
        self.activation_repo = QRActivationRepository(db)
        self.item_repo = ProductItemRepository(db)

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

    # ── Destination Market ────────────────────────────────────────────────────

    def list_destination_markets(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list, dict]:
        items, total = self.market_repo.list_all(
            organization_id, page, page_size, search
        )
        return items, self._build_pagination(total, page, page_size)

    def get_currency_by_market(
        self, name: str, organization_id: UUID
    ) -> str:
        if not name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination Market not provided",
            )
        market = self.market_repo.get_active_by_name(name, organization_id)
        if not market:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination Market for related currency is not found",
            )
        return market.currency_code

    # ── Product ───────────────────────────────────────────────────────────────

    def list_products(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> tuple[list, dict]:
        items, total = self.product_repo.list_all(
            organization_id, page, page_size, search, is_active
        )
        return items, self._build_pagination(total, page, page_size)

    def get_product(self, product_id: UUID, organization_id: UUID):
        product = self.product_repo.get_by_id(product_id, organization_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found",
            )
        return product

    # ── Product Expiry ────────────────────────────────────────────────────────

    def calculate_expiry(
        self,
        product_id: UUID,
        organization_id: UUID,
        manufacturing_date,
    ):
        product = self.get_product(product_id, organization_id)
        if not product.warranty_period_months:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warranty period not configured for this product",
            )
        return manufacturing_date + relativedelta(
            months=product.warranty_period_months
        )

    # ── QR Scan ───────────────────────────────────────────────────────────────

    def scan_qr(
        self,
        req: QRScanRequest,
        organization_id: UUID,
        tenant_schema: str,
    ) -> dict:
        # Extract serial number from URL
        sr_number = self._extract_serial_from_url(req.url, tenant_schema)

        # scoped to organization
        item = self.item_repo.get_by_serial(sr_number, organization_id)
        if not item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Serial Number is not found",
            )

        qr_settings = self.activation_repo.get_active_settings_by_products(
            [item.product_id], organization_id
        )
        if not qr_settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please configure the primary settings for the product QR code before proceeding or scanning.",
            )

        # Already activated
        if not item.qr_deactive and not item.qr_deactive_unit:
            return {
                "message": "This QR code is already activated and ready for use.",
                "status": "activated",
                "sr_number": item.serial_number,
                "product_id": item.product_id,
            }

        # Check batch size limit using COUNT query (memory efficient)
        existing_count = self.activation_repo.count_activated_serials_in_batch(
            batch=qr_settings.dispatch_batch,
            organization_id=organization_id,
            created_after=qr_settings.created_at,
        )
        existing_serials = list(
            filter(None, (req.serialNumbers or "").split(","))
        )
        total = len(existing_serials) + 1 + existing_count

        if total > qr_settings.batch_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="D-Batch limit exceeded. Increase its size or create new D-batch, in settings tab.",
            )

        return {
            "message": "QR code is not activated. Please activate it to continue.",
            "status": "not_activated",
            "sr_number": item.serial_number,
            "product_id": item.product_id,
        }

    def _extract_serial_from_url(self, url: str, tenant_schema: str) -> str:
        """Extract serial number from QR URL with validation"""
        try:
            # Validate URL format
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid URL format",
                )

            # Follow redirects to get the long URL
            response = requests.head(url, allow_redirects=True, timeout=5)

            # Find the redirect URL containing tenant schema
            tenant = f"{tenant_schema}.{settings.domain}"
            long_url = next(
                (i.url for i in response.history if tenant in i.url), None
            )
            if not long_url:
                # If no redirect history, check final URL
                if tenant in response.url:
                    long_url = response.url
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid QR URL - tenant not found in redirect chain",
                    )

            # Extract serial number from path (second-to-last segment)
            path_parts = urlparse(long_url).path.strip("/").split("/")
            if len(path_parts) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid QR URL structure",
                )
            return path_parts[-2]

        except requests.RequestException:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to validate QR URL",
            )

    # ── Product Activation ────────────────────────────────────────────────────

    def activate_products(self, srnumber: str, organization_id: UUID) -> None:
        serial_list = list(set([s.strip() for s in srnumber.split(",") if s.strip()]))

        invalid_serials = []

        # 1. BULK FETCH ITEMS
        items = self.item_repo.get_by_serials(serial_list, organization_id)
        item_map = {i.serial_number: i for i in items}

        # 2. VALID SERIAL CHECK
        product_ids = set()
        valid_serials = []

        for serial in serial_list:
            if serial not in item_map:
                invalid_serials.append(serial)
                continue
            product_ids.add(item_map[serial].product_id)
            valid_serials.append(serial)

        if not valid_serials:
            raise HTTPException(status_code=400, detail="No valid serials found")

        # 3. BULK FETCH SETTINGS
        settings = self.activation_repo.get_active_settings_by_products(
            list(product_ids),
            organization_id
        )
        settings_map = {s.product_id: s for s in settings}

        # 4. BULK FETCH ACTIVATIONS
        existing = self.activation_repo.get_by_serials(valid_serials, organization_id)
        existing_map = {e.serial_number: e for e in existing}

        now = datetime.now(UTC)

        # 5. PREPARE UPDATES
        product_counter = {}
        new_rows = []

        for serial in valid_serials:
            item = item_map[serial]
            qr_settings = settings_map.get(item.product_id)

            if not qr_settings:
                invalid_serials.append(serial)
                continue

            activation = existing_map.get(serial)

            if activation:
                activation.manufacturing_date = qr_settings.manufacturing_date
                activation.expiry_date = qr_settings.expiry_date
                activation.mrp = qr_settings.mrp
                activation.updated_at = now
            else:
                new_rows.append({
                    "serial_number": serial,
                    "product_id": item.product_id,
                    "organization_id": organization_id,
                    "manufacturing_date": qr_settings.manufacturing_date,
                    "expiry_date": qr_settings.expiry_date,
                    "manufacturing_unit": qr_settings.manufacturing_unit,
                    "destination_market": qr_settings.destination_market,
                    "mrp": qr_settings.mrp,
                    "dispatch_batch": qr_settings.dispatch_batch,
                    "currency": qr_settings.currency,
                    "qr_settings": False,
                })

            # only count first activation
            if item.qr_deactive or item.qr_deactive_unit:
                product_counter[item.product_id] = product_counter.get(item.product_id, 0) + 1
                item.qr_deactive = False
                item.qr_deactive_unit = False

        # 6. VALIDATION COMPLETE - RAISE BEFORE COMMIT
        if invalid_serials:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid serial numbers: {', '.join(invalid_serials)}",
            )

        try:
            # 7. BULK PRODUCT COUNTER UPDATE
            for product_id, count in product_counter.items():
                self.db.execute(
                    update(QRProduct)
                    .where(
                        QRProduct.id == product_id,
                        QRProduct.organization_id == organization_id
                    )
                    .values(
                        num_activated_qr=QRProduct.num_activated_qr + count
                    )
                )

            # 8. BULK INSERT
            if new_rows:
                self.db.bulk_insert_mappings(QRActivationParameters, new_rows)

            # 9. FINAL COMMIT
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    # ── QR Settings ──────────────────────────────────────────────────────────

    def create_or_update_qr_settings(
        self,
        data: QRSettingsCreateRequest,
        organization_id: UUID,
    ) -> None:
        product = self.get_product(data.product, organization_id)

        if not product.warranty_period_months:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Warranty period not configured for this product",
            )

        expiry_date = data.manufacturing_date + relativedelta(
            months=product.warranty_period_months
        )

        market = self.market_repo.get_active_by_name(
            data.destination_market, organization_id
        )
        if not market:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Destination Market not found",
            )

        inactive_count = self.item_repo.count_inactive_by_product(
            data.product, organization_id
        )
        if data.batch_size > inactive_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Total blocks generated is {inactive_count}. Batch size can be at most {inactive_count}.",
            )

        existing = self.activation_repo.get_settings_by_batch(
            data.dispatch_batch, data.product, organization_id
        )

        if existing and not data.append_to_existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f'Batch "{data.dispatch_batch}" already active for "{existing.destination_market}". Set append_to_existing=true to update.',
            )

        new_data = {
            "product_id": data.product,
            "organization_id": organization_id,
            "dispatch_batch": data.dispatch_batch,
            "manufacturing_date": data.manufacturing_date,
            "expiry_date": expiry_date,
            "manufacturing_unit": data.manufacturing_unit,
            "currency": market.currency_code,
            "destination_market": data.destination_market,
            "mrp": data.mrp,
            "batch_size": data.batch_size,
            "qr_settings": True,
          #  "history": False,
        }

        if not existing:
            self.activation_repo.create_settings(new_data)
        else:
            self.activation_repo.archive_and_create(existing, new_data)

    def get_qr_settings(
        self, product_id: UUID, organization_id: UUID
    ) -> dict:
        product = self.get_product(product_id, organization_id)
        qr_settings = self.activation_repo.get_active_settings(
            product_id, organization_id
        )
        if not qr_settings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="QR parameters for this product have not been set up yet.",
            )
        return {
            "manufacturing_date": qr_settings.manufacturing_date,
            "manufacturing_unit": qr_settings.manufacturing_unit,
            "expiry_date": qr_settings.expiry_date,
            "mrp": qr_settings.mrp,
            "destination_market": qr_settings.destination_market,
            "dispatch_batch": qr_settings.dispatch_batch,
            "batch_size": qr_settings.batch_size,
            "currency": qr_settings.currency,
            "prefix": getattr(product, "serial_prefix", None),
        }