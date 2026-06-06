import json
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.citation_mapper import CitationMapper
from app.rag.evaluation import citation_coverage, precision_at_k


def _to_chunk(item: dict) -> RetrievedChunk:
    md = ChunkMetadata(
        document_id="bench_doc",
        filename="fixture.pdf",
        page_number=item["page_number"],
        chunk_id=item["chunk_id"],
        ingestion_timestamp=datetime.now(UTC),
    )
    return RetrievedChunk(
        chunk_id=item["chunk_id"],
        score=float(item["score"]),
        metadata=md,
        text=item["text"],
    )


def _load_cases() -> list[dict]:
    fixture = Path("tests/fixtures/retrieval_benchmark.json")
    data = json.loads(fixture.read_text(encoding="utf-8"))
    return data["cases"]


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["name"])
def test_retrieval_regression_benchmark(case: dict):
    chunks = [_to_chunk(c) for c in case["chunks"]]

    started = time.perf_counter()
    ranked = sorted(chunks, key=lambda c: (-c.score, c.chunk_id))[: case["top_k"]]
    citations = CitationMapper().map(ranked)
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    p_at_k = precision_at_k(ranked, set(case["relevant_chunk_ids"]), case["top_k"])
    coverage = citation_coverage(ranked, set(case["cited_chunk_ids"]))

    assert p_at_k >= case["min_precision_at_k"]
    assert coverage >= case["min_citation_coverage"]
    assert elapsed_ms <= case["max_latency_ms"]
    assert len(citations) > 0
