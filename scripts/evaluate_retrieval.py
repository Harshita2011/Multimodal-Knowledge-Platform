import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.api.dependencies import get_embedding_service, get_vector_repository
from app.core.settings import get_settings
from app.rag.citation_mapper import CitationMapper
from app.rag.evaluation import citation_coverage, mean_reciprocal_rank, precision_at_k, recall_at_k
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
    r_scores: list[float] = []
    rr_scores: list[float] = []
    c_scores: list[float] = []

    for case in cases:
        k = k_override or int(case.get("k", 5))
        chunks = retriever.retrieve(case["query"], top_k=k, document_filter=case.get("document_filter"))
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
        r_scores.append(recall_at_k(retrieved_ids, expected_ids))
        rr_scores.append(mean_reciprocal_rank(chunks, expected_ids))
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
            "recall_at_k": sum(r_scores) / count,
            "mrr": sum(rr_scores) / count,
            "citation_coverage": sum(c_scores) / count,
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
    print(f"Recall@K: {report['metrics']['recall_at_k']:.2f}")
    print(f"MRR: {report['metrics']['mrr']:.2f}")
    print(f"Citation Coverage: {report['metrics']['citation_coverage']:.2f}")


if __name__ == "__main__":
    main()
