"""Tests for ReportService"""

import pytest
from datetime import date
from uuid import uuid4

from app.services.report_service import ReportService
from app.models.base import AccountType, AccountStatus


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
        organization_id=organization_id,
        as_of_date=date.today()
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
        organization_id=organization_id,
        as_of_date=date.today()
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
        organization_id=organization_id,
        as_of_date=date.today()
    )
    
    assert report is not None
    assert report["report_type"] == "trial_balance"
    assert report["total_accounts"] == 0
    assert report["accounts"] == []
    assert report["total_debits"] == 0.0
    assert report["total_credits"] == 0.0
    assert report["difference"] == 0.0
    assert report["is_balanced"] is True
