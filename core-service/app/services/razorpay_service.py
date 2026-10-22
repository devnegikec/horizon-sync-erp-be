"""Razorpay client for credit top-up checkout and webhook verification.

Card data never touches this service: the browser completes payment with
Razorpay Checkout using ``key_id`` + provider order id, and this backend only
trusts server-side verified events/payments.
"""

import hashlib
import hmac
import logging

import httpx
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger(__name__)


class RazorpayService:
    BASE_URL = "https://api.razorpay.com/v1"

    def __init__(
        self,
        key_id: str | None = None,
        key_secret: str | None = None,
        webhook_secret: str | None = None,
    ):
        self.key_id = key_id if key_id is not None else settings.razorpay_key_id
        self.key_secret = (
            key_secret if key_secret is not None else settings.razorpay_key_secret
        )
        self.webhook_secret = (
            webhook_secret
            if webhook_secret is not None
            else settings.razorpay_webhook_secret
        )

    @property
    def enabled(self) -> bool:
        return bool(self.key_id and self.key_secret)

    def _auth(self) -> tuple[str, str]:
        if not self.enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "code": "PAYMENT_PROVIDER_NOT_CONFIGURED",
                    "message": "Razorpay is not configured",
                },
            )
        return self.key_id, self.key_secret

    def _request(self, method: str, path: str, **kwargs) -> dict:
        try:
            with httpx.Client(timeout=settings.razorpay_timeout_seconds) as client:
                response = client.request(
                    method,
                    f"{self.BASE_URL}{path}",
                    auth=self._auth(),
                    **kwargs,
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error(
                "Razorpay %s %s failed: %s %s",
                method,
                path,
                exc.response.status_code,
                exc.response.text[:500],
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "PAYMENT_PROVIDER_ERROR",
                    "message": "Razorpay rejected the request",
                },
            ) from exc
        except httpx.HTTPError as exc:
            logger.error("Razorpay %s %s unreachable: %s", method, path, exc)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "code": "PAYMENT_PROVIDER_UNAVAILABLE",
                    "message": "Razorpay is unreachable",
                },
            ) from exc

    def create_order(
        self,
        *,
        amount_paise: int,
        receipt: str,
        notes: dict | None = None,
    ) -> dict:
        payload = {
            "amount": int(amount_paise),
            "currency": settings.razorpay_currency,
            "receipt": receipt[:40],
            "payment_capture": 1,
        }
        if notes:
            payload["notes"] = {k: str(v) for k, v in notes.items()}
        return self._request("POST", "/orders", json=payload)

    def fetch_order(self, provider_order_id: str) -> dict:
        return self._request("GET", f"/orders/{provider_order_id}")

    def fetch_payment(self, provider_payment_id: str) -> dict:
        return self._request("GET", f"/payments/{provider_payment_id}")

    def verify_webhook_signature(self, raw_body: bytes, signature: str) -> bool:
        """HMAC-SHA256 of the raw body with the webhook secret."""
        if not self.webhook_secret or not signature:
            return False
        expected = hmac.new(
            self.webhook_secret.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def verify_checkout_signature(
        self,
        provider_order_id: str,
        provider_payment_id: str,
        signature: str,
    ) -> bool:
        """HMAC-SHA256 of ``order_id|payment_id`` with the API key secret."""
        if not self.key_secret or not signature:
            return False
        message = f"{provider_order_id}|{provider_payment_id}".encode()
        expected = hmac.new(
            self.key_secret.encode(), message, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
