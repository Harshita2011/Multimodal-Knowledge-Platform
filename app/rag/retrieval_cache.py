import time


class RetrievalCache:
    def __init__(self, ttl_seconds: int = 120, max_entries: int = 500):
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self._store: dict[str, tuple[float, dict]] = {}

    def _evict_if_needed(self) -> None:
        if len(self._store) <= self.max_entries:
            return
        oldest = sorted(self._store.items(), key=lambda kv: kv[1][0])[: max(1, len(self._store) - self.max_entries)]
        for key, _ in oldest:
            self._store.pop(key, None)

    def get(self, key: str) -> dict | None:
        row = self._store.get(key)
        now = time.time()
        if row is None:
            return None
        ts, payload = row
        if now - ts > self.ttl_seconds:
            self._store.pop(key, None)
            return None
        return payload

    def put(self, key: str, payload: dict) -> None:
        self._store[key] = (time.time(), payload)
        self._evict_if_needed()

    def invalidate_document(self, document_id: str) -> None:
        keys = [k for k in self._store if f"doc={document_id}" in k]
        for k in keys:
            self._store.pop(k, None)
