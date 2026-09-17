"""Regression coverage for API route collisions."""

from starlette.routing import Match

from app.main import app


def _first_matching_endpoint(path: str):
    scope = {
        "type": "http",
        "path": path,
        "method": "GET",
        "root_path": "",
    }
    for route in app.router.routes:
        match, _ = route.matches(scope)
        if match is Match.FULL:
            return route.endpoint
    return None


def test_qr_credit_balance_resolves_to_credit_endpoint():
    endpoint = _first_matching_endpoint("/api/v1/qr-credits/balance")

    assert endpoint is not None
    assert endpoint.__name__ == "get_organization_credit_balance"


def test_bank_account_balance_keeps_its_scoped_route():
    endpoint = _first_matching_endpoint(
        "/api/v1/bank-accounts/11111111-1111-1111-1111-111111111111/balance"
    )

    assert endpoint is not None
    assert endpoint.__name__ == "get_bank_account_balance"
