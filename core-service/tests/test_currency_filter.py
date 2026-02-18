"""Test currency filtering in chart of accounts API"""

import pytest


class TestCurrencyFilter:
    """Test currency filtering functionality"""

    def test_filter_accounts_by_currency(self, client):
        """Test filtering accounts by currency code"""
        # Create accounts with different currencies
        usd_account = {
            "account_code": "1000-USD",
            "account_name": "USD Cash Account",
            "account_type": "asset",
            "currency": "USD",
        }
        eur_account = {
            "account_code": "1000-EUR",
            "account_name": "EUR Cash Account",
            "account_type": "asset",
            "currency": "EUR",
        }
        gbp_account = {
            "account_code": "1000-GBP",
            "account_name": "GBP Cash Account",
            "account_type": "asset",
            "currency": "GBP",
        }

        # Create the accounts
        client.post("/api/v1/chart-of-accounts", json=usd_account)
        client.post("/api/v1/chart-of-accounts", json=eur_account)
        client.post("/api/v1/chart-of-accounts", json=gbp_account)

        # Filter by USD
        response = client.get("/api/v1/chart-of-accounts?currency=USD")
        assert response.status_code == 200
        data = response.json()
        assert len(data["chart_of_accounts"]) == 1
        assert data["chart_of_accounts"][0]["currency"] == "USD"
        assert data["chart_of_accounts"][0]["account_code"] == "1000-USD"

        # Filter by EUR
        response = client.get("/api/v1/chart-of-accounts?currency=EUR")
        assert response.status_code == 200
        data = response.json()
        assert len(data["chart_of_accounts"]) == 1
        assert data["chart_of_accounts"][0]["currency"] == "EUR"
        assert data["chart_of_accounts"][0]["account_code"] == "1000-EUR"

        # No filter - should return all
        response = client.get("/api/v1/chart-of-accounts")
        assert response.status_code == 200
        data = response.json()
        assert len(data["chart_of_accounts"]) >= 3

    def test_filter_accounts_by_currency_no_results(self, client):
        """Test filtering by currency with no matching accounts"""
        # Create a USD account
        usd_account = {
            "account_code": "2000-USD",
            "account_name": "USD Account",
            "account_type": "asset",
            "currency": "USD",
        }
        client.post("/api/v1/chart-of-accounts", json=usd_account)

        # Filter by JPY (no accounts with this currency)
        response = client.get("/api/v1/chart-of-accounts?currency=JPY")
        assert response.status_code == 200
        data = response.json()
        assert len(data["chart_of_accounts"]) == 0
