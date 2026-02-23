"""Tests for PaymentAuditLogRepository"""

import uuid
from datetime import datetime, timedelta, UTC

import pytest

from app.models.base import PaymentAuditAction
from app.repositories.payment_audit_log_repository import PaymentAuditLogRepository


@pytest.fixture
def audit_log_repo(db_session):
    """Create a PaymentAuditLogRepository instance"""
    return PaymentAuditLogRepository(db_session)


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_payment_id():
    """Test payment ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


def test_create_audit_log(
    audit_log_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test creating an audit log entry"""
    data = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "old_values": None,
        "new_values": {"amount": 100.00, "status": "Draft"},
    }

    audit_log = audit_log_repo.create(data)

    assert audit_log.id is not None
    assert audit_log.organization_id == test_organization_id
    assert audit_log.payment_id == test_payment_id
    assert audit_log.action == PaymentAuditAction.CREATE
    assert audit_log.user_id == test_user_id
    assert audit_log.new_values == {"amount": 100.00, "status": "Draft"}
    assert audit_log.timestamp is not None


def test_get_by_payment_id_ordered_by_timestamp_desc(
    audit_log_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test getting audit logs by payment ID ordered by timestamp DESC (newest first)"""
    # Create multiple audit log entries with different timestamps
    now = datetime.now(UTC)

    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "new_values": {"status": "Draft"},
        "timestamp": now - timedelta(hours=2),
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.UPDATE,
        "user_id": test_user_id,
        "old_values": {"amount": 100.00},
        "new_values": {"amount": 150.00},
        "timestamp": now - timedelta(hours=1),
    }
    data_3 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CONFIRM,
        "user_id": test_user_id,
        "old_values": {"status": "Draft"},
        "new_values": {"status": "Confirmed"},
        "timestamp": now,
    }

    audit_log_repo.create(data_1)
    audit_log_repo.create(data_2)
    audit_log_repo.create(data_3)

    # Get all audit logs for the payment
    audit_logs = audit_log_repo.get_by_payment_id(test_payment_id, test_organization_id)

    assert len(audit_logs) == 3
    # Verify they are ordered by timestamp DESC (newest first)
    assert audit_logs[0].action == PaymentAuditAction.CONFIRM
    assert audit_logs[1].action == PaymentAuditAction.UPDATE
    assert audit_logs[2].action == PaymentAuditAction.CREATE


def test_list_by_organization_no_filters(
    audit_log_repo, test_organization_id, test_user_id
):
    """Test listing audit logs by organization without date filters"""
    payment_id_1 = uuid.uuid4()
    payment_id_2 = uuid.uuid4()

    # Create audit logs for different payments in the same organization
    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": payment_id_1,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "new_values": {"status": "Draft"},
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": payment_id_2,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "new_values": {"status": "Draft"},
    }

    audit_log_repo.create(data_1)
    audit_log_repo.create(data_2)

    # List all audit logs for the organization
    audit_logs, total_count = audit_log_repo.list_by_organization(test_organization_id)

    assert len(audit_logs) == 2
    assert total_count == 2
    assert all(log.organization_id == test_organization_id for log in audit_logs)


def test_list_by_organization_with_date_filters(
    audit_log_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test listing audit logs with date filtering"""
    now = datetime.now(UTC)
    yesterday = now - timedelta(days=1)
    two_days_ago = now - timedelta(days=2)
    three_days_ago = now - timedelta(days=3)

    # Create audit logs with different timestamps
    data_1 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "new_values": {"status": "Draft"},
        "timestamp": three_days_ago,
    }
    data_2 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.UPDATE,
        "user_id": test_user_id,
        "new_values": {"amount": 150.00},
        "timestamp": two_days_ago,
    }
    data_3 = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CONFIRM,
        "user_id": test_user_id,
        "new_values": {"status": "Confirmed"},
        "timestamp": yesterday,
    }

    audit_log_repo.create(data_1)
    audit_log_repo.create(data_2)
    audit_log_repo.create(data_3)

    # Filter by date range (last 2 days)
    audit_logs, total_count = audit_log_repo.list_by_organization(
        test_organization_id, date_from=two_days_ago, date_to=now
    )

    assert len(audit_logs) == 2
    assert total_count == 2
    # Should include UPDATE and CONFIRM, but not CREATE
    actions = [log.action for log in audit_logs]
    assert PaymentAuditAction.UPDATE in actions
    assert PaymentAuditAction.CONFIRM in actions
    assert PaymentAuditAction.CREATE not in actions


def test_list_by_organization_with_pagination(
    audit_log_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test listing audit logs with pagination"""
    # Create 5 audit log entries
    for i in range(5):
        data = {
            "organization_id": test_organization_id,
            "payment_id": test_payment_id,
            "action": PaymentAuditAction.UPDATE,
            "user_id": test_user_id,
            "new_values": {"iteration": i},
        }
        audit_log_repo.create(data)

    # Get first page (2 items per page)
    page_1, total_count = audit_log_repo.list_by_organization(
        test_organization_id, page=1, page_size=2
    )

    assert len(page_1) == 2
    assert total_count == 5

    # Get second page
    page_2, total_count = audit_log_repo.list_by_organization(
        test_organization_id, page=2, page_size=2
    )

    assert len(page_2) == 2
    assert total_count == 5

    # Get third page (should have 1 item)
    page_3, total_count = audit_log_repo.list_by_organization(
        test_organization_id, page=3, page_size=2
    )

    assert len(page_3) == 1
    assert total_count == 5


def test_multi_tenancy_isolation(audit_log_repo, test_payment_id, test_user_id):
    """Test that organization_id filtering works correctly"""
    org_1 = uuid.uuid4()
    org_2 = uuid.uuid4()

    # Create audit log for org_1
    data_1 = {
        "organization_id": org_1,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "new_values": {"status": "Draft"},
    }
    audit_log_repo.create(data_1)

    # Query with org_2 should return empty
    audit_logs = audit_log_repo.get_by_payment_id(test_payment_id, org_2)
    assert len(audit_logs) == 0

    # Query with org_1 should return the audit log
    audit_logs = audit_log_repo.get_by_payment_id(test_payment_id, org_1)
    assert len(audit_logs) == 1


def test_audit_logs_are_append_only(
    audit_log_repo, test_organization_id, test_payment_id, test_user_id
):
    """Test that audit logs are append-only (no update or delete methods)"""
    # Verify that the repository doesn't have update or delete methods
    assert not hasattr(audit_log_repo, "update")
    assert not hasattr(audit_log_repo, "delete")

    # Create an audit log
    data = {
        "organization_id": test_organization_id,
        "payment_id": test_payment_id,
        "action": PaymentAuditAction.CREATE,
        "user_id": test_user_id,
        "new_values": {"status": "Draft"},
    }
    audit_log = audit_log_repo.create(data)

    # Verify it was created
    assert audit_log.id is not None

    # Verify we can only read, not modify
    audit_logs = audit_log_repo.get_by_payment_id(test_payment_id, test_organization_id)
    assert len(audit_logs) == 1
