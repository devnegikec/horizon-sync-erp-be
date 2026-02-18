import uuid

import pytest
from app.core.exceptions import (
    ChartOfAccountNotFoundException,
    CircularReferenceException,
    DuplicateAccountCodeException,
    ValidationError,
)
from app.models.base import AccountType
from app.schemas.chart_of_account import ChartOfAccountCreate, ChartOfAccountUpdate
from app.services.chart_of_account_service import ChartOfAccountService


@pytest.fixture
def account_service(db_session):
    """Create an account service instance"""
    return ChartOfAccountService(db_session)


@pytest.fixture
def organization_id():
    """Create a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Create a test user ID"""
    return uuid.uuid4()


@pytest.fixture
def valid_account_data(organization_id):
    """Create valid account data for testing"""
    return ChartOfAccountCreate(
        account_code="1000",
        account_name="Cash",
        account_type="asset",
    )


class TestRequiredFieldValidation:
    """Test required field validation (Requirements 11.1, 11.2)"""

    def test_empty_account_code_rejected(self, account_service, organization_id, user_id):
        """Test that empty account code is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="",
                account_name="Test Account",
                account_type="asset",
            )

    def test_whitespace_only_account_code_rejected(self, account_service, organization_id, user_id):
        """Test that whitespace-only account code is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="   ",
                account_name="Test Account",
                account_type="asset",
            )

    def test_empty_account_name_rejected(self, account_service, organization_id, user_id):
        """Test that empty account name is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="1000",
                account_name="",
                account_type="asset",
            )

    def test_whitespace_only_account_name_rejected(self, account_service, organization_id, user_id):
        """Test that whitespace-only account name is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="1000",
                account_name="   ",
                account_type="asset",
            )

    def test_empty_account_type_rejected(self, account_service, organization_id, user_id):
        """Test that empty account type is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="1000",
                account_name="Test Account",
                account_type="",
            )


class TestFieldLengthValidation:
    """Test field length validation (Requirements 11.1, 11.2)"""

    def test_account_code_exceeds_50_chars_rejected(self, account_service, organization_id, user_id):
        """Test that account code exceeding 50 characters is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="A" * 51,  # 51 characters
                account_name="Test Account",
                account_type="asset",
            )

    def test_account_code_exactly_50_chars_accepted(self, account_service, organization_id, user_id):
        """Test that account code with exactly 50 characters is accepted"""
        data = ChartOfAccountCreate(
            account_code="A" * 50,  # Exactly 50 characters
            account_name="Test Account",
            account_type="asset",
        )

        # Should not raise ValidationError for length
        account = account_service.create(data, organization_id, user_id)
        assert account.account_code == "A" * 50

    def test_account_name_exceeds_200_chars_rejected(self, account_service, organization_id, user_id):
        """Test that account name exceeding 200 characters is rejected by Pydantic validation"""
        from pydantic import ValidationError as PydanticValidationError
        
        with pytest.raises(PydanticValidationError):
            ChartOfAccountCreate(
                account_code="1000",
                account_name="A" * 201,  # 201 characters
                account_type="asset",
            )

    def test_account_name_exactly_200_chars_accepted(self, account_service, organization_id, user_id):
        """Test that account name with exactly 200 characters is accepted"""
        data = ChartOfAccountCreate(
            account_code="1000",
            account_name="A" * 200,  # Exactly 200 characters
            account_type="asset",
        )

        # Should not raise ValidationError for length
        account = account_service.create(data, organization_id, user_id)
        assert account.account_name == "A" * 200

    def test_update_account_name_exceeds_200_chars_rejected(
        self, account_service, organization_id, user_id, valid_account_data
    ):
        """Test that updating account name to exceed 200 characters is rejected"""
        # Create account first
        account = account_service.create(valid_account_data, organization_id, user_id)

        # Try to update with name exceeding 200 chars
        with pytest.raises(ValidationError):
            update_data = ChartOfAccountUpdate(account_name="B" * 201)
            account_service.update(account.id, update_data, organization_id, user_id)

    def test_update_account_name_empty_rejected(
        self, account_service, organization_id, user_id, valid_account_data
    ):
        """Test that updating account name to empty string is rejected"""
        # Create account first
        account = account_service.create(valid_account_data, organization_id, user_id)

        # Try to update with empty name
        update_data = ChartOfAccountUpdate(account_name="   ")

        with pytest.raises(ValidationError) as exc_info:
            account_service.update(account.id, update_data, organization_id, user_id)

        assert "cannot be empty" in str(exc_info.value)


class TestAccountCodeFormatValidation:
    """Test account code format validation (Requirements 1.6, 6.1, 6.2)"""

    def test_default_pattern_accepts_alphanumeric_and_dash(self, db_session, organization_id, user_id):
        """Test that default pattern accepts alphanumeric characters and dashes"""
        service = ChartOfAccountService(db_session)

        valid_codes = ["1000", "ABC-123", "Asset-001", "1000-01-02"]

        for code in valid_codes:
            data = ChartOfAccountCreate(
                account_code=code,
                account_name="Test Account",
                account_type="asset",
            )
            account = service.create(data, organization_id, user_id)
            assert account.account_code == code

    def test_default_pattern_rejects_special_chars(self, db_session, organization_id, user_id):
        """Test that default pattern rejects special characters"""
        service = ChartOfAccountService(db_session)

        invalid_codes = ["1000@", "ABC#123", "Asset_001", "1000.01", "1000/01"]

        for code in invalid_codes:
            data = ChartOfAccountCreate(
                account_code=code,
                account_name="Test Account",
                account_type="asset",
            )

            with pytest.raises(ValidationError) as exc_info:
                service.create(data, organization_id, user_id)

            assert "does not match the required format pattern" in str(exc_info.value)

    def test_custom_pattern_validation(self, db_session, organization_id, user_id):
        """Test that custom regex pattern is enforced"""
        # Custom pattern: 4 digits, dash, 2 digits (e.g., "1000-01")
        custom_pattern = r"^\d{4}-\d{2}$"
        service = ChartOfAccountService(db_session, account_code_pattern=custom_pattern)

        # Valid code matching custom pattern
        valid_data = ChartOfAccountCreate(
            account_code="1000-01",
            account_name="Test Account",
            account_type="asset",
        )
        account = service.create(valid_data, organization_id, user_id)
        assert account.account_code == "1000-01"

        # Invalid code not matching custom pattern
        invalid_data = ChartOfAccountCreate(
            account_code="ABC-123",
            account_name="Test Account 2",
            account_type="asset",
        )

        with pytest.raises(ValidationError) as exc_info:
            service.create(invalid_data, organization_id, user_id)

        assert "does not match the required format pattern" in str(exc_info.value)
        assert custom_pattern in str(exc_info.value)


class TestDuplicateCodeDetection:
    """Test duplicate account code detection (Requirement 1.2)"""

    def test_duplicate_account_code_rejected(
        self, account_service, organization_id, user_id, valid_account_data
    ):
        """Test that duplicate account code is rejected"""
        # Create first account
        account_service.create(valid_account_data, organization_id, user_id)

        # Try to create another account with same code
        duplicate_data = ChartOfAccountCreate(
            account_code=valid_account_data.account_code,
            account_name="Different Name",
            account_type="asset",
        )

        with pytest.raises(DuplicateAccountCodeException) as exc_info:
            account_service.create(duplicate_data, organization_id, user_id)

        assert valid_account_data.account_code in str(exc_info.value)
        assert "already exists" in str(exc_info.value)

    def test_same_code_different_organization_allowed(
        self, account_service, user_id, valid_account_data
    ):
        """Test that same account code is allowed in different organizations"""
        org1_id = uuid.uuid4()
        org2_id = uuid.uuid4()

        # Create account in first organization
        valid_data_org1 = ChartOfAccountCreate(
            account_code=valid_account_data.account_code,
            account_name=valid_account_data.account_name,
            account_type=valid_account_data.account_type,
        )
        account1 = account_service.create(valid_data_org1, org1_id, user_id)

        # Create account with same code in second organization (should succeed)
        valid_data_org2 = ChartOfAccountCreate(
            account_code=valid_account_data.account_code,
            account_name=valid_account_data.account_name,
            account_type=valid_account_data.account_type,
        )
        account2 = account_service.create(valid_data_org2, org2_id, user_id)

        assert account1.account_code == account2.account_code
        assert account1.organization_id != account2.organization_id


class TestParentAccountValidation:
    """Test parent account validation"""

    def test_nonexistent_parent_rejected(
        self, account_service, organization_id, user_id
    ):
        """Test that nonexistent parent account is rejected"""
        fake_parent_id = uuid.uuid4()

        data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Child Account",
            account_type="asset",
            parent_account_id=fake_parent_id,
        )

        with pytest.raises(ChartOfAccountNotFoundException) as exc_info:
            account_service.create(data, organization_id, user_id)

        assert str(fake_parent_id) in str(exc_info.value)
        assert "not found" in str(exc_info.value)

    def test_circular_reference_rejected(
        self, account_service, organization_id, user_id, valid_account_data
    ):
        """Test that circular reference is rejected"""
        # Create parent account
        parent = account_service.create(valid_account_data, organization_id, user_id)

        # Try to update parent to have itself as parent
        update_data = ChartOfAccountUpdate(parent_account_id=parent.id)

        with pytest.raises(CircularReferenceException) as exc_info:
            account_service.update(parent.id, update_data, organization_id, user_id)

        assert "cannot be its own parent" in str(exc_info.value)

    def test_inactive_parent_rejected_on_create(
        self, account_service, organization_id, user_id
    ):
        """Test that inactive parent account is rejected when creating child (Requirement 11.3)"""
        # Create parent account
        parent_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Parent Account",
            account_type="asset",
        )
        parent = account_service.create(parent_data, organization_id, user_id)

        # Deactivate parent
        account_service.deactivate_account(parent.id, organization_id, user_id)

        # Try to create child with inactive parent
        child_data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Child Account",
            account_type="asset",
            parent_account_id=parent.id,
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.create(child_data, organization_id, user_id)

        assert "must be active" in str(exc_info.value).lower()
        assert parent.account_code in str(exc_info.value)

    def test_inactive_parent_rejected_on_update(
        self, account_service, organization_id, user_id
    ):
        """Test that inactive parent account is rejected when updating child (Requirement 11.3)"""
        # Create parent account
        parent_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Parent Account",
            account_type="asset",
        )
        parent = account_service.create(parent_data, organization_id, user_id)

        # Create child account without parent
        child_data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Child Account",
            account_type="asset",
        )
        child = account_service.create(child_data, organization_id, user_id)

        # Deactivate parent
        account_service.deactivate_account(parent.id, organization_id, user_id)

        # Try to update child to have inactive parent
        update_data = ChartOfAccountUpdate(parent_account_id=parent.id)

        with pytest.raises(ValidationError) as exc_info:
            account_service.update(child.id, update_data, organization_id, user_id)

        assert "must be active" in str(exc_info.value).lower()
        assert parent.account_code in str(exc_info.value)

    def test_archived_parent_rejected_on_create(
        self, account_service, organization_id, user_id
    ):
        """Test that archived parent account is rejected when creating child (Requirement 11.3)"""
        # Create parent account
        parent_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Parent Account",
            account_type="asset",
        )
        parent = account_service.create(parent_data, organization_id, user_id)

        # Archive parent
        account_service.archive_account(parent.id, organization_id, user_id)

        # Try to create child with archived parent
        child_data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Child Account",
            account_type="asset",
            parent_account_id=parent.id,
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.create(child_data, organization_id, user_id)

        assert "must be active" in str(exc_info.value).lower()
        assert parent.account_code in str(exc_info.value)

    def test_active_parent_accepted(
        self, account_service, organization_id, user_id
    ):
        """Test that active parent account is accepted (Requirement 11.3)"""
        # Create parent account
        parent_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Parent Account",
            account_type="asset",
        )
        parent = account_service.create(parent_data, organization_id, user_id)

        # Create child with active parent (should succeed)
        child_data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Child Account",
            account_type="asset",
            parent_account_id=parent.id,
        )
        child = account_service.create(child_data, organization_id, user_id)

        assert child.parent_account_id == parent.id
        assert child.account_code == "1100"


class TestValidAccountCreation:
    """Test successful account creation with valid data"""

    def test_create_account_with_all_validations_passing(
        self, account_service, organization_id, user_id
    ):
        """Test that account is created when all validations pass"""
        data = ChartOfAccountCreate(
            account_code="1000-01",
            account_name="Cash in Hand",
            account_type="asset",
        )

        account = account_service.create(data, organization_id, user_id)

        assert account.account_code == "1000-01"
        assert account.account_name == "Cash in Hand"
        assert account.account_type == AccountType.ASSET
        assert account.organization_id == organization_id
        assert account.created_by == str(user_id)
        assert account.updated_by == str(user_id)

    def test_create_account_with_parent(
        self, account_service, organization_id, user_id, valid_account_data
    ):
        """Test creating account with valid parent"""
        # Create parent account
        parent = account_service.create(valid_account_data, organization_id, user_id)

        # Create child account
        child_data = ChartOfAccountCreate(
            account_code="1100",
            account_name="Bank Accounts",
            account_type="asset",
            parent_account_id=parent.id,
        )

        child = account_service.create(child_data, organization_id, user_id)

        assert child.parent_account_id == parent.id
        assert child.account_code == "1100"



class TestAccountTypeImmutability:
    """Test account type immutability when transactions exist (Requirement 11.6)"""

    def test_account_type_change_without_transactions_allowed(
        self, account_service, organization_id, user_id
    ):
        """Test that account type can be changed when no transactions exist"""
        # Create an account
        account_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        account = account_service.create(
            data=account_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Update account type (should succeed since no transactions exist)
        update_data = ChartOfAccountUpdate(
            account_type="expense",
        )
        updated_account = account_service.update(
            account_id=account.id,
            data=update_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        assert updated_account.account_type == AccountType.EXPENSE

    def test_account_type_change_with_transactions_rejected(
        self, account_service, organization_id, user_id, monkeypatch
    ):
        """Test that account type cannot be changed when transactions exist"""
        # Create an account
        account_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        account = account_service.create(
            data=account_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Mock the _has_transactions method to return True
        def mock_has_transactions(self, account_id, org_id):
            return True

        monkeypatch.setattr(
            ChartOfAccountService,
            "_has_transactions",
            mock_has_transactions,
        )

        # Attempt to update account type (should fail)
        update_data = ChartOfAccountUpdate(
            account_type="expense",
        )

        with pytest.raises(ValidationError) as exc_info:
            account_service.update(
                account_id=account.id,
                data=update_data,
                organization_id=organization_id,
                user_id=user_id,
            )

        assert "Cannot change account type" in str(exc_info.value)
        assert "existing transactions" in str(exc_info.value)
        assert "immutable" in str(exc_info.value)

    def test_account_type_unchanged_with_transactions_allowed(
        self, account_service, organization_id, user_id, monkeypatch
    ):
        """Test that updating other fields is allowed even when transactions exist"""
        # Create an account
        account_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        account = account_service.create(
            data=account_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Mock the _has_transactions method to return True
        def mock_has_transactions(self, account_id, org_id):
            return True

        monkeypatch.setattr(
            ChartOfAccountService,
            "_has_transactions",
            mock_has_transactions,
        )

        # Update account name (should succeed even with transactions)
        update_data = ChartOfAccountUpdate(
            account_name="Updated Cash Account",
        )
        updated_account = account_service.update(
            account_id=account.id,
            data=update_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        assert updated_account.account_name == "Updated Cash Account"
        assert updated_account.account_type == AccountType.ASSET  # Type unchanged

    def test_account_type_same_value_with_transactions_allowed(
        self, account_service, organization_id, user_id, monkeypatch
    ):
        """Test that setting account type to the same value is allowed even with transactions"""
        # Create an account
        account_data = ChartOfAccountCreate(
            account_code="1000",
            account_name="Cash",
            account_type="asset",
        )
        account = account_service.create(
            data=account_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Mock the _has_transactions method to return True
        def mock_has_transactions(self, account_id, org_id):
            return True

        monkeypatch.setattr(
            ChartOfAccountService,
            "_has_transactions",
            mock_has_transactions,
        )

        # Update with same account type (should succeed)
        update_data = ChartOfAccountUpdate(
            account_type="asset",
        )
        updated_account = account_service.update(
            account_id=account.id,
            data=update_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        assert updated_account.account_type == AccountType.ASSET
