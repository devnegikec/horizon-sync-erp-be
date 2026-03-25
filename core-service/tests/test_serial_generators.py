"""
Unit tests for serial number generation utilities and QR helpers.

Tests R6DAN, R4DAN, S8DN, S10DN generators, sign_qr_item, and build_qr_url.
Validates: Requirements 7.1, 7.2, 7.3, 7.4
"""

import re
import string
import time
from unittest.mock import MagicMock, patch

import pytest
from cryptography.fernet import Fernet

from app.services.key_service import KeyService
from app.utils.serial_generators import (
    build_qr_url,
    generate_r4dan,
    generate_r6dan,
    sequential_s10dn,
    sequential_s8dn,
    sign_qr_item,
)

ALPHANUMERIC = set(string.ascii_uppercase + string.digits)


# ── Random generators ──────────────────────────────────────────────


class TestGenerateR6DAN:
    def test_length_is_6(self):
        assert len(generate_r6dan()) == 6

    def test_only_uppercase_and_digits(self):
        serial = generate_r6dan()
        assert all(c in ALPHANUMERIC for c in serial)

    def test_multiple_calls_produce_different_values(self):
        serials = {generate_r6dan() for _ in range(50)}
        assert len(serials) > 1


class TestGenerateR4DAN:
    def test_length_is_4(self):
        assert len(generate_r4dan()) == 4

    def test_only_uppercase_and_digits(self):
        serial = generate_r4dan()
        assert all(c in ALPHANUMERIC for c in serial)

    def test_multiple_calls_produce_different_values(self):
        serials = {generate_r4dan() for _ in range(50)}
        assert len(serials) > 1


# ── Sequential generators ──────────────────────────────────────────


class TestSequentialS8DN:
    def test_default_start(self):
        gen = sequential_s8dn()
        assert next(gen) == "00000001"
        assert next(gen) == "00000002"

    def test_custom_start(self):
        gen = sequential_s8dn(start=100)
        assert next(gen) == "00000100"
        assert next(gen) == "00000101"

    def test_zero_padded_to_8_digits(self):
        gen = sequential_s8dn(start=1)
        for _ in range(5):
            val = next(gen)
            assert len(val) == 8
            assert val.isdigit()

    def test_large_number(self):
        gen = sequential_s8dn(start=99999999)
        assert next(gen) == "99999999"


class TestSequentialS10DN:
    def test_default_start(self):
        gen = sequential_s10dn()
        assert next(gen) == "0000000001"
        assert next(gen) == "0000000002"

    def test_custom_start(self):
        gen = sequential_s10dn(start=500)
        assert next(gen) == "0000000500"

    def test_zero_padded_to_10_digits(self):
        gen = sequential_s10dn(start=1)
        for _ in range(5):
            val = next(gen)
            assert len(val) == 10
            assert val.isdigit()


# ── sign_qr_item ───────────────────────────────────────────────────


class TestSignQrItem:
    @pytest.fixture
    def key_service(self):
        fernet_key = Fernet.generate_key().decode()
        return KeyService(encryption_secret=fernet_key)

    def test_returns_tuple_of_signature_and_timestamp(self, key_service):
        encrypted_priv, _ = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_priv)

        sig, ts = sign_qr_item(key_service, private_key, "ABC123")
        assert isinstance(sig, str)
        assert isinstance(ts, int)

    def test_timestamp_is_current_epoch_ms(self, key_service):
        encrypted_priv, _ = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_priv)

        before = int(time.time() * 1000)
        _, ts = sign_qr_item(key_service, private_key, "SN001")
        after = int(time.time() * 1000)

        assert before <= ts <= after

    def test_signature_verifies_with_public_key(self, key_service):
        encrypted_priv, public_hex = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_priv)

        sig, ts = sign_qr_item(key_service, private_key, "SN001")
        message = f"SN001~{ts}"

        assert key_service.verify_signature(public_hex, message, sig) is True

    def test_signature_fails_with_wrong_serial(self, key_service):
        encrypted_priv, public_hex = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_priv)

        sig, ts = sign_qr_item(key_service, private_key, "SN001")
        wrong_message = f"WRONG~{ts}"

        assert key_service.verify_signature(public_hex, wrong_message, sig) is False


# ── build_qr_url ───────────────────────────────────────────────────


class TestBuildQrUrl:
    def test_url_format(self):
        url = build_qr_url(
            org_short_code="acme",
            domain="verify.example.com",
            gtin="1234567890123",
            serial_number="ABC123",
            timestamp=1718000000000,
            signature="c2lnbmF0dXJl",
        )
        assert url == (
            "https://acme.verify.example.com"
            "/g/1234567890123/s/ABC123/1718000000000?c=c2lnbmF0dXJl"
        )

    def test_url_starts_with_https(self):
        url = build_qr_url("org", "d.com", "gtin", "sn", 123, "sig")
        assert url.startswith("https://")

    def test_url_contains_all_components(self):
        url = build_qr_url("myorg", "qr.io", "0012345", "XY99", 999, "abc123")
        assert "myorg.qr.io" in url
        assert "/g/0012345/" in url
        assert "/s/XY99/" in url
        assert "/999?" in url
        assert "c=abc123" in url
