"""Tests for audit trail functionality"""

import pytest
from uuid import uuid4
from datetime import datetime, UTC

from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.services.audit_logger import AuditLogger


class TestAuditLogger:
    """Test audit logger service"""

    def test_log_account_creation(self, db_session):
        """Test logging account creation"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()
        user_id = "test-user"

        new_values = {
            "account_code": "1000",
            "account_name": "Test Account",
            "account_type": "asset",
            "currency": "USD",
            "status": "ACTIVE",
        }

        entry = audit_logger.log_account_change(
            account_id=account_id,
            action=AuditAction.CREATE,
            user_id=user_id,
            new_values=new_values,
        )

        db_session.commit()

        assert entry.account_id == account_id
        assert entry.action == AuditAction.CREATE.value
        assert entry.user_id == user_id
        assert "new" in entry.changes
        assert entry.changes["new"]["account_code"] == "1000"

    def test_log_account_update(self, db_session):
        """Test logging account update"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()
        user_id = "test-user"

        old_values = {
            "account_name": "Old Name",
            "status": "ACTIVE",
        }

        new_values = {
            "account_name": "New Name",
            "status": "ACTIVE",
        }

        entry = audit_logger.log_account_change(
            account_id=account_id,
            action=AuditAction.UPDATE,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )

        db_session.commit()

        assert entry.account_id == account_id
        assert entry.action == AuditAction.UPDATE.value
        assert "account_name" in entry.changes
        assert entry.changes["account_name"]["oldValue"] == "Old Name"
        assert entry.changes["account_name"]["newValue"] == "New Name"
        # Status didn't change, so it shouldn't be in changes
        assert "status" not in entry.changes

    def test_log_status_change(self, db_session):
        """Test logging status change"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()
        user_id = "test-user"

        old_values = {"status": "ACTIVE"}
        new_values = {"status": "INACTIVE"}

        entry = audit_logger.log_account_change(
            account_id=account_id,
            action=AuditAction.STATUS_CHANGE,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
        )

        db_session.commit()

        assert entry.action == AuditAction.STATUS_CHANGE.value
        assert "status" in entry.changes
        assert entry.changes["status"]["oldValue"] == "ACTIVE"
        assert entry.changes["status"]["newValue"] == "INACTIVE"

    def test_get_audit_trail(self, db_session):
        """Test retrieving audit trail"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()

        # Create multiple audit entries
        for i in range(5):
            audit_logger.log_account_change(
                account_id=account_id,
                action=AuditAction.UPDATE,
                user_id=f"user-{i}",
                old_values={"field": f"old-{i}"},
                new_values={"field": f"new-{i}"},
            )

        db_session.commit()

        # Get audit trail
        entries = audit_logger.get_audit_trail(account_id, limit=10)

        assert len(entries) == 5
        # Should be ordered by timestamp descending (newest first)
        assert entries[0].user_id == "user-4"
        assert entries[4].user_id == "user-0"

    def test_get_audit_trail_with_action_filter(self, db_session):
        """Test retrieving audit trail with action filter"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()

        # Create different types of audit entries
        audit_logger.log_account_change(
            account_id=account_id,
            action=AuditAction.CREATE,
            user_id="user-1",
            new_values={"field": "value"},
        )

        audit_logger.log_account_change(
            account_id=account_id,
            action=AuditAction.UPDATE,
            user_id="user-2",
            old_values={"field": "old"},
            new_values={"field": "new"},
        )

        audit_logger.log_account_change(
            account_id=account_id,
            action=AuditAction.STATUS_CHANGE,
            user_id="user-3",
            old_values={"status": "ACTIVE"},
            new_values={"status": "INACTIVE"},
        )

        db_session.commit()

        # Filter by UPDATE action
        entries = audit_logger.get_audit_trail(
            account_id, action_filter=AuditAction.UPDATE.value
        )

        assert len(entries) == 1
        assert entries[0].action == AuditAction.UPDATE.value
        assert entries[0].user_id == "user-2"

    def test_get_audit_count(self, db_session):
        """Test getting audit entry count"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()

        # Create multiple audit entries
        for i in range(10):
            audit_logger.log_account_change(
                account_id=account_id,
                action=AuditAction.UPDATE,
                user_id=f"user-{i}",
                old_values={"field": f"old-{i}"},
                new_values={"field": f"new-{i}"},
            )

        db_session.commit()

        count = audit_logger.get_audit_count(account_id)
        assert count == 10

    def test_audit_trail_pagination(self, db_session):
        """Test audit trail pagination"""
        audit_logger = AuditLogger(db_session)
        account_id = uuid4()

        # Create 15 audit entries
        for i in range(15):
            audit_logger.log_account_change(
                account_id=account_id,
                action=AuditAction.UPDATE,
                user_id=f"user-{i}",
                old_values={"field": f"old-{i}"},
                new_values={"field": f"new-{i}"},
            )

        db_session.commit()

        # Get first page
        page1 = audit_logger.get_audit_trail(account_id, limit=5, offset=0)
        assert len(page1) == 5

        # Get second page
        page2 = audit_logger.get_audit_trail(account_id, limit=5, offset=5)
        assert len(page2) == 5

        # Get third page
        page3 = audit_logger.get_audit_trail(account_id, limit=5, offset=10)
        assert len(page3) == 5

        # Ensure no overlap
        page1_users = {e.user_id for e in page1}
        page2_users = {e.user_id for e in page2}
        page3_users = {e.user_id for e in page3}

        assert len(page1_users & page2_users) == 0
        assert len(page2_users & page3_users) == 0
        assert len(page1_users & page3_users) == 0
