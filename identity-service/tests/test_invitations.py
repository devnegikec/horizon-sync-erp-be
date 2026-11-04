"""Unit and integration tests for invitation creation and logic"""

from datetime import UTC, datetime, timedelta
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


def test_create_invitation_with_owner_full_access(
    db_session, test_organization, test_user
):
    service = InvitationService(db_session)
    invitation_data = {
        "organization_id": test_organization.id,
        "email": "ownerinvite@example.com",
        "first_name": "Owner",
        "last_name": "User",
        "role_id": None,
        "team_ids": [],
        "message": "Welcome!",
        "extra_data": {},
    }
    inviter_permissions = ["*.*"]
    result = service.create_invitation(
        invitation_data,
        inviter_id=test_user.id,
        inviter_permissions=inviter_permissions,
    )

    assert result["email"] == "ownerinvite@example.com"
    assert result["status"] == "pending"
    assert isinstance(result["id"], UUID)


def test_duplicate_invitation_reuses_active_invite(
    db_session, test_organization, test_user
):
    """Re-inviting while an invitation is still valid must not create/send one.

    The recipient already holds a working link, so the existing invitation is
    returned unchanged with no new token (the endpoint skips the email).
    """
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
        "extra_data": {"warehouse_ids": ["wh-1"]},
    }
    # First invitation
    result1 = service.create_invitation(
        invitation_data.copy(),
        inviter_id=test_user.id,
        inviter_permissions=inviter_permissions,
    )
    assert result1["token"], "first invitation must carry a token to email"

    # Second invitation (active one exists -> reused, nothing to send, but the
    # request's own extra_data - e.g. warehouse_ids - must be applied)
    repeat_data = invitation_data.copy()
    repeat_data["extra_data"] = {"warehouse_ids": ["wh-2"]}
    result2 = service.create_invitation(
        repeat_data,
        inviter_id=test_user.id,
        inviter_permissions=inviter_permissions,
    )

    repo = InvitationRepository(db_session)
    assert result2["id"] == result1["id"]
    assert result2["token"] is None
    assert result2["already_invited"] is True
    assert result2["status"] == "pending"
    assert result2["extra_data"]["warehouse_ids"] == ["wh-2"]

    pending = repo.get_pending_invitations(email, test_organization.id)
    assert len(pending) == 1
    assert pending[0].id == result1["id"]


def test_expired_invitation_is_superseded(db_session, test_organization, test_user):
    """An expired invitation is closed and a fresh one is issued."""
    service = InvitationService(db_session)
    repo = InvitationRepository(db_session)
    email = "expired@example.com"
    invitation_data = {
        "organization_id": test_organization.id,
        "email": email,
        "first_name": "Late",
        "last_name": "User",
        "role_id": None,
        "team_ids": [],
        "message": None,
        "extra_data": {},
    }

    result1 = service.create_invitation(
        invitation_data.copy(),
        inviter_id=test_user.id,
        inviter_permissions=["user.invite"],
    )

    # Force the first invitation past its expiry window.
    repo.update_invitation(
        repo.get_invitation_by_id(result1["id"]),
        {"expires_at": datetime.now(UTC) - timedelta(hours=1)},
    )

    result2 = service.create_invitation(
        invitation_data.copy(),
        inviter_id=test_user.id,
        inviter_permissions=["user.invite"],
    )

    assert result2["id"] != result1["id"]
    assert result2["token"]
    assert not result2.get("already_invited")

    old = repo.get_invitation_by_id(result1["id"])
    assert old.status in {"expired", "cancelled"}
    assert [
        inv.id for inv in repo.get_pending_invitations(email, test_organization.id)
    ] == [result2["id"]]


def test_api_reinvite_does_not_send_second_email(
    client, test_organization, test_user, auth_headers
):
    payload = {
        "organization_id": str(test_organization.id),
        "email": "repeat@example.com",
        "first_name": "Repeat",
        "last_name": "User",
        "role_id": None,
        "team_ids": [],
        "message": "API Test",
        "extra_data": {},
    }
    first = client.post("/api/v1/invitations", json=payload, headers=auth_headers)
    assert first.status_code == status.HTTP_201_CREATED
    assert first.json()["already_invited"] is False

    second = client.post("/api/v1/invitations", json=payload, headers=auth_headers)
    assert second.status_code == status.HTTP_201_CREATED
    body = second.json()
    assert body["already_invited"] is True
    assert body["id"] == first.json()["id"]


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
