from app.core.exceptions import AppError
from app.core.resilience import RetryPolicy, compute_retry_delay_seconds, with_retries


def test_compute_retry_delay_respects_cap_and_bounds_with_jitter():
    policy = RetryPolicy(max_attempts=3, initial_delay=0.5, max_delay=8, exponential_backoff=True, jitter=True)
    d0 = compute_retry_delay_seconds(policy, 0)
    d1 = compute_retry_delay_seconds(policy, 1)
    d6 = compute_retry_delay_seconds(policy, 6)
    assert 0.25 <= d0 <= 0.5
    assert 0.5 <= d1 <= 1.0
    assert 4.0 <= d6 <= 8.0


def test_with_retries_retries_retryable_errors_then_succeeds():
    policy = RetryPolicy(max_attempts=3, initial_delay=0.001, max_delay=0.002, exponential_backoff=True, jitter=False)
    state = {"attempts": 0}

    def fn():
        state["attempts"] += 1
        if state["attempts"] < 3:
            raise AppError("llm_timeout", "timeout", 504)
        return "ok"

    out = with_retries(fn, policy=policy, is_retryable=lambda exc: isinstance(exc, AppError) and exc.code == "llm_timeout")
    assert out == "ok"
    assert state["attempts"] == 3
