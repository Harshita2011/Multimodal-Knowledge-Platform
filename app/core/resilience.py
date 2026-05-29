import random
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass
from typing import TypeVar

from app.core.exceptions import AppError

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    max_attempts: int = 3
    initial_delay: float = 0.5
    max_delay: float = 8.0
    exponential_backoff: bool = True
    jitter: bool = True


def call_with_timeout(fn: Callable[[], T], timeout_seconds: float, code: str, message: str, status_code: int = 504) -> T:
    with ThreadPoolExecutor(max_workers=1) as ex:
        future = ex.submit(fn)
        try:
            return future.result(timeout=timeout_seconds)
        except FuturesTimeout as exc:
            raise AppError(code, message, status_code) from exc


def compute_retry_delay_seconds(policy: RetryPolicy, attempt_index: int) -> float:
    base_delay = policy.initial_delay
    if policy.exponential_backoff:
        base_delay = policy.initial_delay * (2 ** attempt_index)
    delay = min(base_delay, policy.max_delay)
    if policy.jitter:
        delay = random.uniform(delay * 0.5, delay)
    return delay


def with_retries(fn: Callable[[], T], policy: RetryPolicy, is_retryable: Callable[[Exception], bool]) -> T:
    attempts = 0
    while True:
        try:
            return fn()
        except Exception as exc:
            attempts += 1
            if attempts >= policy.max_attempts or not is_retryable(exc):
                raise
            time.sleep(compute_retry_delay_seconds(policy, attempts - 1))
