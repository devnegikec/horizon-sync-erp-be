"""Unit tests for audit logging in DefaultChartSetupService"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.models.account_audit_log import AccountAuditLog, AuditAction
from app.services.default_chart_setup_service import DefaultChartSetupService


class TestAuditLogging:
    """Test audit logging in DefaultChartSetupService"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        db = MagicMock()
        db.commit = MagicMock()
        db.rollback = MagicMock()
        db.add = MagicMock()
        return db

    @pytest.fixture
    def service(self, mock_db):
        """Create service instance with mocked dependencies"""
        return DefaultChartSetupService(mock_db)

    def test_log_account_creation_creates_audit_entry(self, service, mock_db):
        """Test that _log_account_creation creates an AccountAuditLog entry"""
        # Arrange
        organization_id = uuid.uuid4()
        created_by = "test_user"
        
        # Mock account object
        mock_account = MagicMock()
        mock_account.id = uuid.uuid4()
        mock_account.account_code = "1000"
        mock_account.account_name = "Cash and Bank Accounts"
        mock_account.account_type.value = "ASSET"
        mock_account.currency = "USD"
        mock_account.status.value = "active"

        # Act
        service._log_account_creation(
            account=mock_account,
            created_by=created_by,
            organization_id=organization_id,
        )

        # Assert
        mock_db.add.assert_called_once()
        audit_log = mock_db.add.call_args[0][0]
        
        assert isinstance(audit_log, AccountAuditLog)
        assert audit_log.account_id == mock_account.id
        assert audit_log.action == AuditAction.CREATE.value
        assert audit_log.user_id == created_by
        assert audit_log.changes["account_code"] == "1000"
        assert audit_log.changes["account_name"] == "Cash and Bank Accounts"
        assert audit_log.changes["account_type"] == "ASSET"
        assert audit_log.changes["currency"] == "USD"
        assert audit_log.changes["status"] == "active"
        assert audit_log.changes["source"] == "default_chart_setup"

    def test_log_account_creation_includes_metadata(self, service, mock_db):
        """Test that audit log includes metadata"""
        # Arrange
        organization_id = uuid.uuid4()
        created_by = "test_user"
        
        mock_account = MagicMock()
        mock_account.id = uuid.uuid4()
        mock_account.account_code = "2000"
        mock_account.account_name = "Accounts Payable"
        mock_account.account_type.value = "LIABILITY"
        mock_account.currency = "EUR"
        mock_account.status.value = "active"

        # Act
        service._log_account_creation(
            account=mock_account,
            created_by=created_by,
            organization_id=organization_id,
        )

        # Assert
        audit_log = mock_db.add.call_args[0][0]
        
        assert audit_log.audit_metadata is not None
        assert audit_log.audit_metadata["organization_id"] == str(organization_id)
        assert audit_log.audit_metadata["created_via"] == "default_chart_setup_service"
        assert "timestamp" in audit_log.audit_metadata

    def test_log_account_creation_sets_timestamp(self, service, mock_db):
        """Test that audit log has a timestamp"""
        # Arrange
        organization_id = uuid.uuid4()
        created_by = "test_user"
        
        mock_account = MagicMock()
        mock_account.id = uuid.uuid4()
        mock_account.account_code = "3000"
        mock_account.account_name = "Owner's Equity"
        mock_account.account_type.value = "EQUITY"
        mock_account.currency = "GBP"
        mock_account.status.value = "active"

        # Act
        before_time = datetime.now(UTC)
        service._log_account_creation(
            account=mock_account,
            created_by=created_by,
            organization_id=organization_id,
        )
        after_time = datetime.now(UTC)

        # Assert
        audit_log = mock_db.add.call_args[0][0]
        
        assert audit_log.timestamp is not None
        assert before_time <= audit_log.timestamp <= after_time

    @patch("app.services.default_chart_setup_service.get_default_account_structure")
    def test_create_chart_calls_audit_logging_for_each_account(
        self, mock_get_structure, service, mock_db
    ):
        """Test that audit logging is called for each created account"""
        # Arrange
        organization_id = uuid.uuid4()
        created_by = str(uuid.uuid4())  # Use valid UUID string
        
        # Mock account repository to return False (no existing accounts)
        service.account_repo.check_default_accounts_exist = MagicMock(return_value=False)
        
        # Mock account template with 2 accounts
        mock_template1 = MagicMock()
        mock_template1.account_code = "1000"
        mock_template1.account_name = "Cash"
        mock_template1.account_type.value = "ASSET"
        mock_template1.parent_code = None
        mock_template1.level = 1
        mock_template1.is_posting_account = True
        mock_template1.description = "Cash account"
        
        mock_template2 = MagicMock()
        mock_template2.account_code = "2000"
        mock_template2.account_name = "Payables"
        mock_template2.account_type.value = "LIABILITY"
        mock_template2.parent_code = None
        mock_template2.level = 1
        mock_template2.is_posting_account = True
        mock_template2.description = "Payables account"
        
        mock_get_structure.return_value = [mock_template1, mock_template2]
        
        # Mock chart service to return account objects
        mock_account1 = MagicMock()
        mock_account1.id = uuid.uuid4()
        mock_account1.account_code = "1000"
        mock_account1.account_name = "Cash"
        mock_account1.account_type.value = "ASSET"
        mock_account1.currency = "USD"
        mock_account1.status.value = "active"
        
        mock_account2 = MagicMock()
        mock_account2.id = uuid.uuid4()
        mock_account2.account_code = "2000"
        mock_account2.account_name = "Payables"
        mock_account2.account_type.value = "LIABILITY"
        mock_account2.currency = "USD"
        mock_account2.status.value = "active"
        
        service.chart_service.create = MagicMock(side_effect=[mock_account1, mock_account2])
        
        # Mock default account service
        service.default_account_service.set_default_account = MagicMock()
        service.default_account_service.list_default_accounts = MagicMock(return_value=[])
        
        # Act
        result = service.create_default_chart_of_accounts(
            organization_id=organization_id,
            currency="USD",
            created_by=created_by,
        )

        # Assert
        # db.add should be called for each account's audit log
        # (2 accounts = 2 audit log entries)
        assert mock_db.add.call_count >= 2
        
        # Verify audit logs were created for both accounts
        audit_log_calls = [call[0][0] for call in mock_db.add.call_args_list if isinstance(call[0][0], AccountAuditLog)]
        assert len(audit_log_calls) == 2
        
        # Verify the audit logs have correct account IDs
        audit_account_ids = {log.account_id for log in audit_log_calls}
        assert mock_account1.id in audit_account_ids
        assert mock_account2.id in audit_account_ids
