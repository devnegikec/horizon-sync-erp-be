"""Tests for ExportService"""

from datetime import date
from uuid import uuid4

from app.services.export_service import ExportService
from app.services.report_service import ReportService


def test_export_service_initialization(db_session):
    """Test that ExportService can be initialized"""
    report_service = ReportService(db_session)
    export_service = ExportService(report_service)

    assert export_service is not None
    assert export_service.report_service == report_service


def test_export_to_csv_empty(db_session):
    """Test exporting to CSV with no accounts"""
    report_service = ReportService(db_session)
    export_service = ExportService(report_service)
    organization_id = uuid4()

    csv_data = export_service.export_to_csv(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert csv_data is not None
    assert isinstance(csv_data, bytes)
    assert b"Account Code" in csv_data  # Header should be present


def test_export_to_json_empty(db_session):
    """Test exporting to JSON with no accounts"""
    report_service = ReportService(db_session)
    export_service = ExportService(report_service)
    organization_id = uuid4()

    json_data = export_service.export_to_json(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert json_data is not None
    assert isinstance(json_data, bytes)
    assert b"report_type" in json_data


def test_export_to_xlsx_empty(db_session):
    """Test exporting to XLSX with no accounts"""
    report_service = ReportService(db_session)
    export_service = ExportService(report_service)
    organization_id = uuid4()

    xlsx_data = export_service.export_to_xlsx(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert xlsx_data is not None
    assert isinstance(xlsx_data, bytes)
    # XLSX files start with PK (ZIP signature)
    assert xlsx_data[:2] == b"PK"


def test_export_to_pdf_empty(db_session):
    """Test exporting to PDF with no accounts"""
    report_service = ReportService(db_session)
    export_service = ExportService(report_service)
    organization_id = uuid4()

    pdf_data = export_service.export_to_pdf(
        organization_id=organization_id, as_of_date=date.today()
    )

    assert pdf_data is not None
    assert isinstance(pdf_data, bytes)
    # PDF files start with %PDF
    assert pdf_data[:4] == b"%PDF"
