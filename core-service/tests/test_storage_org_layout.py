"""Organization-scoped object-storage layout and S3-compatible settings."""

import uuid
from unittest.mock import Mock

import pytest

from app.config import settings
from app.services import storage_service
from app.services.organization_directory import (
    OrganizationDirectory,
    organization_folder,
    sanitize_org_slug,
)


@pytest.fixture(autouse=True)
def _clear_slug_cache():
    OrganizationDirectory.clear_cache()
    yield
    OrganizationDirectory.clear_cache()


def test_sanitize_org_slug_makes_path_safe_folder():
    assert sanitize_org_slug("Ciphercode Tech") == "ciphercode-tech"
    assert sanitize_org_slug("  Acme//Corp..  ") == "acme-corp"
    assert sanitize_org_slug("") is None
    assert sanitize_org_slug(None) is None


def test_organization_folder_uses_slug_from_identity(monkeypatch):
    org_id = uuid.uuid4()
    response = Mock(status_code=200)
    response.json.return_value = {"organization_id": str(org_id), "slug": "acme-corp"}
    requested = {}

    def fake_get(url, headers, timeout):
        requested["url"] = url
        requested["headers"] = headers
        return response

    monkeypatch.setattr("app.services.organization_directory.httpx.get", fake_get)

    assert organization_folder(org_id) == "orgs/acme-corp"
    assert str(org_id) in requested["url"]
    assert requested["headers"]["X-Internal-Secret"] == (
        settings.internal_service_secret
    )


def test_organization_folder_falls_back_to_uuid_when_lookup_fails(monkeypatch):
    org_id = uuid.uuid4()
    monkeypatch.setattr(
        "app.services.organization_directory.httpx.get",
        Mock(side_effect=RuntimeError("identity unavailable")),
    )

    assert organization_folder(org_id) == f"orgs/org-{org_id}"


def test_qr_artifact_key_is_org_scoped(monkeypatch):
    org_id, product_id, block_id = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    monkeypatch.setattr(
        storage_service, "organization_folder", lambda _org: "orgs/acme-corp"
    )

    key = storage_service.build_qr_artifact_key(org_id, product_id, block_id)

    assert key == (
        f"orgs/acme-corp/qseal/products/{product_id}/blocks/{block_id}/qr_codes.xlsx"
    )


def test_product_image_key_pattern_accepts_slug_and_legacy_layouts():
    pattern = storage_service.PRODUCT_IMAGE_S3_KEY_PATTERN
    org_id, product_id = uuid.uuid4(), uuid.uuid4()

    new_key = f"orgs/acme-corp/qseal/products/{product_id}/images/logo/{'a' * 32}.png"
    legacy_key = (
        f"qseal/organizations/{org_id}/products/{product_id}/images/logo/"
        f"{'b' * 32}.webp"
    )

    assert pattern.fullmatch(new_key)
    assert pattern.fullmatch(legacy_key)


def test_sse_header_is_omitted_when_provider_does_not_support_it(monkeypatch):
    monkeypatch.setattr(settings, "aws_s3_server_side_encryption", "")

    assert storage_service._sse_kwargs() == {}


def test_sse_header_is_omitted_for_explicit_disable_word(monkeypatch):
    monkeypatch.setattr(settings, "aws_s3_server_side_encryption", "none")

    assert storage_service._sse_kwargs() == {}


def test_sse_header_defaults_to_aes256(monkeypatch):
    monkeypatch.setattr(settings, "aws_s3_server_side_encryption", "AES256")

    assert storage_service._sse_kwargs() == {"ServerSideEncryption": "AES256"}
