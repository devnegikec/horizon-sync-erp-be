"""Tests for QR Product image replacement and storage."""

from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.config import settings
from app.services.qr_product_service import QRProductService
from app.services.storage_service import (
    delete_product_image,
    read_product_image,
    store_product_image,
)


def make_product_service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.product_repo = Mock()
    return service


@pytest.mark.parametrize(
    ("image_type", "field"),
    [
        ("logo", "image_url"),
        ("banner", "banner_image_url"),
    ],
)
def test_update_product_image_maps_type_to_url_field(image_type, field):
    service = make_product_service()
    product = SimpleNamespace(
        id=uuid4(),
        image_url="https://old.example/logo.png",
        banner_image_url="https://old.example/banner.png",
    )
    organization_id = uuid4()
    user_id = uuid4()
    new_url = f"https://new.example/{image_type}.png"
    service.product_repo.get_by_id.return_value = product
    service.product_repo.update.side_effect = lambda instance, payload: instance

    _, previous_url = service.update_product_image(
        product.id,
        image_type,
        new_url,
        organization_id,
        user_id,
    )

    assert previous_url == getattr(product, field)
    service.product_repo.get_by_id.assert_called_once_with(
        product.id, organization_id
    )
    service.product_repo.update.assert_called_once_with(
        product,
        {field: new_url, "updated_by": user_id},
    )


def test_update_product_image_rejects_cross_organization_product():
    service = make_product_service()
    service.product_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        service.update_product_image(
            uuid4(),
            "logo",
            "https://new.example/logo.png",
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 404
    service.product_repo.update.assert_not_called()


def test_local_product_image_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "aws_s3_bucket", "")
    monkeypatch.setattr(settings, "gcs_bucket", "")
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "product_image_upload_dir", str(tmp_path))
    data = b"test-png-data"

    object_key = store_product_image(
        data,
        "image/png",
        uuid4(),
        uuid4(),
        "logo",
    )

    stored_data, content_type = read_product_image(object_key)
    assert stored_data == data
    assert content_type == "image/png"

    delete_product_image(object_key)
    with pytest.raises(FileNotFoundError):
        read_product_image(object_key)


def test_product_image_storage_requires_s3_in_production(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "aws_s3_bucket", "")
    monkeypatch.setattr(settings, "gcs_bucket", "")
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "product_image_upload_dir", str(tmp_path))

    with pytest.raises(RuntimeError, match="AWS_S3_BUCKET is required"):
        store_product_image(
            b"test-png-data",
            "image/png",
            uuid4(),
            uuid4(),
            "logo",
        )


def test_s3_product_image_round_trip_uses_tenant_scoped_key(monkeypatch):
    organization_id = uuid4()
    product_id = uuid4()
    data = b"test-webp-data"
    stored_objects: dict[str, tuple[bytes, str]] = {}
    client = Mock()

    def put_object(**kwargs):
        stored_objects[kwargs["Key"]] = (kwargs["Body"], kwargs["ContentType"])

    def get_object(**kwargs):
        stored_data, content_type = stored_objects[kwargs["Key"]]
        return {"Body": BytesIO(stored_data), "ContentType": content_type}

    def delete_object(**kwargs):
        stored_objects.pop(kwargs["Key"], None)

    client.put_object.side_effect = put_object
    client.get_object.side_effect = get_object
    client.delete_object.side_effect = delete_object
    monkeypatch.setattr(settings, "aws_s3_bucket", "product-assets")
    monkeypatch.setattr(
        "app.services.storage_service._get_s3_client",
        lambda: client,
    )

    object_key = store_product_image(
        data,
        "image/webp",
        organization_id,
        product_id,
        "banner",
    )

    expected_prefix = (
        f"qseal/organizations/{organization_id}/products/{product_id}/"
        "images/banner/"
    )
    assert object_key.startswith(expected_prefix)
    assert object_key.endswith(".webp")
    assert stored_objects[object_key] == (data, "image/webp")
    client.put_object.assert_called_once_with(
        Bucket="product-assets",
        Key=object_key,
        Body=data,
        ContentType="image/webp",
        ServerSideEncryption="AES256",
    )

    assert read_product_image(object_key) == (data, "image/webp")

    delete_product_image(object_key)
    assert object_key not in stored_objects


def test_product_image_reader_rejects_non_image_qseal_keys(monkeypatch):
    client = Mock()
    monkeypatch.setattr(settings, "aws_s3_bucket", "product-assets")
    monkeypatch.setattr(
        "app.services.storage_service._get_s3_client",
        lambda: client,
    )

    workbook_key = (
        f"qseal/organizations/{uuid4()}/products/{uuid4()}/"
        f"blocks/{uuid4()}/qr_codes.xlsx"
    )
    with pytest.raises(ValueError, match="Invalid Product image object key"):
        read_product_image(workbook_key)

    client.get_object.assert_not_called()
