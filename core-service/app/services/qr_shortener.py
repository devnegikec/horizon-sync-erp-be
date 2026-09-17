"""Short URL provider used by QR block generation workers."""

import logging
import time
from collections.abc import Callable
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class QRShortenerError(RuntimeError):
    """Raised when a QR URL cannot be shortened safely."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class QRShortener:
    """Create short QR URLs through the configured CloudFront endpoint."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.client = client
        self.sleep = sleep

    def shorten(self, long_url: str) -> str:
        """Return one validated short URL, retrying transient provider errors."""
        if not settings.qr_shortener_enabled:
            return long_url

        attempts = max(0, settings.qr_shortener_max_retries) + 1
        last_error: Exception | None = None
        attempted = 0

        for attempt in range(attempts):
            attempted += 1
            try:
                response = self._post(long_url)
                if response.status_code >= 400:
                    raise QRShortenerError(
                        f"Short URL provider returned HTTP {response.status_code}",
                        retryable=(
                            response.status_code == 429
                            or response.status_code >= 500
                        ),
                    )
                return self._validated_short_url(response)
            except (httpx.RequestError, QRShortenerError) as exc:
                last_error = exc
                if attempt == attempts - 1 or not self._is_retryable(exc):
                    break
                self.sleep(min(0.25 * (2**attempt), 2.0))

        logger.error(
            "QR short URL generation failed after %d attempt(s)",
            attempted,
        )
        raise QRShortenerError("QR short URL generation failed") from last_error

    def _post(self, long_url: str) -> httpx.Response:
        payload = {
            "cdn_prefix": settings.qr_shortener_cdn_prefix,
            "url_long": long_url,
        }
        if self.client is not None:
            return self.client.post(settings.qr_shortener_url, json=payload)
        with httpx.Client(timeout=settings.qr_shortener_timeout_seconds) as client:
            return client.post(settings.qr_shortener_url, json=payload)

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, httpx.RequestError):
            return True
        return isinstance(exc, QRShortenerError) and exc.retryable

    @staticmethod
    def _validated_short_url(response: httpx.Response) -> str:
        try:
            short_url = response.json()["url_short"]
        except (ValueError, KeyError, TypeError) as exc:
            raise QRShortenerError(
                "Short URL provider returned an invalid response"
            ) from exc

        if not isinstance(short_url, str):
            raise QRShortenerError("Short URL provider returned an invalid URL")

        parsed = urlparse(short_url.strip())
        expected_host = settings.qr_shortener_cdn_prefix.lower()
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname != expected_host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port is not None
        ):
            raise QRShortenerError("Short URL provider returned an invalid URL")
        return parsed._replace(scheme="https").geturl()
