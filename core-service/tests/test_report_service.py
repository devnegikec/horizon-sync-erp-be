"""Tests for ReportService"""

from datetime import date
from uuid import uuid4

from app.services.report_service import ReportService


def test_report_service_initialization(db_session):
    """Test that ReportService can be initialized"""
    service = ReportService(db_session)
    assert service is not None
    assert service.db == db_session


def test_generate_chart_of_accounts_report_empty(db_session):
    """Test generating chart of accounts report with no accounts"""
    service = ReportService(db_session)
    organization_id = uuid4()

    report = service.generate_chart_of_accounts_report(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert report is not None
    assert report["report_type"] == "chart_of_accounts"
    assert report["total_accounts"] == 0
    assert report["accounts"] == []


def test_generate_hierarchical_report_empty(db_session):
    """Test generating hierarchical report with no accounts"""
    service = ReportService(db_session)
    organization_id = uuid4()

    report = service.generate_hierarchical_report(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert report is not None
    assert report["report_type"] == "hierarchical"
    assert report["total_accounts"] == 0
    assert report["tree"] == []


def test_generate_trial_balance_empty(db_session):
    """Test generating trial balance with no accounts"""
    service = ReportService(db_session)
    organization_id = uuid4()

    report = service.generate_trial_balance(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert report is not None
    assert report["report_type"] == "trial_balance"
    assert report["total_accounts"] == 0
    assert report["accounts"] == []
    assert report["total_debits"] == 0.0
    assert report["total_credits"] == 0.0
    assert report["difference"] == 0.0
    assert report["is_balanced"] is True


def test_generate_financial_statement_grouped_empty(db_session):
    """Test generating financial statement grouped report with no accounts"""
    service = ReportService(db_session)
    organization_id = uuid4()

    report = service.generate_financial_statement_grouped(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert report is not None
    assert report["report_type"] == "financial_statement_grouped"
    assert report["total_accounts"] == 0
    assert report["groups"] == []


def test_generate_financial_statement_grouped_with_accounts(
    db_session, sample_accounts
):
    """Test generating financial statement grouped report with accounts"""
    from unittest.mock import patch

    service = ReportService(db_session)
    organization_id = sample_accounts[0].organization_id

    # Mock balance calculator to return zero balances quickly
    mock_balance = {
        "balance": 0.0,
        "base_currency_balance": 0.0,
        "debit_total": 0.0,
        "credit_total": 0.0,
    }

    with patch.object(
        service.balance_calculator, "calculate_balance", return_value=mock_balance
    ):
        report = service.generate_financial_statement_grouped(
            organization_id=organization_id, as_of_date=date.today()
        )

    assert report is not None
    assert report["report_type"] == "financial_statement_grouped"
    assert report["total_accounts"] == len(sample_accounts)

    # Verify accounts are grouped by type
    account_types_in_report = [group["account_type"] for group in report["groups"]]

    # Check that we have all 5 account types represented (using lowercase values from enum)
    assert "asset" in account_types_in_report
    assert "liability" in account_types_in_report
    assert "equity" in account_types_in_report
    assert "income" in account_types_in_report  # REVENUE maps to "income"
    assert "expense" in account_types_in_report

    # Check that each group has the correct type
    for group in report["groups"]:
        assert group["account_type"] in [
            "asset",
            "liability",
            "equity",
            "income",
            "expense",
        ]
        assert group["count"] == len(group["accounts"])

        # Verify all accounts in the group have the same type
        for account in group["accounts"]:
            assert account["account_type"] == group["account_type"]

        # Verify accounts are sorted by account_code within each group
        account_codes = [acc["account_code"] for acc in group["accounts"]]
        assert account_codes == sorted(account_codes)
