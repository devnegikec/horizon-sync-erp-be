"""Organization Onboarding API endpoint

Called by the Identity Service (service-to-service, no user auth) immediately
after a new organization is created to seed default master data:
  - Base currency
  - Standard UOMs
  - Default tax templates
  - Default item groups
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.organization_onboarding_service import OrganizationOnboardingService

logger = logging.getLogger(__name__)

router = APIRouter()


class OrganizationDefaultsRequest(BaseModel):
    """Request body for seeding organization defaults."""

    organization_id: UUID = Field(..., description="UUID of the newly created organization")
    base_currency: str = Field(
        default="USD",
        max_length=3,
        description="ISO 4217 currency code (3 uppercase letters)",
    )
    created_by: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="UUID string of the user who created the organization",
    )

    @field_validator("base_currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("base_currency must be a 3-letter ISO code (e.g. USD)")
        return v

    @field_validator("created_by")
    @classmethod
    def validate_created_by(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("created_by cannot be empty")
        return v


class OrganizationDefaultsResponse(BaseModel):
    """Response body for organization defaults seeding."""

    success: bool
    organization_id: UUID
    message: str
    summary: dict | None = None


@router.post(
    "/setup/organization-defaults",
    response_model=OrganizationDefaultsResponse,
    status_code=status.HTTP_200_OK,
    summary="Seed default master data for a new organization",
    description=(
        "Seeds default currency, UOMs, tax templates, and item groups for a newly "
        "created organization. This endpoint is idempotent and is called by the "
        "Identity Service during organization creation. No user authentication required."
    ),
    tags=["Organization Setup"],
)
async def seed_organization_defaults(
    request: OrganizationDefaultsRequest,
    db: Session = Depends(get_db),
) -> OrganizationDefaultsResponse:
    """
    Seed default master data for a new organization.

    This endpoint is called by the Identity Service (service-to-service) right
    after a new organization is created. It is idempotent — calling it multiple
    times for the same organization is safe.

    **Seeded data:**
    - **Currency**: Base currency as the organization's default currency
    - **UOMs**: ~40 standard units of measure (PCS, KG, LTR, MTR, HR, etc.)
    - **Tax Templates**: Standard Input and Output tax templates (0% placeholder)
    - **Item Groups**: Default hierarchy (All Items → Products, Services, Raw Materials, etc.)

    **Request Body:**
    - `organization_id`: UUID of the organization
    - `base_currency`: ISO currency code (default: USD)
    - `created_by`: UUID of the user who created the organization

    **Returns:** Summary of records created/skipped per category.
    """
    service = OrganizationOnboardingService(db)

    try:
        summary = service.seed_defaults(
            organization_id=request.organization_id,
            base_currency=request.base_currency,
            created_by=request.created_by,
        )

        return OrganizationDefaultsResponse(
            success=True,
            organization_id=request.organization_id,
            message="Organization defaults seeded successfully",
            summary=summary,
        )

    except Exception as e:
        logger.error(
            "Failed to seed organization defaults",
            extra={
                "organization_id": str(request.organization_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed organization defaults: {str(e)}",
        )
