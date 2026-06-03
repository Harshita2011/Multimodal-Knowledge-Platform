from datetime import datetime, timezone

from app.models.domain.entities import ChunkMetadata, RetrievedChunk
from app.rag.retrieval_cache import RetrievalCache
from app.rag.rrf import RRFMerger
from app.rag.text_normalizer import expand_aliases, normalize_query_text, simple_stem


def _chunk(cid: str, score: float) -> RetrievedChunk:
    md = ChunkMetadata(document_id="d1", filename="f.pdf", page_number=1, chunk_id=cid, ingestion_timestamp=datetime.now(timezone.utc))
    return RetrievedChunk(chunk_id=cid, score=score, metadata=md, text=f"text {cid}")


def test_rrf_merges_and_traces():
    merged, trace = RRFMerger(k=60).merge({"vector": [_chunk("a", 0.9), _chunk("b", 0.8)], "bm25": [_chunk("b", 0.7)]})
    assert merged[0].chunk_id in {"a", "b"}
    assert "rrf_score" in trace["b"]


def test_cache_put_get_and_invalidate():
    cache = RetrievalCache(ttl_seconds=60, max_entries=10)
    cache.put("q=x|doc=abc", {"ok": True})
    assert cache.get("q=x|doc=abc") == {"ok": True}
    cache.invalidate_document("abc")
    assert cache.get("q=x|doc=abc") is None


def test_normalizer_alias_stem():
    assert normalize_query_text("K8S!! ") == "k8s"
    assert simple_stem("running") == "runn"
    assert "kubernetes" in expand_aliases(["k8s"])
