from dataclasses import dataclass

from app.models.domain.entities import RetrievedChunk


@dataclass(slots=True)
class RetrievalEvalResult:
    precision_at_k: float
    citation_coverage: float
    avg_latency_ms: float


def precision_at_k(chunks: list[RetrievedChunk], relevant_chunk_ids: set[str], k: int) -> float:
    if k <= 0:
        return 0.0
    top = chunks[:k]
    hits = sum(1 for c in top if c.chunk_id in relevant_chunk_ids)
    return hits / k


def citation_coverage(chunks: list[RetrievedChunk], cited_chunk_ids: set[str]) -> float:
    if not cited_chunk_ids:
        return 1.0
    retrieved = {c.chunk_id for c in chunks}
    return len(retrieved.intersection(cited_chunk_ids)) / len(cited_chunk_ids)


def recall_at_k(retrieved_chunk_ids: set[str], relevant_chunk_ids: set[str]) -> float:
    if not relevant_chunk_ids:
        return 1.0
    return len(retrieved_chunk_ids.intersection(relevant_chunk_ids)) / len(relevant_chunk_ids)


def mean_reciprocal_rank(chunks: list[RetrievedChunk], relevant_chunk_ids: set[str]) -> float:
    if not relevant_chunk_ids:
        return 1.0
    for idx, chunk in enumerate(chunks, start=1):
        if chunk.chunk_id in relevant_chunk_ids:
            return 1.0 / idx
    return 0.0
