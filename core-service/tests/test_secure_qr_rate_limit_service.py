from app.services.secure_qr_rate_limit_service import SecureQRRateLimiter


class FakeCache:
    def __init__(self):
        self.counters = {}
        self.ttls = {}
        self.deleted = []
        self.set_values = []

    def increment_with_ttl(self, key, ttl):
        self.counters[key] = self.counters.get(key, 0) + 1
        self.ttls.setdefault(key, ttl)
        return self.counters[key]

    def ttl(self, key):
        return self.ttls.get(key)

    def set(self, key, value, ttl=3600):
        self.set_values.append((key, value, ttl))
        self.ttls[key] = ttl
        return True

    def delete(self, key):
        self.deleted.append(key)
        self.ttls.pop(key, None)
        return True


def test_source_rate_limit_blocks_after_configured_threshold(monkeypatch):
    monkeypatch.setattr("app.services.secure_qr_rate_limit_service.settings.secure_qr_rate_limit_per_minute", 1)
    cache = FakeCache()
    limiter = SecureQRRateLimiter(cache)

    assert limiter.before_attempt("SERIAL-1", "203.0.113.10") is None
    decision = limiter.before_attempt("SERIAL-2", "203.0.113.10")

    assert decision is not None
    assert decision.reason == "rate_limit"
    assert decision.retry_after_seconds == 60


def test_failed_attempts_create_a_temporary_lockout(monkeypatch):
    monkeypatch.setattr("app.services.secure_qr_rate_limit_service.settings.secure_qr_failed_attempt_limit", 2)
    cache = FakeCache()
    limiter = SecureQRRateLimiter(cache)

    assert limiter.record_failure("SERIAL-1", "203.0.113.10") is None
    decision = limiter.record_failure("SERIAL-1", "203.0.113.10")

    assert decision is not None
    assert decision.reason == "lockout"
    assert decision.retry_after_seconds == 900
    assert cache.set_values[-1][1:] == (True, 900)


def test_existing_lockout_is_returned_before_consuming_rate_limit_slot():
    cache = FakeCache()
    limiter = SecureQRRateLimiter(cache)
    lockout_key = limiter._lockout_key("SERIAL-1", "203.0.113.10")
    cache.ttls[lockout_key] = 120

    decision = limiter.before_attempt("SERIAL-1", "203.0.113.10")

    assert decision is not None
    assert decision.reason == "lockout"
    assert decision.retry_after_seconds == 120
    assert cache.counters == {}
