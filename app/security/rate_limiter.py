import time
from abc import ABC, abstractmethod


class RateLimiter(ABC):
    @abstractmethod
    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    def __init__(self):
        self._buckets: dict[str, list[float]] = {}

    def allow(self, key: str, limit: int, window_seconds: int) -> bool:
        now = time.time()
        values = self._buckets.get(key, [])
        cutoff = now - window_seconds
        values = [t for t in values if t >= cutoff]
        if len(values) >= limit:
            self._buckets[key] = values
            return False
        values.append(now)
        self._buckets[key] = values
        return True


limiter = InMemoryRateLimiter()
