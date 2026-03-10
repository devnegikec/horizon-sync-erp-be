"""Tests for bank reconciliation reporting endpoints"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient


class TestReportingEndpoints:
    """Test suite for bank reconciliation reporting endpoints"""
    
    def test_generate_reconciliation_report_endpoint_exists(self, client: TestClient):
        """Test that the reconciliation report endpoint exists"""
        bank_account_id = uuid4()
        response = client.get(
            f"/api/v1/reconciliations/report",
            params={
                "bank_account_id": str(bank_account_id),
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
    
    def test_export_reconciliation_report_csv_endpoint_exists(self, client: TestClient):
        """Test that the CSV export endpoint exists"""
        bank_account_id = uuid4()
        response = client.get(
            f"/api/v1/reconciliations/report/export/csv",
            params={
                "bank_account_id": str(bank_account_id),
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
    
    def test_export_reconciliation_report_pdf_endpoint_exists(self, client: TestClient):
        """Test that the PDF export endpoint exists"""
        bank_account_id = uuid4()
        response = client.get(
            f"/api/v1/reconciliations/report/export/pdf",
            params={
                "bank_account_id": str(bank_account_id),
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
    
    def test_get_bank_account_balance_endpoint_exists(self, client: TestClient):
        """Test that the bank account balance endpoint exists"""
        bank_account_id = uuid4()
        response = client.get(
            f"/api/v1/bank-accounts/{bank_account_id}/balance"
        )
        # Should return 401 (unauthorized) not 404 (not found)
        assert response.status_code == 401
