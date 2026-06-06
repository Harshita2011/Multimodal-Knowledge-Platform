import time
from abc import ABC, abstractmethod

from sentence_transformers import CrossEncoder

from app.models.domain.entities import RetrievedChunk


class Reranker(ABC):
    @abstractmethod
    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        raise NotImplementedError


class SemanticReranker(Reranker):
    """Cross-encoder reranker with latency caps and graceful fallback."""

    def __init__(self, model_name: str, timeout_ms: int, top_n: int = 8):
        self.model_name = model_name
        self.timeout_ms = timeout_ms
        self.top_n = top_n
        self._model: CrossEncoder | None = None

    def _get_model(self) -> CrossEncoder:
        if self._model is None:
            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(self, query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
        if not chunks:
            return chunks
        started = time.perf_counter()
        candidates = chunks[: self.top_n]
        pairs = [(query, c.text) for c in candidates]
        scores = self._get_model().predict(pairs, convert_to_numpy=True).tolist()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if elapsed_ms > self.timeout_ms:
            return chunks
        rescored = [(float(score), chunk) for score, chunk in zip(scores, candidates, strict=False)]
        rescored.sort(key=lambda x: (-x[0], x[1].chunk_id))
        reranked = [c.model_copy(update={"score": score}) for score, c in rescored]
        return reranked + chunks[self.top_n :]


def suppress_near_duplicates(chunks: list[RetrievedChunk], threshold: float) -> list[RetrievedChunk]:
    seen: set[str] = set()
    out: list[RetrievedChunk] = []
    for chunk in chunks:
        signature = " ".join(chunk.text.lower().split()[:32])
        if signature in seen:
            continue
        if any(_jaccard(signature, sig) >= threshold for sig in seen):
            continue
        seen.add(signature)
        out.append(chunk)
    return out


def _jaccard(a: str, b: str) -> float:
    aset = set(a.split())
    bset = set(b.split())
    if not aset or not bset:
        return 0.0
    return len(aset & bset) / len(aset | bset)
