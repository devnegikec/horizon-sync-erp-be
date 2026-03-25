"""
Unit tests for CreditService.

Tests credit balance checking and atomic deduction with ledger entries.
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import uuid
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi import HTTPException

from app.services.credit_service import CreditService


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return MagicMock()


@pytest.fixture
def credit_service(mock_db):
    """Create a CreditService with a mocked DB session."""
    with patch("app.services.credit_service.CreditRepository") as MockRepo:
        service = CreditService(mock_db)
        service.repo = MockRepo.return_value
        yield service


class TestCheckBalance:
    """Tests for check_balance method."""

    def test_returns_true_when_sufficient(self, credit_service):
        balance = MagicMock()
        balance.balance_credits = 100
        credit_service.repo.get_balance.return_value = balance

        org_id = uuid.uuid4()
        result = credit_service.check_balance(org_id, 50)

        assert result is True
        credit_service.repo.get_balance.assert_called_once_with(org_id)

    def test_returns_true_when_exact_balance(self, credit_service):
        balance = MagicMock()
        balance.balance_credits = 50
        credit_service.repo.get_balance.return_value = balance

        result = credit_service.check_balance(uuid.uuid4(), 50)
        assert result is True

    def test_raises_422_when_no_balance_record(self, credit_service):
        credit_service.repo.get_balance.return_value = None

        with pytest.raises(HTTPException) as exc_info:
            credit_service.check_balance(uuid.uuid4(), 10)

        assert exc_info.value.status_code == 422
        assert "No credit balance configured" in exc_info.value.detail

    def test_raises_422_when_insufficient_credits(self, credit_service):
        balance = MagicMock()
        balance.balance_credits = 5
        credit_service.repo.get_balance.return_value = balance

        with pytest.raises(HTTPException) as exc_info:
            credit_service.check_balance(uuid.uuid4(), 10)

        assert exc_info.value.status_code == 422
        assert "Insufficient credits" in exc_info.value.detail

    def test_raises_422_when_zero_balance(self, credit_service):
        balance = MagicMock()
        balance.balance_credits = 0
        credit_service.repo.get_balance.return_value = balance

        with pytest.raises(HTTPException) as exc_info:
            credit_service.check_balance(uuid.uuid4(), 1)

        assert exc_info.value.status_code == 422


class TestDeductCredits:
    """Tests for deduct_credits method."""

    def test_calls_repo_deduct_and_creates_ledger(self, credit_service, mock_db):
        org_id = uuid.uuid4()
        block_id = uuid.uuid4()
        quantity = 25

        balance_after = MagicMock()
        balance_after.balance_credits = 75
        credit_service.repo.get_balance.return_value = balance_after

        credit_service.deduct_credits(org_id, block_id, quantity)

        credit_service.repo.deduct.assert_called_once_with(org_id, quantity)
        credit_service.repo.create_ledger_entry.assert_called_once_with(
            {
                "organization_id": org_id,
                "block_id": block_id,
                "quantity_deducted": quantity,
                "balance_after": 75,
            }
        )
        mock_db.commit.assert_called_once()

    def test_deduct_propagates_repo_error(self, credit_service):
        credit_service.repo.deduct.side_effect = ValueError("No credit balance configured")

        with pytest.raises(ValueError):
            credit_service.deduct_credits(uuid.uuid4(), uuid.uuid4(), 10)

    def test_ledger_records_correct_balance_after(self, credit_service, mock_db):
        org_id = uuid.uuid4()
        block_id = uuid.uuid4()

        balance_after = MagicMock()
        balance_after.balance_credits = 0
        credit_service.repo.get_balance.return_value = balance_after

        credit_service.deduct_credits(org_id, block_id, 100)

        ledger_data = credit_service.repo.create_ledger_entry.call_args[0][0]
        assert ledger_data["balance_after"] == 0
