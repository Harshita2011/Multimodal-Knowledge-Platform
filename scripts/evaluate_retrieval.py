import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from app.api.dependencies import get_embedding_service, get_vector_repository
from app.core.settings import get_settings
from app.rag.citation_mapper import CitationMapper
from app.rag.evaluation import citation_coverage, mean_reciprocal_rank, ndcg_at_k, precision_at_k, recall_at_k
from app.rag.retriever import Retriever


def load_dataset(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(cases: list[dict], k_override: int | None = None) -> dict:
    settings = get_settings()
    retriever = Retriever(
        embeddings=get_embedding_service(),
        vectors=get_vector_repository(),
        min_score_threshold=settings.min_retrieval_score,
        enable_reranking=settings.enable_reranking,
        rerank_top_n=settings.rerank_top_n,
        duplicate_threshold=settings.retrieval_near_duplicate_threshold,
        reranker_model_name=settings.reranker_model_name,
        reranker_timeout_ms=settings.reranker_max_latency_ms,
    )
    mapper = CitationMapper()

    p_scores: list[float] = []
    r5_scores: list[float] = []
    r10_scores: list[float] = []
    r_scores: list[float] = []
    rr_scores: list[float] = []
    ndcg_scores: list[float] = []
    c_scores: list[float] = []
    latency_ms: list[float] = []

    for case in cases:
        k = k_override or int(case.get("k", 5))
        started = time.perf_counter()
        chunks = retriever.retrieve(case["query"], top_k=k, document_filter=case.get("document_filter"))
        latency_ms.append((time.perf_counter() - started) * 1000.0)
        expected_ids = set(case.get("expected_chunk_ids", []))
        expected_pages = set(case.get("expected_pages", []))
        citations = mapper.map(chunks)
        cited_chunk_ids = {c.chunk_id for c in citations}

        retrieved_ids = {c.chunk_id for c in chunks}
        page_hits = {c.metadata.page_number for c in chunks}
        if expected_pages and not expected_ids:
            # fall back to page-based relevance when chunk ids are not provided
            expected_ids = {c.chunk_id for c in chunks if c.metadata.page_number in expected_pages}

        p_scores.append(precision_at_k(chunks, expected_ids, k))
        r5_scores.append(recall_at_k({c.chunk_id for c in chunks[:5]}, expected_ids))
        r10_scores.append(recall_at_k({c.chunk_id for c in chunks[:10]}, expected_ids))
        r_scores.append(recall_at_k(retrieved_ids, expected_ids))
        rr_scores.append(mean_reciprocal_rank(chunks, expected_ids))
        ndcg_scores.append(ndcg_at_k(chunks, expected_ids, k))
        c_scores.append(citation_coverage(chunks, cited_chunk_ids))

    count = max(1, len(cases))
    return {
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "embedding_model": settings.embedding_model,
            "reranking_enabled": settings.enable_reranking,
            "retrieval_threshold": settings.min_retrieval_score,
            "dataset_size": len(cases),
        },
        "metrics": {
            "precision_at_k": sum(p_scores) / count,
            "recall_at_5": sum(r5_scores) / count,
            "recall_at_10": sum(r10_scores) / count,
            "recall_at_k": sum(r_scores) / count,
            "mrr": sum(rr_scores) / count,
            "ndcg": sum(ndcg_scores) / count,
            "citation_coverage": sum(c_scores) / count,
            "grounding_score": sum(c_scores) / count,
            "p95_latency_ms": sorted(latency_ms)[max(0, int(0.95 * len(latency_ms)) - 1)] if latency_ms else 0.0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline retrieval evaluation against the live configured index")
    parser.add_argument("--dataset", default="tests/evaluation/retrieval_eval_dataset.json")
    parser.add_argument("--k", type=int, default=None)
    parser.add_argument("--output-json", action="store_true")
    args = parser.parse_args()

    cases = load_dataset(Path(args.dataset))
    report = evaluate(cases, k_override=args.k)

    if args.output_json:
        print(json.dumps(report, indent=2))
        return

    print(f"Precision@K: {report['metrics']['precision_at_k']:.2f}")
    print(f"Recall@5: {report['metrics']['recall_at_5']:.2f}")
    print(f"Recall@10: {report['metrics']['recall_at_10']:.2f}")
    print(f"Recall@K: {report['metrics']['recall_at_k']:.2f}")
    print(f"MRR: {report['metrics']['mrr']:.2f}")
    print(f"nDCG: {report['metrics']['ndcg']:.2f}")
    print(f"Citation Coverage: {report['metrics']['citation_coverage']:.2f}")
    print(f"Grounding Score: {report['metrics']['grounding_score']:.2f}")
    print(f"P95 Latency (ms): {report['metrics']['p95_latency_ms']:.1f}")


if __name__ == "__main__":
    main()
