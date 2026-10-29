"""Rate limiting and temporary lockouts for Secure QR code attempts."""

import hashlib
import hmac
from dataclasses import dataclass

from app.config import settings
from app.core.cache import RedisCache, cache


@dataclass(frozen=True)
class SecureQRRateLimitDecision:
    """A blocked attempt and the number of seconds before retrying."""

    reason: str
    retry_after_seconds: int


class SecureQRRateLimiter:
    """Use privacy-safe Redis keys to protect Secure QR code attempts.

    The source limit prevents one client from rapidly trying codes across
    products. The per-serial failure counter temporarily locks a source out
    after repeated incorrect attempts for the same Secure QR.

    Redis failures fail open so a cache outage cannot take down public QR
    verification. Deployed environments should keep Redis available for the
    protection to be enforced consistently across worker processes.
    """

    KEY_PREFIX = "qseal:secure-qr"

    def __init__(self, cache_client: RedisCache | None = None):
        self.cache = cache_client or cache

    @staticmethod
    def _fingerprint(*values: str) -> str:
        payload = "\x00".join(values).encode("utf-8")
        return hmac.new(
            settings.secret_key.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()

    def _source_key(self, client_ip: str | None) -> str:
        source = client_ip or "unknown"
        return f"{self.KEY_PREFIX}:source:{self._fingerprint(source)}"

    def _failure_key(self, serial_number: str, client_ip: str | None) -> str:
        return f"{self.KEY_PREFIX}:failure:{self._fingerprint(serial_number, client_ip or 'unknown')}"

    def _lockout_key(self, serial_number: str, client_ip: str | None) -> str:
        return f"{self.KEY_PREFIX}:lockout:{self._fingerprint(serial_number, client_ip or 'unknown')}"

    def before_attempt(
        self, serial_number: str, client_ip: str | None
    ) -> SecureQRRateLimitDecision | None:
        """Check the lockout and consume one source-rate-limit slot."""
        lockout_ttl = self.cache.ttl(self._lockout_key(serial_number, client_ip))
        if lockout_ttl:
            return SecureQRRateLimitDecision("lockout", lockout_ttl)

        source_count = self.cache.increment_with_ttl(
            self._source_key(client_ip), 60
        )
        if (
            source_count is not None
            and source_count > settings.secure_qr_rate_limit_per_minute
        ):
            retry_after = self.cache.ttl(self._source_key(client_ip)) or 60
            return SecureQRRateLimitDecision("rate_limit", retry_after)
        return None

    def record_failure(
        self, serial_number: str, client_ip: str | None
    ) -> SecureQRRateLimitDecision | None:
        """Record a wrong code and create a temporary source lockout if needed."""
        failure_key = self._failure_key(serial_number, client_ip)
        failure_count = self.cache.increment_with_ttl(
            failure_key, settings.secure_qr_failed_attempt_window_seconds
        )
        if (
            failure_count is not None
            and failure_count >= settings.secure_qr_failed_attempt_limit
        ):
            lockout_key = self._lockout_key(serial_number, client_ip)
            self.cache.set(lockout_key, True, settings.secure_qr_lockout_seconds)
            self.cache.delete(failure_key)
            return SecureQRRateLimitDecision(
                "lockout", settings.secure_qr_lockout_seconds
            )
        return None

    def clear_failures(self, serial_number: str, client_ip: str | None) -> None:
        """Clear failed-attempt state after a successful code submission."""
        self.cache.delete(self._failure_key(serial_number, client_ip))
        self.cache.delete(self._lockout_key(serial_number, client_ip))
