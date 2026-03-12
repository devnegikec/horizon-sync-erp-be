"""Unit tests for hierarchical account creation in DefaultChartSetupService"""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.models.base import AccountType
from app.services.default_account_template import AccountTemplate
from app.services.default_chart_setup_service import DefaultChartSetupService


class TestHierarchicalAccountCreation:
    """Test hierarchical account creation in DefaultChartSetupService"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create DefaultChartSetupService with mocked dependencies"""
        service = DefaultChartSetupService(mock_db_session)
        
        # Mock the repository methods
        service.account_repo.check_default_accounts_exist = MagicMock(return_value=False)
        service.account_repo.get_accounts_by_codes = MagicMock(return_value={})
        
        return service

    @pytest.fixture
    def hierarchical_templates(self):
        """Create a set of hierarchical account templates for testing"""
        return [
            # Parent account (level 1)
            AccountTemplate(
                account_code="1000",
                account_name="Cash and Bank Accounts",
                account_type=AccountType.ASSET,
                is_group=True,
                is_posting_account=False,
                level=1,
            ),
            # Child accounts (level 2)
            AccountTemplate(
                account_code="1010",
                account_name="Cash",
                account_type=AccountType.ASSET,
                parent_code="1000",
                level=2,
            ),
            AccountTemplate(
                account_code="1020",
                account_name="Bank Accounts",
                account_type=AccountType.ASSET,
                parent_code="1000",
                level=2,
            ),
            # Another parent (level 1)
            AccountTemplate(
                account_code="5100",
                account_name="Operating Expenses",
                account_type=AccountType.EXPENSE,
                is_group=True,
                is_posting_account=False,
                level=1,
            ),
            # Child of second parent (level 2)
            AccountTemplate(
                account_code="5110",
                account_name="Office Supplies",
                account_type=AccountType.EXPENSE,
                parent_code="5100",
                level=2,
            ),
        ]

    def test_templates_sorted_by_level(self, service, hierarchical_templates):
        """Test that account templates are sorted by level to ensure parents created first"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Create a mock account object that will be returned by chart_service.create
        def create_mock_account(data, organization_id, user_id):
            mock_account = MagicMock()
            mock_account.id = uuid.uuid4()
            mock_account.account_code = data.account_code
            mock_account.account_name = data.account_name
            mock_account.account_type = AccountType(data.account_type)
            return mock_account
        
        service.chart_service.create = MagicMock(side_effect=create_mock_account)
        service.default_account_service.set_default_account = MagicMock()
        
        # Shuffle templates to test sorting (put level 2 before level 1)
        shuffled_templates = [
            hierarchical_templates[1],  # level 2
            hierarchical_templates[0],  # level 1
            hierarchical_templates[3],  # level 1
            hierarchical_templates[2],  # level 2
            hierarchical_templates[4],  # level 2
        ]
        
        with patch(
            'app.services.default_chart_setup_service.get_default_account_structure',
            return_value=shuffled_templates
        ):
            result = service.create_default_chart_of_accounts(
                organization_id=organization_id,
                currency="USD",
                created_by=str(user_id)
            )
        
        # Verify accounts were created
        assert len(result.accounts) == 5
        
        # Verify chart_service.create was called 5 times
        assert service.chart_service.create.call_count == 5
        
        # Verify the order: level 1 accounts should be created before level 2
        calls = service.chart_service.create.call_args_list
        
        # First two calls should be level 1 accounts (1000 and 5100)
        first_call_code = calls[0][1]['data'].account_code
        second_call_code = calls[1][1]['data'].account_code
        assert first_call_code in ["1000", "5100"]
        assert second_call_code in ["1000", "5100"]
        assert first_call_code != second_call_code
        
        # Last three calls should be level 2 accounts (1010, 1020, 5110)
        third_call_code = calls[2][1]['data'].account_code
        fourth_call_code = calls[3][1]['data'].account_code
        fifth_call_code = calls[4][1]['data'].account_code
        assert third_call_code in ["1010", "1020", "5110"]
        assert fourth_call_code in ["1010", "1020", "5110"]
        assert fifth_call_code in ["1010", "1020", "5110"]

    def test_parent_account_id_passed_for_child_accounts(self, service, hierarchical_templates):
        """Test that parent_account_id is passed when creating child accounts"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        parent_account_id = uuid.uuid4()
        
        # Track created accounts
        created_accounts = {}
        
        def create_mock_account(data, organization_id, user_id):
            mock_account = MagicMock()
            mock_account.id = uuid.uuid4()
            mock_account.account_code = data.account_code
            mock_account.account_name = data.account_name
            mock_account.account_type = AccountType(data.account_type)
            
            # Store parent account with specific ID for testing
            if data.account_code == "1000":
                mock_account.id = parent_account_id
            
            created_accounts[data.account_code] = mock_account
            return mock_account
        
        service.chart_service.create = MagicMock(side_effect=create_mock_account)
        service.default_account_service.set_default_account = MagicMock()
        
        with patch(
            'app.services.default_chart_setup_service.get_default_account_structure',
            return_value=hierarchical_templates
        ):
            result = service.create_default_chart_of_accounts(
                organization_id=organization_id,
                currency="USD",
                created_by=str(user_id)
            )
        
        # Verify accounts were created
        assert len(result.accounts) == 5
        
        # Find the calls for child accounts (1010 and 1020)
        calls = service.chart_service.create.call_args_list
        
        # Check that child accounts have parent_account_id set
        for call in calls:
            data = call[1]['data']
            if data.account_code in ["1010", "1020"]:
                # These are children of 1000
                assert data.parent_account_id == parent_account_id
            elif data.account_code == "5110":
                # This is a child of 5100
                assert data.parent_account_id is not None
            else:
                # Parent accounts should have None
                assert data.parent_account_id is None

    def test_parent_exists_validation(self, service):
        """Test that parent account must exist before creating child"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Create templates where child references non-existent parent
        invalid_templates = [
            AccountTemplate(
                account_code="1010",
                account_name="Cash",
                account_type=AccountType.ASSET,
                parent_code="9999",  # Non-existent parent
                level=2,
            ),
        ]
        
        service.chart_service.create = MagicMock()
        service.default_account_service.set_default_account = MagicMock()
        
        with patch(
            'app.services.default_chart_setup_service.get_default_account_structure',
            return_value=invalid_templates
        ):
            # Should raise ValueError when parent not found
            with pytest.raises(ValueError, match="Parent account 9999 not found"):
                service.create_default_chart_of_accounts(
                    organization_id=organization_id,
                    currency="USD",
                    created_by=str(user_id)
                )
        
        # Verify rollback was called
        service.db.rollback.assert_called_once()

    def test_created_accounts_tracked_by_code(self, service, hierarchical_templates):
        """Test that created accounts are tracked by code for parent reference lookup"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Track the accounts that were looked up for parent references
        parent_lookups = []
        
        def create_mock_account(data, organization_id, user_id):
            mock_account = MagicMock()
            mock_account.id = uuid.uuid4()
            mock_account.account_code = data.account_code
            mock_account.account_name = data.account_name
            mock_account.account_type = AccountType(data.account_type)
            
            # Track when parent_account_id is set (means parent was looked up)
            if data.parent_account_id is not None:
                parent_lookups.append(data.account_code)
            
            return mock_account
        
        service.chart_service.create = MagicMock(side_effect=create_mock_account)
        service.default_account_service.set_default_account = MagicMock()
        
        with patch(
            'app.services.default_chart_setup_service.get_default_account_structure',
            return_value=hierarchical_templates
        ):
            result = service.create_default_chart_of_accounts(
                organization_id=organization_id,
                currency="USD",
                created_by=str(user_id)
            )
        
        # Verify that child accounts were created with parent references
        # (which means parents were successfully tracked and looked up)
        assert "1010" in parent_lookups  # Child of 1000
        assert "1020" in parent_lookups  # Child of 1000
        assert "5110" in parent_lookups  # Child of 5100
        
        # Verify all accounts were created
        assert len(result.accounts) == 5

    def test_hierarchical_creation_with_real_template(self, service):
        """Test hierarchical creation using the actual default account structure"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Track parent-child relationships
        created_accounts = {}
        parent_child_relationships = []
        
        def create_mock_account(data, organization_id, user_id):
            mock_account = MagicMock()
            mock_account.id = uuid.uuid4()
            mock_account.account_code = data.account_code
            mock_account.account_name = data.account_name
            mock_account.account_type = AccountType(data.account_type)
            
            created_accounts[data.account_code] = mock_account
            
            # Track parent-child relationships
            if data.parent_account_id is not None:
                # Find parent code
                parent_code = None
                for code, acc in created_accounts.items():
                    if acc.id == data.parent_account_id:
                        parent_code = code
                        break
                
                if parent_code:
                    parent_child_relationships.append({
                        'parent': parent_code,
                        'child': data.account_code
                    })
            
            return mock_account
        
        service.chart_service.create = MagicMock(side_effect=create_mock_account)
        service.default_account_service.set_default_account = MagicMock()
        
        # Use the real template (not mocked)
        result = service.create_default_chart_of_accounts(
            organization_id=organization_id,
            currency="USD",
            created_by=str(user_id)
        )
        
        # Verify accounts were created
        assert len(result.accounts) > 0
        
        # Verify some expected parent-child relationships exist
        # (based on the default template structure)
        expected_relationships = [
            {'parent': '1000', 'child': '1010'},  # Cash and Bank -> Cash
            {'parent': '1000', 'child': '1020'},  # Cash and Bank -> Bank Accounts
            {'parent': '1500', 'child': '1510'},  # Property -> Land and Buildings
            {'parent': '5100', 'child': '5110'},  # Operating Expenses -> Office Supplies
        ]
        
        for expected in expected_relationships:
            assert expected in parent_child_relationships, \
                f"Expected relationship {expected} not found in {parent_child_relationships}"

    def test_error_logged_when_parent_not_found(self, service, caplog):
        """Test that error is logged when parent account is not found"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        # Create templates where child references non-existent parent
        invalid_templates = [
            AccountTemplate(
                account_code="1010",
                account_name="Cash",
                account_type=AccountType.ASSET,
                parent_code="9999",  # Non-existent parent
                level=2,
            ),
        ]
        
        service.chart_service.create = MagicMock()
        service.default_account_service.set_default_account = MagicMock()
        
        with patch(
            'app.services.default_chart_setup_service.get_default_account_structure',
            return_value=invalid_templates
        ):
            with pytest.raises(ValueError):
                service.create_default_chart_of_accounts(
                    organization_id=organization_id,
                    currency="USD",
                    created_by=str(user_id)
                )
        
        # Verify error was logged
        assert "Parent account 9999 not found for account 1010" in caplog.text
