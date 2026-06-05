import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from app.rag.citation_mapper import CitationMapper
from app.rag.evaluation import citation_coverage, precision_at_k
from app.rag.retriever import Retriever


class FixtureEmbeddingService:
    def __init__(self, latency_ms: int):
        self.latency_ms = latency_ms

    def embed_query(self, query: str) -> list[float]:
        _ = query
        time.sleep(self.latency_ms / 1000)
        return [0.1, 0.2, 0.3]


class FixtureVectorRepository:
    def __init__(self, chunks: list[RetrievedChunk], latency_ms: int):
        self._chunks = chunks
        self.latency_ms = latency_ms

    def search_similar(
        self,
        query_embedding: list[float],
        top_k: int,
        document_filter: str | None = None,
        user_scope: str | None = None,
        workspace_scope: str | None = None,
    ) -> list[RetrievedChunk]:
        _ = query_embedding
        _ = document_filter, user_scope, workspace_scope
        time.sleep(self.latency_ms / 1000)
        return sorted(self._chunks, key=lambda c: (-c.score, c.chunk_id))[:top_k]


def _to_chunk(item: dict) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="bench_doc",
        filename="fixture.pdf",
        page_number=item["page_number"],
        chunk_id=item["chunk_id"],
        ingestion_timestamp=datetime.now(timezone.utc),
        owner_user_id=BENCHMARK_RETRIEVAL_USER_ID,
        workspace_id=BENCHMARK_RETRIEVAL_USER_ID,
    )
    return RetrievedChunk(
        chunk_id=item["chunk_id"],
        score=float(item["score"]),
        metadata=md,
        text=item["text"],
    )


def _load_cases() -> list[dict]:
    fixture = Path("tests/fixtures/retrieval_benchmark_e2e.json")
    data = json.loads(fixture.read_text(encoding="utf-8"))
    return data["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_retriever_e2e_regression_benchmark(case: dict):
    chunks = [_to_chunk(c) for c in case["chunks"]]
    embedding = FixtureEmbeddingService(latency_ms=case["embedding_latency_ms"])
    vectors = FixtureVectorRepository(chunks=chunks, latency_ms=case["vector_latency_ms"])
    retriever = Retriever(
        embeddings=embedding,
        vectors=vectors,
        min_score_threshold=float(case.get("min_score_threshold", 0.0)),
        enable_reranking=False,
    )

    started = time.perf_counter()
    ranked = retriever.retrieve(
        case["query"],
        top_k=case["top_k"],
        document_filter=case.get("document_filter"),
        user_scope=BENCHMARK_RETRIEVAL_USER_ID,
        workspace_scope=BENCHMARK_RETRIEVAL_USER_ID,
    )
    citations = CitationMapper().map(ranked)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    p_at_k = precision_at_k(ranked, set(case["relevant_chunk_ids"]), case["top_k"])
    coverage = citation_coverage(ranked, set(case["cited_chunk_ids"]))

    assert p_at_k >= case["min_precision_at_k"]
    assert coverage >= case["min_citation_coverage"]
    assert elapsed_ms <= case["max_latency_ms"]
    assert len(citations) > 0
