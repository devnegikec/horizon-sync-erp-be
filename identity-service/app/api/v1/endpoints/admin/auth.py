"""Admin authentication endpoints for identity-service"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin
from app.models.role import UserOrganizationRole
from app.schemas.admin import AdminProfileResponse

router = APIRouter()


@router.get(
    "/me",
    response_model=AdminProfileResponse,
    summary="Get admin profile",
    description="Get current admin user profile with permissions. Requires system_admin user_type.",
)
async def get_admin_me(
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> AdminProfileResponse:
    """
    Return the authenticated admin's profile including organization_id and permissions.

    This is the authoritative source for admin identity in the admin portal.
    Only accessible to users with user_type == system_admin.
    """
    # Look up the admin's primary organization
    user_org_role = (
        db.query(UserOrganizationRole)
        .filter(
            UserOrganizationRole.user_id == current_user.id,
            UserOrganizationRole.is_active == True,  # noqa: E712
        )
        .order_by(UserOrganizationRole.is_primary.desc())
        .first()
    )

    organization_id = None
    if user_org_role:
        organization_id = str(user_org_role.organization_id)

    return AdminProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        display_name=current_user.display_name,
        user_type=current_user.user_type.value if current_user.user_type else "system_admin",
        organization_id=organization_id,
        permissions=current_user.permissions,
    )
