from app.security.rate_limiter import InMemoryRateLimiter


def test_rate_limiter_enforces_limit():
    limiter = InMemoryRateLimiter()
    key = "k"
    assert limiter.allow(key, limit=2, window_seconds=60)
    assert limiter.allow(key, limit=2, window_seconds=60)
    assert not limiter.allow(key, limit=2, window_seconds=60)
