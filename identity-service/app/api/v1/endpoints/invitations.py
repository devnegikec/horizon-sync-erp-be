"""Invitation management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvitationAlreadyAcceptedException,
    InvitationExpiredException,
    InvitationNotFoundException,
    PermissionDeniedException,
    UserAlreadyExistsException,
)
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.invitation import (
    InvitationAcceptRequest,
    InvitationAcceptResponse,
    InvitationCreate,
    InvitationListResponse,
    InvitationResponse,
)
from app.services.invitation_service import InvitationService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/invitations",
    response_model=InvitationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send invitation",
    description="Send an invitation to a user to join an organization",
)
async def send_invitation(
    invitation: InvitationCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Send an invitation to a user.

    Requires the 'user.invite' or 'invitation.create' permission.

    **Request Body:**
    - **organization_id**: Organization UUID to invite to
    - **email**: Email address to invite
    - **first_name**: Optional first name
    - **last_name**: Optional last name
    - **role_id**: Optional role to assign
    - **team_ids**: Optional list of team UUIDs
    - **message**: Optional personal message
    """
    logger.info(f"User {current_user.id} sending invitation to {invitation.email}")

    invitation_service = InvitationService(db)

    try:
        result = invitation_service.create_invitation(
            invitation.model_dump(),
            inviter_id=current_user.id,
            inviter_permissions=current_user.permissions,
        )
        logger.info(f"Invitation created: {result['id']}")
        return InvitationResponse(**result)

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except UserAlreadyExistsException as e:
        logger.warning(f"User already exists: {invitation.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error creating invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create invitation",
        )


@router.get(
    "/invitations",
    response_model=InvitationListResponse,
    summary="List invitations",
    description="Get paginated list of invitations",
)
async def list_invitations(
    organization_id: UUID = Query(..., description="Organization UUID"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Maximum records to return"),
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status"
    ),
    search: str | None = Query(None, description="Search by email or name"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List invitations for an organization.

    **Query Parameters:**
    - **organization_id**: Organization UUID (required)
    - **skip**: Number of records to skip (default: 0)
    - **limit**: Maximum records to return (default: 10, max: 100)
    - **status**: Filter by status (pending, accepted, expired, cancelled)
    - **search**: Search term for email or name
    """
    logger.info(f"Listing invitations for org: {organization_id}")

    invitation_service = InvitationService(db)

    try:
        result = invitation_service.list_invitations(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            status=status_filter,
            search=search,
        )

        logger.info(f"Retrieved {len(result['data'])} invitations")

        return InvitationListResponse(**result)

    except Exception as e:
        logger.error(f"Error listing invitations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitations",
        )


@router.get(
    "/invitations/{invitation_id}",
    response_model=InvitationResponse,
    summary="Get invitation",
    description="Get a specific invitation by ID",
)
async def get_invitation(
    invitation_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get a specific invitation by ID.

    **Path Parameters:**
    - **invitation_id**: UUID of the invitation
    """
    logger.info(f"Fetching invitation: {invitation_id}")

    invitation_service = InvitationService(db)

    try:
        result = invitation_service.get_invitation_by_id(invitation_id)
        logger.info(f"Invitation fetched: {invitation_id}")
        return InvitationResponse(**result)

    except InvitationNotFoundException as e:
        logger.warning(f"Invitation not found: {invitation_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error fetching invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve invitation",
        )


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel invitation",
    description="Cancel a pending invitation",
)
async def cancel_invitation(
    invitation_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a pending invitation.

    Requires the 'user.invite' or 'invitation.create' permission.

    **Path Parameters:**
    - **invitation_id**: UUID of the invitation to cancel
    """
    logger.info(f"Cancelling invitation: {invitation_id}")

    invitation_service = InvitationService(db)

    try:
        invitation_service.cancel_invitation(
            invitation_id,
            user_id=current_user.id,
            user_permissions=current_user.permissions,
        )
        logger.info(f"Invitation cancelled: {invitation_id}")

    except InvitationNotFoundException as e:
        logger.warning(f"Invitation not found: {invitation_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except InvitationAlreadyAcceptedException as e:
        logger.warning(f"Cannot cancel invitation {invitation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error cancelling invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel invitation",
        )


@router.post(
    "/invitations/{invitation_id}/resend",
    response_model=InvitationResponse,
    summary="Resend invitation",
    description="Resend an invitation with a new token",
)
async def resend_invitation(
    invitation_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Resend an invitation with a new token.

    Requires the 'user.invite' or 'invitation.create' permission.

    **Path Parameters:**
    - **invitation_id**: UUID of the invitation to resend
    """
    logger.info(f"Resending invitation: {invitation_id}")

    invitation_service = InvitationService(db)

    try:
        result = invitation_service.resend_invitation(
            invitation_id,
            user_id=current_user.id,
            user_permissions=current_user.permissions,
        )
        logger.info(f"Invitation resent: {invitation_id}")
        return InvitationResponse(**result)

    except InvitationNotFoundException as e:
        logger.warning(f"Invitation not found: {invitation_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except PermissionDeniedException as e:
        logger.warning(f"Permission denied for user {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )

    except InvitationAlreadyAcceptedException as e:
        logger.warning(f"Cannot resend invitation {invitation_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error resending invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resend invitation",
        )


# Public endpoints (no authentication required)


@router.get(
    "/invitations/validate/{token}",
    summary="Validate invitation token",
    description="Validate an invitation token without accepting it",
)
async def validate_invitation_token(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Validate an invitation token.

    This is a public endpoint (no authentication required).

    **Path Parameters:**
    - **token**: Invitation token from the email
    """
    logger.info("Validating invitation token")

    invitation_service = InvitationService(db)

    try:
        result = invitation_service.validate_invitation(token)
        return result

    except InvitationNotFoundException as e:
        logger.warning("Invalid invitation token")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except InvitationExpiredException as e:
        logger.warning("Expired invitation token")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(e),
        )

    except InvitationAlreadyAcceptedException as e:
        logger.warning("Already accepted invitation")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.post(
    "/invitations/accept",
    response_model=InvitationAcceptResponse,
    summary="Accept invitation",
    description="Accept an invitation and create user account",
)
async def accept_invitation(
    request: InvitationAcceptRequest,
    db: Session = Depends(get_db),
):
    """
    Accept an invitation and create user account.

    This is a public endpoint (no authentication required).

    **Request Body:**
    - **token**: Invitation token from the email
    - **password**: Password for new account (min 8 characters)
    - **first_name**: Optional first name override
    - **last_name**: Optional last name override
    """
    logger.info("Accepting invitation")

    invitation_service = InvitationService(db)

    try:
        result = invitation_service.accept_invitation(
            token=request.token,
            password=request.password,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        logger.info(f"Invitation accepted, user created: {result['user_id']}")
        return InvitationAcceptResponse(**result)

    except InvitationNotFoundException as e:
        logger.warning("Invalid invitation token")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except InvitationExpiredException as e:
        logger.warning("Expired invitation token")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=str(e),
        )

    except InvitationAlreadyAcceptedException as e:
        logger.warning("Already accepted invitation")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    except Exception as e:
        logger.error(f"Error accepting invitation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to accept invitation",
        )
