"""Unit and integration tests for invitation creation and logic"""

from uuid import UUID, uuid4

from fastapi import status

from app.repositories.invitation_repository import InvitationRepository
from app.services.invitation_service import InvitationService

# -------- UNIT TESTS --------


def test_create_invitation_with_team_ids_as_uuids(
    db_session, test_organization, test_user
):
    service = InvitationService(db_session)
    team_ids = [uuid4(), uuid4()]
    invitation_data = {
        "organization_id": test_organization.id,
        "email": "invitee@example.com",
        "first_name": "Invitee",
        "last_name": "User",
        "role_id": None,
        "team_ids": team_ids,
        "message": "Welcome!",
        "extra_data": {},
    }
    inviter_permissions = ["user.invite"]
    result = service.create_invitation(
        invitation_data,
        inviter_id=test_user.id,
        inviter_permissions=inviter_permissions,
    )
    assert result["email"] == "invitee@example.com"
    assert result["team_ids"] == [str(tid) for tid in team_ids]
    assert result["status"] == "pending"
    assert isinstance(result["id"], UUID)


def test_duplicate_invitation_cancels_old(db_session, test_organization, test_user):
    service = InvitationService(db_session)
    email = "dupe@example.com"
    inviter_permissions = ["user.invite"]
    invitation_data = {
        "organization_id": test_organization.id,
        "email": email,
        "first_name": "First",
        "last_name": "User",
        "role_id": None,
        "team_ids": [],
        "message": None,
        "extra_data": {},
    }
    # First invitation
    result1 = service.create_invitation(
        invitation_data.copy(),
        inviter_id=test_user.id,
        inviter_permissions=inviter_permissions,
    )
    # Second invitation (should cancel the first)
    result2 = service.create_invitation(
        invitation_data.copy(),
        inviter_id=test_user.id,
        inviter_permissions=inviter_permissions,
    )
    repo = InvitationRepository(db_session)
    old_inv = repo.get_invitation_by_id(result1["id"])
    assert old_inv.status == "cancelled"
    assert result2["email"] == email
    assert result2["status"] == "pending"


# -------- INTEGRATION TESTS --------


def test_post_invitations_api(client, test_organization, test_user, auth_headers):
    team_ids = [str(uuid4()), str(uuid4())]
    payload = {
        "organization_id": str(test_organization.id),
        "email": "apiinvite@example.com",
        "first_name": "Api",
        "last_name": "User",
        "role_id": None,
        "team_ids": team_ids,
        "message": "API Test",
        "extra_data": {},
    }
    response = client.post("/api/v1/invitations", json=payload, headers=auth_headers)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["email"] == "apiinvite@example.com"
    assert data["team_ids"] == team_ids
    assert data["status"] == "pending"
    assert "id" in data


def test_post_invitations_api_duplicate(
    client, test_organization, test_user, auth_headers
):
    team_ids = [str(uuid4())]
    payload = {
        "organization_id": str(test_organization.id),
        "email": "apidup@example.com",
        "first_name": "Api",
        "last_name": "Dup",
        "role_id": None,
        "team_ids": team_ids,
        "message": None,
        "extra_data": {},
    }
    # First invite
    resp1 = client.post("/api/v1/invitations", json=payload, headers=auth_headers)
    assert resp1.status_code == status.HTTP_201_CREATED
    # Second invite (should cancel the first)
    resp2 = client.post("/api/v1/invitations", json=payload, headers=auth_headers)
    assert resp2.status_code == status.HTTP_201_CREATED
    data2 = resp2.json()
    assert data2["email"] == "apidup@example.com"
    assert data2["status"] == "pending"
