"""Tests for Chart of Accounts Setup API endpoints"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.chart_of_accounts_setup import DefaultChartResult

client = TestClient(app)


class TestCreateDefaultChartEndpoint:
    """Tests for POST /api/v1/setup/default-chart-of-accounts endpoint"""

    def test_create_default_chart_success(self, db_session):
        """Test successful chart creation returns 200 OK"""
        organization_id = uuid.uuid4()
        request_data = {
            "organization_id": str(organization_id),
            "currency": "USD",
            "created_by": "test_user",
        }

        # Mock the service to return success result
        mock_result = DefaultChartResult(
            accounts=[
                {
                    "id": str(uuid.uuid4()),
                    "account_code": "1000",
                    "account_name": "Cash and Bank Accounts",
                    "account_type": "ASSET",
                }
            ],
            mappings=[
                {
                    "id": str(uuid.uuid4()),
                    "transaction_type": "payment",
                    "scenario": "cash",
                    "account_id": str(uuid.uuid4()),
                }
            ],
            already_existed=False,
        )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/v1/setup/default-chart-of-accounts", json=request_data
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["organization_id"] == str(organization_id)
        assert data["accounts_created"] == 1
        assert data["mappings_created"] == 1
        assert "created successfully" in data["message"]

    def test_create_default_chart_already_exists(self, db_session):
        """Test idempotent behavior when chart already exists returns 200 OK"""
        organization_id = uuid.uuid4()
        request_data = {
            "organization_id": str(organization_id),
            "currency": "USD",
            "created_by": "test_user",
        }

        # Mock the service to return already existed result
        mock_result = DefaultChartResult(
            accounts=[],
            mappings=[],
            already_existed=True,
        )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/v1/setup/default-chart-of-accounts", json=request_data
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["organization_id"] == str(organization_id)
        assert data["accounts_created"] == 0
        assert data["mappings_created"] == 0
        assert "already exists" in data["message"]

    def test_create_default_chart_invalid_currency(self, db_session):
        """Test invalid currency code returns 400/422 validation error"""
        organization_id = uuid.uuid4()
        request_data = {
            "organization_id": str(organization_id),
            "currency": "INVALID",  # 7 characters, should be 3
            "created_by": "test_user",
        }

        response = client.post(
            "/api/v1/setup/default-chart-of-accounts", json=request_data
        )

        # FastAPI may return 400 or 422 for validation errors
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_create_default_chart_missing_created_by(self, db_session):
        """Test missing created_by field returns 400/422 validation error"""
        organization_id = uuid.uuid4()
        request_data = {
            "organization_id": str(organization_id),
            "currency": "USD",
            # created_by is missing
        }

        response = client.post(
            "/api/v1/setup/default-chart-of-accounts", json=request_data
        )

        # FastAPI may return 400 or 422 for validation errors
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        ]

    def test_create_default_chart_service_error(self, db_session):
        """Test service error returns 500 internal server error"""
        organization_id = uuid.uuid4()
        request_data = {
            "organization_id": str(organization_id),
            "currency": "USD",
            "created_by": "test_user",
        }

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.side_effect = Exception(
                "Database error"
            )
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/v1/setup/default-chart-of-accounts", json=request_data
            )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to create default chart of accounts" in data["detail"]

    def test_create_default_chart_default_currency(self, db_session):
        """Test currency defaults to USD when not provided"""
        organization_id = uuid.uuid4()
        request_data = {
            "organization_id": str(organization_id),
            # currency not provided, should default to USD
            "created_by": "test_user",
        }

        mock_result = DefaultChartResult(
            accounts=[],
            mappings=[],
            already_existed=False,
        )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            response = client.post(
                "/api/v1/setup/default-chart-of-accounts", json=request_data
            )

        assert response.status_code == status.HTTP_200_OK
        # Verify the service was called with USD as default
        mock_service.create_default_chart_of_accounts.assert_called_once()
        call_args = mock_service.create_default_chart_of_accounts.call_args
        assert call_args.kwargs["currency"] == "USD"


class TestTriggerDefaultChartEndpoint:
    """Tests for POST /api/v1/setup/default-chart-of-accounts/{organization_id}/trigger endpoint"""

    def test_trigger_default_chart_success(self, db_session):
        """Test successful manual trigger returns 200 OK"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        request_data = {
            "currency": "EUR",
            "force_recreate": False,
        }

        # Mock the service to return success result
        mock_result = DefaultChartResult(
            accounts=[
                {
                    "id": str(uuid.uuid4()),
                    "account_code": "1000",
                    "account_name": "Cash and Bank Accounts",
                    "account_type": "ASSET",
                }
            ],
            mappings=[
                {
                    "id": str(uuid.uuid4()),
                    "transaction_type": "payment",
                    "scenario": "cash",
                    "account_id": str(uuid.uuid4()),
                }
            ],
            already_existed=False,
        )

        # Mock current user
        from app.dependencies import CurrentUser, get_current_active_user

        def override_get_current_active_user():
            return CurrentUser(
                id=user_id,
                email="admin@test.com",
                organization_id=organization_id,
                user_type="admin",
                permissions=["chart.*"],
            )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            # Override the dependency
            from app.main import app

            app.dependency_overrides[get_current_active_user] = (
                override_get_current_active_user
            )

            try:
                response = client.post(
                    f"/api/v1/setup/default-chart-of-accounts/{organization_id}/trigger",
                    json=request_data,
                )
            finally:
                # Clean up override
                app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["organization_id"] == str(organization_id)
        assert data["accounts_created"] == 1
        assert data["mappings_created"] == 1
        assert "created successfully" in data["message"]

        # Verify service was called with correct parameters
        mock_service.create_default_chart_of_accounts.assert_called_once()
        call_args = mock_service.create_default_chart_of_accounts.call_args
        assert call_args.kwargs["organization_id"] == organization_id
        assert call_args.kwargs["currency"] == "EUR"
        assert call_args.kwargs["created_by"] == str(user_id)

    def test_trigger_default_chart_already_exists(self, db_session):
        """Test manual trigger when chart already exists returns 200 OK"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        request_data = {
            "currency": "USD",
            "force_recreate": False,
        }

        # Mock the service to return already existed result
        mock_result = DefaultChartResult(
            accounts=[],
            mappings=[],
            already_existed=True,
        )

        # Mock current user
        from app.dependencies import CurrentUser, get_current_active_user

        def override_get_current_active_user():
            return CurrentUser(
                id=user_id,
                email="admin@test.com",
                organization_id=organization_id,
                user_type="admin",
                permissions=["chart.*"],
            )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            # Override the dependency
            from app.main import app

            app.dependency_overrides[get_current_active_user] = (
                override_get_current_active_user
            )

            try:
                response = client.post(
                    f"/api/v1/setup/default-chart-of-accounts/{organization_id}/trigger",
                    json=request_data,
                )
            finally:
                # Clean up override
                app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["organization_id"] == str(organization_id)
        assert data["accounts_created"] == 0
        assert data["mappings_created"] == 0
        assert "already exists" in data["message"]

    def test_trigger_default_chart_without_auth(self, db_session):
        """Test manual trigger without authentication returns 401"""
        organization_id = uuid.uuid4()
        request_data = {
            "currency": "USD",
            "force_recreate": False,
        }

        # Create a client without auth header
        from fastapi.testclient import TestClient

        from app.main import app

        unauthenticated_client = TestClient(app)

        response = unauthenticated_client.post(
            f"/api/v1/setup/default-chart-of-accounts/{organization_id}/trigger",
            json=request_data,
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_trigger_default_chart_default_currency(self, db_session):
        """Test manual trigger defaults to USD when currency not provided"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        request_data = {
            # currency not provided, should default to USD
            "force_recreate": False,
        }

        mock_result = DefaultChartResult(
            accounts=[],
            mappings=[],
            already_existed=False,
        )

        # Mock current user
        from app.dependencies import CurrentUser, get_current_active_user

        def override_get_current_active_user():
            return CurrentUser(
                id=user_id,
                email="admin@test.com",
                organization_id=organization_id,
                user_type="admin",
                permissions=["chart.*"],
            )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            # Override the dependency
            from app.main import app

            app.dependency_overrides[get_current_active_user] = (
                override_get_current_active_user
            )

            try:
                response = client.post(
                    f"/api/v1/setup/default-chart-of-accounts/{organization_id}/trigger",
                    json=request_data,
                )
            finally:
                # Clean up override
                app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_200_OK
        # Verify the service was called with USD as default
        mock_service.create_default_chart_of_accounts.assert_called_once()
        call_args = mock_service.create_default_chart_of_accounts.call_args
        assert call_args.kwargs["currency"] == "USD"

    def test_trigger_default_chart_force_recreate_warning(self, db_session):
        """Test manual trigger with force_recreate logs warning (not yet implemented)"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        request_data = {
            "currency": "USD",
            "force_recreate": True,  # This should log a warning
        }

        mock_result = DefaultChartResult(
            accounts=[],
            mappings=[],
            already_existed=False,
        )

        # Mock current user
        from app.dependencies import CurrentUser, get_current_active_user

        def override_get_current_active_user():
            return CurrentUser(
                id=user_id,
                email="admin@test.com",
                organization_id=organization_id,
                user_type="admin",
                permissions=["chart.*"],
            )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.return_value = mock_result
            mock_service_class.return_value = mock_service

            # Override the dependency
            from app.main import app

            app.dependency_overrides[get_current_active_user] = (
                override_get_current_active_user
            )

            try:
                response = client.post(
                    f"/api/v1/setup/default-chart-of-accounts/{organization_id}/trigger",
                    json=request_data,
                )
            finally:
                # Clean up override
                app.dependency_overrides.clear()

        # Should still succeed even though force_recreate is not implemented
        assert response.status_code == status.HTTP_200_OK

    def test_trigger_default_chart_service_error(self, db_session):
        """Test manual trigger service error returns 500"""
        organization_id = uuid.uuid4()
        user_id = uuid.uuid4()
        request_data = {
            "currency": "USD",
            "force_recreate": False,
        }

        # Mock current user
        from app.dependencies import CurrentUser, get_current_active_user

        def override_get_current_active_user():
            return CurrentUser(
                id=user_id,
                email="admin@test.com",
                organization_id=organization_id,
                user_type="admin",
                permissions=["chart.*"],
            )

        with patch(
            "app.api.v1.endpoints.chart_of_accounts_setup.DefaultChartSetupService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.create_default_chart_of_accounts.side_effect = Exception(
                "Database error"
            )
            mock_service_class.return_value = mock_service

            # Override the dependency
            from app.main import app

            app.dependency_overrides[get_current_active_user] = (
                override_get_current_active_user
            )

            try:
                response = client.post(
                    f"/api/v1/setup/default-chart-of-accounts/{organization_id}/trigger",
                    json=request_data,
                )
            finally:
                # Clean up override
                app.dependency_overrides.clear()

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "Failed to create default chart of accounts" in data["detail"]
