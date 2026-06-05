import argparse
import json
import time
from pathlib import Path

from app.core.settings import get_settings
from app.rag.citation_mapper import CitationMapper
from app.rag.evaluation import citation_coverage, mean_reciprocal_rank, precision_at_k, recall_at_k
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from scripts.evaluate_retrieval import load_dataset
from app.api.dependencies import get_embedding_service, get_vector_repository
from app.rag.retriever import Retriever


def generate_report(cases: list[dict], k_override: int | None = None) -> dict:
    settings = get_settings()
    retriever = Retriever(
        embeddings=get_embedding_service(),
        vectors=get_vector_repository(),
        min_score_threshold=settings.min_retrieval_score,
        enable_reranking=settings.enable_reranking,
        rerank_top_n=settings.rerank_top_n,
        duplicate_threshold=settings.duplicate_similarity_threshold,
        enable_diversity=settings.enable_diversity_retrieval,
        diversity_lambda=settings.diversity_lambda,
        reranker_model_name=settings.reranker_model_name,
        reranker_timeout_ms=settings.reranker_max_latency_ms,
    )
    mapper = CitationMapper()

    p, r, mrr, cov, lat, tokens, dup_rates = [], [], [], [], [], [], []

    for case in cases:
        k = k_override or int(case.get("k", 5))
        t0 = time.perf_counter()
        chunks, stats = retriever.retrieve_with_stats(
            case["query"],
            top_k=k,
            document_filter=case.get("document_filter"),
            user_scope=BENCHMARK_RETRIEVAL_USER_ID,
            workspace_scope=BENCHMARK_RETRIEVAL_USER_ID,
        )
        elapsed_ms = int((time.perf_counter() - t0) * 1000)
        lat.append(elapsed_ms)

        expected_ids = set(case.get("expected_chunk_ids", []))
        if case.get("expected_pages") and not expected_ids:
            expected_pages = set(case.get("expected_pages", []))
            expected_ids = {c.chunk_id for c in chunks if c.metadata.page_number in expected_pages}

        citations = mapper.map(chunks, query=case["query"])
        cited = {c.chunk_id for c in citations}

        p.append(precision_at_k(chunks, expected_ids, k))
        r.append(recall_at_k({c.chunk_id for c in chunks}, expected_ids))
        mrr.append(mean_reciprocal_rank(chunks, expected_ids))
        cov.append(citation_coverage(chunks, cited))
        tokens.append(sum(len(c.text.split()) for c in chunks))
        dup_rates.append(stats.duplicate_suppression_rate)

    n = max(1, len(cases))
    return {
        "metrics": {
            "precision_at_k": sum(p) / n,
            "recall_at_k": sum(r) / n,
            "mrr": sum(mrr) / n,
            "citation_coverage": sum(cov) / n,
            "average_latency_ms": sum(lat) / n,
            "average_context_tokens": sum(tokens) / n,
            "duplicate_suppression_rate": sum(dup_rates) / n,
        },
        "dataset_size": len(cases),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate retrieval quality report")
    parser.add_argument("--dataset", default="tests/evaluation/retrieval_eval_dataset.json")
    parser.add_argument("--k", type=int, default=None)
    parser.add_argument("--output-json", action="store_true")
    parser.add_argument("--output-markdown", action="store_true")
    args = parser.parse_args()

    report = generate_report(load_dataset(Path(args.dataset)), args.k)
    if args.output_json:
        print(json.dumps(report, indent=2))
    if args.output_markdown:
        print("# Retrieval Quality Report")
        for key, value in report["metrics"].items():
            print(f"- {key}: {value:.4f}")
    if not args.output_json and not args.output_markdown:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
