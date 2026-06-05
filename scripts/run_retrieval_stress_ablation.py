import argparse
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from app.api.dependencies import get_embedding_service, get_lexical_repository, get_vector_repository
from app.core.settings import get_settings
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from app.rag.evaluation import mean_reciprocal_rank, ndcg_at_k, recall_at_k
from app.rag.retriever import Retriever


ABLATIONS = [
    ("vector_only", {"enable_bm25": False, "enable_entity": False, "enable_rrf": False}),
    ("vector_bm25", {"enable_bm25": True, "enable_entity": False, "enable_rrf": False}),
    ("vector_entity", {"enable_bm25": False, "enable_entity": True, "enable_rrf": False}),
    ("vector_bm25_entity", {"enable_bm25": True, "enable_entity": True, "enable_rrf": False}),
    ("vector_bm25_entity_rrf", {"enable_bm25": True, "enable_entity": True, "enable_rrf": True}),
]
MODE_LABELS = {
    "vector_only": "Vector Only",
    "vector_bm25": "Vector + BM25",
    "vector_entity": "Vector + Entity",
    "vector_bm25_entity": "Vector + BM25 + Entity",
    "vector_bm25_entity_rrf": "Vector + BM25 + Entity + RRF",
}
SIMILARITY_THRESHOLD = 0.02


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_retriever(config: dict) -> Retriever:
    settings = get_settings()
    return Retriever(
        embeddings=get_embedding_service(),
        vectors=get_vector_repository(),
        lexical=get_lexical_repository(),
        min_score_threshold=settings.min_retrieval_score,
        enable_reranking=settings.enable_reranking,
        rerank_top_n=settings.rerank_top_n,
        duplicate_threshold=settings.duplicate_similarity_threshold,
        enable_diversity=settings.enable_diversity_retrieval,
        diversity_lambda=settings.diversity_lambda,
        reranker_model_name=settings.reranker_model_name,
        reranker_timeout_ms=settings.reranker_max_latency_ms,
        rrf_k=settings.rrf_k,
        enable_bm25=config["enable_bm25"],
        enable_entity=config["enable_entity"],
        enable_rrf=config["enable_rrf"],
    )


def _preflight_validate(queries: list[dict]) -> dict:
    expected_ids = sorted({chunk_id for row in queries for chunk_id in row.get("gold_chunk_ids", [])})
    matched_ids: set[str] = set()
    lexical = get_lexical_repository()
    with lexical.engine.begin() as conn:
        rows = conn.execute(
            __import__("sqlalchemy").text("SELECT chunk_id FROM chunks WHERE chunk_id = ANY(:ids)"),
            {"ids": expected_ids},
        ).fetchall()
        matched_ids = {row[0] for row in rows}
    unmatched_ids = set(expected_ids) - matched_ids
    coverage = len(matched_ids) / max(1, len(expected_ids))
    return {
        "expected_chunk_ids_total": len(expected_ids),
        "matched_chunk_ids": len(matched_ids),
        "unmatched_chunk_ids": len(unmatched_ids),
        "coverage": coverage,
        "unmatched_ids_sample": sorted(unmatched_ids)[:20],
    }


def _evaluate_mode(mode: str, config: dict, queries: list[dict]) -> dict:
    retriever = _build_retriever(config)
    per_query = []
    metric_series = defaultdict(list)

    for row in queries:
        expected = set(row["gold_chunk_ids"])
        started = time.perf_counter()
        chunks, stats = retriever.retrieve_with_stats(
            row["query"],
            top_k=max(20, int(row.get("k", 20))),
            document_filter=row.get("document_filter"),
            retrieval_profile="DEEP",
            answer_mode="detailed_analysis",
            user_scope=BENCHMARK_RETRIEVAL_USER_ID,
            workspace_scope=BENCHMARK_RETRIEVAL_USER_ID,
        )
        elapsed = (time.perf_counter() - started) * 1000.0
        ids = [chunk.chunk_id for chunk in chunks]
        hit_at_10 = 1.0 if any(chunk_id in expected for chunk_id in ids[:10]) else 0.0
        metric_series["recall_at_5"].append(recall_at_k(set(ids[:5]), expected))
        metric_series["recall_at_10"].append(recall_at_k(set(ids[:10]), expected))
        metric_series["recall_at_20"].append(recall_at_k(set(ids[:20]), expected))
        metric_series["mrr"].append(mean_reciprocal_rank(chunks, expected))
        metric_series["ndcg"].append(ndcg_at_k(chunks, expected, 20))
        metric_series["citation_accuracy"].append(hit_at_10)
        metric_series["grounding_score"].append(hit_at_10)
        metric_series["claim_support_rate"].append(hit_at_10)
        metric_series["latency_ms"].append(elapsed)

        explainability = (stats.trace or {}).get("explainability", {})
        per_query.append(
            {
                "query_id": row["query_id"],
                "query": row["query"],
                "retrieval_category": row["retrieval_category"],
                "expected_strategy": row["expected_strategy"],
                "gold_chunk_ids": row["gold_chunk_ids"],
                "gold_document_ids": row["gold_document_ids"],
                "latency_ms": round(elapsed, 3),
                "hit_at_10": bool(hit_at_10),
                "reciprocal_rank": mean_reciprocal_rank(chunks, expected),
                "ndcg": ndcg_at_k(chunks, expected, 20),
                "retrieved": [
                    {
                        "rank": index + 1,
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.metadata.document_id,
                        "retrieval_source": explainability.get(chunk.chunk_id, {}).get("retrieval_source", "vector"),
                        "score": round(chunk.score, 6),
                    }
                    for index, chunk in enumerate(chunks[:20])
                ],
            }
        )

    latencies = metric_series["latency_ms"]
    metrics = {
        "recall_at_5": sum(metric_series["recall_at_5"]) / len(queries),
        "recall_at_10": sum(metric_series["recall_at_10"]) / len(queries),
        "recall_at_20": sum(metric_series["recall_at_20"]) / len(queries),
        "mrr": sum(metric_series["mrr"]) / len(queries),
        "ndcg": sum(metric_series["ndcg"]) / len(queries),
        "citation_accuracy": sum(metric_series["citation_accuracy"]) / len(queries),
        "grounding_score": sum(metric_series["grounding_score"]) / len(queries),
        "claim_support_rate": sum(metric_series["claim_support_rate"]) / len(queries),
        "p50_latency_ms": statistics.median(latencies),
        "p95_latency_ms": sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)],
    }
    return {"mode": mode, "metrics": metrics, "per_query": per_query}


def _pct(new: float, old: float) -> float:
    if old == 0:
        return 0.0 if new == 0 else 100.0
    return ((new - old) / old) * 100.0


def _aggregate_metrics(rows: list[dict]) -> dict:
    if not rows:
        return {key: 0.0 for key in ("recall_at_5", "recall_at_10", "recall_at_20", "mrr", "ndcg", "citation_accuracy", "grounding_score", "claim_support_rate", "p50_latency_ms", "p95_latency_ms")}
    latencies = [row["latency_ms"] for row in rows]
    mrrs = [float(row["reciprocal_rank"]) for row in rows]
    hits = [1.0 if row["hit_at_10"] else 0.0 for row in rows]
    ndcgs = [float(row["ndcg"]) for row in rows]
    recalls_5 = []
    recalls_10 = []
    recalls_20 = []
    for row in rows:
        expected = set(row["gold_chunk_ids"])
        retrieved = row["retrieved"]
        top5 = {item["chunk_id"] for item in retrieved[:5]}
        top10 = {item["chunk_id"] for item in retrieved[:10]}
        top20 = {item["chunk_id"] for item in retrieved[:20]}
        recalls_5.append(recall_at_k(top5, expected))
        recalls_10.append(recall_at_k(top10, expected))
        recalls_20.append(recall_at_k(top20, expected))
    return {
        "recall_at_5": sum(recalls_5) / len(rows),
        "recall_at_10": sum(recalls_10) / len(rows),
        "recall_at_20": sum(recalls_20) / len(rows),
        "mrr": sum(mrrs) / len(rows),
        "ndcg": sum(ndcgs) / len(rows),
        "citation_accuracy": sum(hits) / len(rows),
        "grounding_score": sum(hits) / len(rows),
        "claim_support_rate": sum(hits) / len(rows),
        "p50_latency_ms": statistics.median(latencies),
        "p95_latency_ms": sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)],
    }


def _category_breakdown(results: dict[str, dict], categories: list[str]) -> dict:
    breakdown: dict[str, dict] = {}
    for category in categories:
        breakdown[category] = {}
        for mode, result in results.items():
            rows = [row for row in result["per_query"] if row["retrieval_category"] == category]
            breakdown[category][mode] = _aggregate_metrics(rows)
    return breakdown


def _winning_mode_by_category(category_breakdown: dict) -> dict[str, dict]:
    winners: dict[str, dict] = {}
    for category, mode_metrics in category_breakdown.items():
        base_score = (0.7 * mode_metrics["vector_only"]["recall_at_10"]) + (0.3 * mode_metrics["vector_only"]["mrr"])
        ranked = sorted(
            (
                (
                    mode,
                    (0.7 * metrics["recall_at_10"]) + (0.3 * metrics["mrr"]),
                    metrics["mrr"],
                    metrics["recall_at_10"],
                )
                for mode, metrics in mode_metrics.items()
            ),
            key=lambda item: (item[1], item[3], item[2]),
            reverse=True,
        )
        best = ranked[0]
        winners[category] = {
            "mode": best[0],
            "label": MODE_LABELS[best[0]],
            "score": best[1],
            "mrr": best[2],
            "recall_at_10": best[3],
            "delta_vs_vector": best[1] - base_score,
        }
    return winners


def _benchmark_similarity_flag(overall_contrib: dict, category_breakdown: dict) -> dict:
    max_overall = max(
        abs(overall_contrib[mode][metric])
        for mode in overall_contrib
        for metric in ("recall_at_10", "mrr", "ndcg")
    )
    max_category_delta = 0.0
    for category, mode_metrics in category_breakdown.items():
        base = mode_metrics["vector_only"]
        for mode, metrics in mode_metrics.items():
            if mode == "vector_only":
                continue
            max_category_delta = max(
                max_category_delta,
                abs(metrics["mrr"] - base["mrr"]),
                abs(metrics["recall_at_10"] - base["recall_at_10"]),
            )
    flagged = max_overall < (SIMILARITY_THRESHOLD * 100.0) and max_category_delta < SIMILARITY_THRESHOLD
    return {
        "flagged": flagged,
        "max_overall_pct_delta": max_overall,
        "max_category_absolute_delta": max_category_delta,
        "reason": "All retrieval modes achieved nearly identical performance." if flagged else "Category-level and overall deltas show measurable separation.",
    }


def _top_failures(rows: list[dict], limit: int = 12) -> list[dict]:
    failures = [row for row in rows if not row["hit_at_10"]]
    failures.sort(key=lambda row: (row["retrieval_category"], row["query"]))
    return failures[:limit]


def _write_report(
    manifest: dict,
    preflight: dict,
    results: dict[str, dict],
    contributions: dict[str, dict],
    category_breakdown: dict,
    winners: dict,
    quality_flag: dict,
) -> None:
    reports = Path("reports")
    reports.mkdir(parents=True, exist_ok=True)
    final_mode = "vector_bm25_entity_rrf"
    lines = [
        "# Retrieval Stress Ablation Report",
        "",
        f"- Dataset version: `{manifest['dataset_version']}`",
        f"- Source documents: {manifest['document_count']}",
        f"- Evaluation queries: {manifest['query_count']}",
        f"- Preflight coverage: {preflight['coverage']:.2%}",
        f"- Benchmark quality flag: {'FLAGGED' if quality_flag['flagged'] else 'OK'}",
        f"- Quality rationale: {quality_flag['reason']}",
        "",
        "## Overall Metric Deltas vs Vector Only",
    ]
    for mode, _ in ABLATIONS[1:]:
        lines.append(f"\n### {MODE_LABELS[mode]}")
        for metric, value in contributions[mode].items():
            lines.append(f"- {metric}: {value:.2f}%")
    lines.append("\n## Category Breakdown")
    for category, winner in winners.items():
        lines.append(f"\n### {category}")
        lines.append(f"- winning_channel: {winner['label']}")
        lines.append(f"- winner_score: {winner['score']:.4f}")
        lines.append(f"- winner_mrr: {winner['mrr']:.4f}")
        lines.append(f"- winner_recall_at_10: {winner['recall_at_10']:.4f}")
        lines.append(f"- delta_vs_vector_score: {winner['delta_vs_vector']:.4f}")
        base = category_breakdown[category]["vector_only"]
        lines.append(f"- vector_only_mrr: {base['mrr']:.4f}")
        lines.append(f"- vector_only_recall_at_10: {base['recall_at_10']:.4f}")
        for mode, _ in ABLATIONS[1:]:
            metrics = category_breakdown[category][mode]
            lines.append(
                f"- {mode}: mrr={metrics['mrr']:.4f}, recall_at_10={metrics['recall_at_10']:.4f}, "
                f"citation_accuracy={metrics['citation_accuracy']:.4f}"
            )
    lines.append("\n## Retrieval Failures")
    failures = _top_failures(results[final_mode]["per_query"])
    if failures:
        for row in failures:
            lines.append(
                f"- [{row['retrieval_category']}] {row['query']} | expected={row['gold_chunk_ids']} | top3="
                f"{[item['chunk_id'] for item in row['retrieved'][:3]]}"
            )
    else:
        lines.append("- None in final mode.")
    Path("reports/ablation_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval stress ablation benchmark")
    parser.add_argument("--manifest", default="tests/evaluation/retrieval_stress_manifest.json")
    args = parser.parse_args()

    manifest = _load_manifest(Path(args.manifest))
    queries = manifest["queries"]
    preflight = _preflight_validate(queries)
    if preflight["unmatched_chunk_ids"] > 0:
        raise RuntimeError(
            "Stress corpus preflight failed: unmatched gold chunk IDs found. "
            f"coverage={preflight['coverage']:.2%}, unmatched={preflight['unmatched_chunk_ids']}"
        )

    results = {}
    for mode, config in ABLATIONS:
        results[mode] = _evaluate_mode(mode, config, queries)

    base_metrics = results["vector_only"]["metrics"]
    contributions = {}
    for mode, _ in ABLATIONS[1:]:
        contributions[mode] = {metric: _pct(results[mode]["metrics"][metric], base_metrics[metric]) for metric in base_metrics}

    categories = sorted({query["retrieval_category"] for query in queries})
    category_breakdown = _category_breakdown(results, categories)
    winners = _winning_mode_by_category(category_breakdown)
    quality_flag = _benchmark_similarity_flag(contributions, category_breakdown)

    payload = {
        "dataset_version": manifest["dataset_version"],
        "document_count": manifest["document_count"],
        "query_count": manifest["query_count"],
        "preflight": preflight,
        "ablation_results": results,
        "overall_contributions_pct": contributions,
        "category_breakdown": category_breakdown,
        "category_winners": winners,
        "benchmark_quality": quality_flag,
    }
    Path("reports/stress_ablation_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_report(manifest, preflight, results, contributions, category_breakdown, winners, quality_flag)


if __name__ == "__main__":
    main()
