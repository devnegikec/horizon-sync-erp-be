"""Service layer for Landing Page Config module."""

import logging
import os
import uuid
from datetime import UTC, datetime

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.repositories.landing_page_repository import LandingPageRepository
from app.repositories.qr_product_repository import QRProductRepository
from app.schemas.landing_page import (
    LandingPageConfigCreate,
    LandingPageConfigOut,
    LandingPageConfigUpdate,
)

logger = logging.getLogger(__name__)

# Maximum upload size: 5 MB
MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg"}


class LandingPageService:
    """Business logic for landing page configurations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = LandingPageRepository(db)
        self.product_repo = QRProductRepository(db)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _get_product(self, product_id: uuid.UUID, organization_id: uuid.UUID):
        """Validate product exists and belongs to the org. Raises 404/403."""
        product = self.product_repo.get_by_id(product_id, organization_id)
        if not product:
            # Check if product exists at all (for a better error message)
            from app.models.qr_product import QRProduct

            exists = (
                self.db.query(QRProduct)
                .filter(
                    QRProduct.id == product_id,
                    QRProduct.deleted_at.is_(None),
                )
                .first()
            )
            if exists:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Product does not belong to this organization",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR product not found",
            )
        return product

    def _config_to_dict(self, config) -> dict:
        """Convert an ORM LandingPageConfig to a dict suitable for the response."""
        return {
            "id": config.id,
            "product_id": config.product_id,
            "organization_id": config.organization_id,
            "logo_url": config.logo_url,
            "banner_image_url": config.banner_image_url,
            "primary_color": config.primary_color,
            "accent_color": config.accent_color,
            "product_details": config.product_details or {},
            "social_links": config.social_links or [],
            "feedback": config.feedback or {},
            "warranty": config.warranty or {},
            "custom_cta": config.custom_cta or {},
            "footer": config.footer or {},
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None,
        }

    def _merge_nested(self, existing: dict | None, incoming: dict) -> dict:
        """Deep-merge incoming dict into existing dict. Used for PATCH partial updates."""
        if existing is None:
            return incoming
        merged = dict(existing)
        merged.update({k: v for k, v in incoming.items() if v is not None})
        return merged

    # ── CRUD ─────────────────────────────────────────────────────────────

    def get_config(
        self, product_id: uuid.UUID, organization_id: uuid.UUID
    ) -> LandingPageConfigOut:
        """Fetch the landing page config for a product."""
        self._get_product(product_id, organization_id)
        config = self.repo.get_by_product(product_id, organization_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No landing page config exists for this product",
            )
        return LandingPageConfigOut.model_validate(self._config_to_dict(config))

    def get_config_public(self, product_id: uuid.UUID) -> LandingPageConfigOut:
        """Fetch landing page config by product ID only (public, no auth).

        Resolves the organization_id from the product itself.
        """
        from app.models.qr_product import QRProduct

        product = (
            self.db.query(QRProduct)
            .filter(
                QRProduct.id == product_id,
                QRProduct.deleted_at.is_(None),
            )
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR product not found",
            )

        organization_id = product.organization_id
        config = self.repo.get_by_product(product_id, organization_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No landing page config exists for this product",
            )
        return LandingPageConfigOut.model_validate(self._config_to_dict(config))

    def get_config_by_sku(self, sku: str) -> LandingPageConfigOut:
        """Fetch landing page config by product SKU (public, no auth).

        Looks up the QR product via Item.sku, then resolves the config.
        Also tries direct GTIN match on QRProduct as fallback.
        """
        from app.models.item import Item
        from app.models.qr_product import QRProduct

        # Try Item.sku → QRProduct
        item = (
            self.db.query(Item)
            .filter(
                Item.sku == sku,
                Item.qr_product_id.is_not(None),
                Item.deleted_at.is_(None),
            )
            .first()
        )
        if item and item.qr_product_id:
            product_id = item.qr_product_id
        else:
            # Fallback: try GTIN match directly on QRProduct
            product = (
                self.db.query(QRProduct)
                .filter(
                    QRProduct.gtin == sku,
                    QRProduct.deleted_at.is_(None),
                )
                .first()
            )
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No product found for this SKU",
                )
            product_id = product.id

        return self.get_config_public(product_id)

    def create_config(
        self,
        product_id: uuid.UUID,
        data: LandingPageConfigCreate,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LandingPageConfigOut:
        """Create a landing page config for a product."""
        self._get_product(product_id, organization_id)

        # Ensure only one config per product
        existing = self.repo.get_by_product(product_id, organization_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Landing page config already exists for this product. Use PATCH to update.",
            )

        payload = data.model_dump()
        payload["product_id"] = product_id
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        payload["created_at"] = datetime.now(UTC)
        payload["updated_at"] = datetime.now(UTC)

        # Convert nested Pydantic models to dicts for JSONB columns
        for field in (
            "product_details",
            "social_links",
            "feedback",
            "warranty",
            "custom_cta",
            "footer",
        ):
            val = payload.get(field)
            if hasattr(val, "model_dump"):
                payload[field] = val.model_dump()

        config = self.repo.create(payload)
        logger.info(
            "Landing page config created: product_id=%s org=%s",
            product_id,
            organization_id,
        )
        return LandingPageConfigOut.model_validate(self._config_to_dict(config))

    def update_config(
        self,
        product_id: uuid.UUID,
        data: LandingPageConfigUpdate,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> LandingPageConfigOut:
        """Partial update of the landing page config."""
        self._get_product(product_id, organization_id)

        config = self.repo.get_by_product(product_id, organization_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No landing page config exists for this product. Use POST to create one.",
            )

        update_dict = data.model_dump(exclude_unset=True)

        # Merge nested JSONB fields
        for field in (
            "product_details",
            "social_links",
            "feedback",
            "warranty",
            "custom_cta",
            "footer",
        ):
            if field in update_dict and update_dict[field] is not None:
                incoming = update_dict[field]
                if hasattr(incoming, "model_dump"):
                    incoming = incoming.model_dump()
                existing = getattr(config, field) or {}
                # For array fields (social_links, custom_fields, custom_links),
                # replace entirely. For dict fields, deep-merge.
                if field in ("social_links",):
                    update_dict[field] = incoming  # replace
                else:
                    update_dict[field] = self._merge_nested(existing, incoming)

        update_dict["updated_by"] = user_id
        update_dict["updated_at"] = datetime.now(UTC)

        config = self.repo.update(config, update_dict)
        logger.info(
            "Landing page config updated: product_id=%s org=%s",
            product_id,
            organization_id,
        )
        return LandingPageConfigOut.model_validate(self._config_to_dict(config))

    def delete_config(self, product_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        """Delete the landing page config for a product."""
        self._get_product(product_id, organization_id)

        config = self.repo.get_by_product(product_id, organization_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No landing page config exists for this product",
            )

        self.repo.delete(config)
        logger.info(
            "Landing page config deleted: product_id=%s org=%s",
            product_id,
            organization_id,
        )

    # ── Image Upload ─────────────────────────────────────────────────────

    async def upload_image(
        self,
        product_id: uuid.UUID,
        file: UploadFile,
        image_type: str,  # "logo" or "banner"
        organization_id: uuid.UUID,
    ) -> dict:
        """Upload a logo or banner image and return the URL."""
        self._get_product(product_id, organization_id)

        # Validate image type
        if image_type not in ("logo", "banner"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='image_type must be "logo" or "banner"',
            )

        # Validate content type
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PNG and JPEG images are allowed",
            )

        # Read and validate size
        contents = await file.read()
        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Image must be under 5 MB",
            )

        # Determine file extension from content type
        ext = "png" if file.content_type == "image/png" else "jpg"

        # If GCS is configured, upload there; otherwise store locally
        if settings.gcs_bucket:
            url = await self._upload_to_gcs(
                contents, product_id, organization_id, image_type, ext
            )
        else:
            url = self._save_locally(
                contents, product_id, organization_id, image_type, ext
            )

        logger.info(
            "Image uploaded: product_id=%s type=%s url=%s",
            product_id,
            image_type,
            url,
        )
        return {"url": url}

    async def _upload_to_gcs(
        self,
        contents: bytes,
        product_id: uuid.UUID,
        organization_id: uuid.UUID,
        image_type: str,
        ext: str,
    ) -> str:
        """Upload image to Google Cloud Storage."""
        from google.cloud import storage  # type: ignore[import]

        if settings.gcs_credentials_path:
            client = storage.Client.from_service_account_json(
                settings.gcs_credentials_path
            )
        else:
            client = storage.Client()

        bucket = client.bucket(settings.gcs_bucket)
        object_name = (
            f"landing-pages/{organization_id}/{product_id}/"
            f"{image_type}_{uuid.uuid4().hex[:8]}.{ext}"
        )
        blob = bucket.blob(object_name)
        blob.upload_from_string(contents, content_type=f"image/{ext}")

        return blob.public_url

    def _save_locally(
        self,
        contents: bytes,
        product_id: uuid.UUID,
        organization_id: uuid.UUID,
        image_type: str,
        ext: str,
    ) -> str:
        """Save image to local filesystem (dev fallback when GCS not configured).

        Uses settings.upload_dir when set (e.g. Railway volume mount at /uploads).
        Otherwise falls back to <project_root>/uploads/landing-pages.
        """
        if settings.upload_dir:
            upload_dir = os.path.join(
                settings.upload_dir,
                "landing-pages",
                str(organization_id),
                str(product_id),
            )
        else:
            upload_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "uploads",
                "landing-pages",
                str(organization_id),
                str(product_id),
            )
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{image_type}_{uuid.uuid4().hex[:8]}.{ext}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, "wb") as f:
            f.write(contents)

        # Return a relative URL that can be served by the static files mount
        return f"/static/landing-pages/{organization_id}/{product_id}/{filename}"
