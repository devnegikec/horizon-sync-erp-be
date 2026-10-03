"""
Unit tests for CreditService.

Tests credit balance checking and atomic deduction with ledger entries.
Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
        service.repo.get_consumption_by_block.return_value = None
        service.repo.get_ledger_by_reference.return_value = None
        service.repo.get_reservation_by_block.return_value = None
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
        credit_service.repo.deduct.return_value = balance_after

        credit_service.deduct_credits(org_id, block_id, quantity)

        credit_service.repo.deduct.assert_called_once_with(org_id, quantity)
        credit_service.repo.create_ledger_entry.assert_called_once_with(
            {
                "organization_id": org_id,
                "block_id": block_id,
                "transaction_type": "block_consumption",
                "amount": -quantity,
                "balance_after": 75,
                "reason": "QR Block generation",
                "created_by": None,
                "reference_id": None,
            }
        )
        mock_db.commit.assert_called_once()

    def test_deduct_propagates_repo_error(self, credit_service):
        credit_service.repo.deduct.side_effect = ValueError(
            "No credit balance configured"
        )

        with pytest.raises(HTTPException) as exc_info:
            credit_service.deduct_credits(uuid.uuid4(), uuid.uuid4(), 10)
        assert exc_info.value.status_code == 422

    def test_ledger_records_correct_balance_after(self, credit_service, mock_db):
        org_id = uuid.uuid4()
        block_id = uuid.uuid4()

        balance_after = MagicMock()
        balance_after.balance_credits = 0
        credit_service.repo.deduct.return_value = balance_after

        credit_service.deduct_credits(org_id, block_id, 100)

        ledger_data = credit_service.repo.create_ledger_entry.call_args[0][0]
        assert ledger_data["balance_after"] == 0

    def test_same_block_is_not_consumed_twice(self, credit_service, mock_db):
        credit_service.repo.get_consumption_by_block.return_value = MagicMock()

        credit_service.deduct_credits(uuid.uuid4(), uuid.uuid4(), 10)

        credit_service.repo.deduct.assert_not_called()
        credit_service.repo.create_ledger_entry.assert_not_called()
        mock_db.commit.assert_not_called()


class TestAddCredits:
    def test_adds_balance_and_records_admin_audit(self, credit_service, mock_db):
        org_id = uuid.uuid4()
        user_id = uuid.uuid4()
        reference_id = uuid.uuid4()
        balance = MagicMock(balance_credits=250)
        credit_service.repo.add.return_value = balance

        result = credit_service.add_credits(
            org_id, 250, "Purchased credit pack", reference_id, user_id
        )

        assert result is balance
        credit_service.repo.add.assert_called_once_with(org_id, 250)
        credit_service.repo.create_ledger_entry.assert_called_once_with(
            {
                "organization_id": org_id,
                "block_id": None,
                "transaction_type": "credit_addition",
                "amount": 250,
                "balance_after": 250,
                "reason": "Purchased credit pack",
                "created_by": user_id,
                "reference_id": reference_id,
            }
        )
        mock_db.commit.assert_called_once()

    def test_repeated_reference_is_idempotent(self, credit_service, mock_db):
        org_id = uuid.uuid4()
        reference_id = uuid.uuid4()
        credit_service.repo.get_ledger_by_reference.return_value = MagicMock(
            transaction_type="credit_addition",
            amount=100,
        )
        balance = MagicMock()
        credit_service.repo.get_balance.return_value = balance

        result = credit_service.add_credits(
            org_id, 100, "Initial allocation", reference_id, uuid.uuid4()
        )

        assert result is balance
        credit_service.repo.add.assert_not_called()
        mock_db.commit.assert_not_called()


class TestCreditReservations:
    def test_reserve_moves_available_credits_to_reserved(
        self,
        credit_service,
        mock_db,
    ):
        organization_id = uuid.uuid4()
        block_id = uuid.uuid4()
        balance = SimpleNamespace(balance_credits=100, reserved_credits=0)
        reservation = SimpleNamespace(quantity=25, status="reserved")
        credit_service.repo.get_balance_for_update.return_value = balance
        credit_service.repo.create_reservation.return_value = reservation

        result = credit_service.reserve_credits(
            organization_id,
            block_id,
            25,
        )

        assert result is reservation
        assert balance.balance_credits == 75
        assert balance.reserved_credits == 25
        credit_service.repo.create_reservation.assert_called_once_with(
            organization_id,
            block_id,
            25,
        )
        mock_db.commit.assert_called_once()

    def test_consume_reserved_credits_is_idempotent_and_audited(
        self,
        credit_service,
        mock_db,
    ):
        organization_id = uuid.uuid4()
        block_id = uuid.uuid4()
        reservation = SimpleNamespace(
            quantity=10,
            status="reserved",
            resolved_at=None,
        )
        balance = SimpleNamespace(
            balance_credits=90,
            reserved_credits=10,
            used_credits=0,
        )
        credit_service.repo.get_reservation_by_block.return_value = reservation
        credit_service.repo.get_balance_for_update.return_value = balance

        credit_service.consume_reserved_credits(
            organization_id,
            block_id,
        )

        assert reservation.status == "consumed"
        assert balance.reserved_credits == 0
        assert balance.used_credits == 10
        credit_service.repo.create_ledger_entry.assert_called_once()
        assert (
            credit_service.repo.create_ledger_entry.call_args.args[0]["amount"]
            == -10
        )
        mock_db.commit.assert_called_once()

    def test_release_returns_reserved_credits_to_available(
        self,
        credit_service,
        mock_db,
    ):
        organization_id = uuid.uuid4()
        block_id = uuid.uuid4()
        reservation = SimpleNamespace(
            quantity=40,
            status="reserved",
            resolved_at=None,
        )
        balance = SimpleNamespace(balance_credits=60, reserved_credits=40)
        credit_service.repo.get_reservation_by_block.return_value = reservation
        credit_service.repo.get_balance_for_update.return_value = balance

        credit_service.release_reserved_credits(organization_id, block_id)

        assert reservation.status == "released"
        assert balance.balance_credits == 100
        assert balance.reserved_credits == 0
        mock_db.commit.assert_called_once()
