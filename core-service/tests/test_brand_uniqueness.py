"""Tests for organization-scoped brand uniqueness."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.brand import BrandCreate, BrandUpdate
from app.services.brand_service import BrandService


def make_service() -> BrandService:
    service = BrandService.__new__(BrandService)
    service.db = Mock()
    service.repo = Mock()
    service.key_service = Mock()
    service.key_service.generate_key_pair.return_value = ("encrypted", "public")
    return service


def test_brand_values_are_normalized_before_create():
    service = make_service()
    service.repo.value_exists.return_value = False
    service.repo.create.side_effect = lambda payload: payload

    result = service.create(
        BrandCreate(name="  Acme Corp  ", short_code=" ACME "),
        uuid4(),
        uuid4(),
    )

    assert result["name"] == "Acme Corp"
    assert result["short_code"] == "acme"


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", "N" * 21), ("short_code", "C" * 9)],
)
def test_brand_fields_enforce_maximum_lengths(field, value):
    with pytest.raises(ValidationError):
        BrandCreate(
            name=value if field == "name" else "Acme",
            short_code=value if field == "short_code" else "acme",
        )


@pytest.mark.parametrize(
    ("duplicate_field", "expected_detail"),
    [
        ("name", "Brand name 'Acme Corp' already exists for this organization."),
        ("short_code", "Brand short code 'acme' already exists for this organization."),
    ],
)
def test_duplicate_brand_values_return_conflict(duplicate_field, expected_detail):
    service = make_service()
    service.repo.value_exists.side_effect = lambda field, *_args: field == duplicate_field

    with pytest.raises(HTTPException) as exc_info:
        service.create(
            BrandCreate(name="Acme Corp", short_code="ACME"),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == expected_detail
    service.repo.create.assert_not_called()


def test_duplicate_brand_name_returns_conflict_on_update():
    service = make_service()
    brand = SimpleNamespace(id=uuid4())
    service.repo.get_by_id.return_value = brand
    service.repo.value_exists.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.update(
            brand.id,
            BrandUpdate(name="Acme Corp"),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Brand name 'Acme Corp' already exists for this organization."
    service.repo.update.assert_not_called()
