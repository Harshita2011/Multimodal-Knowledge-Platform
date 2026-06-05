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
CATEGORY_MAP = {
    "Dense-Dominant": "Vector-dominant",
    "BM25-Dominant": "BM25-dominant",
    "Entity-Dominant": "Entity-dominant",
    "Hybrid-Dominant": "Hybrid-dominant",
    "Multi-Hop": "Multi-hop-dominant",
}
WINNER_EPSILON = 1e-9


def _load_manifest(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _build_diagnostic_sets(manifest: dict, limit_per_category: int) -> dict:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in manifest["queries"]:
        raw_category = row["retrieval_category"]
        if raw_category not in CATEGORY_MAP:
            continue
        grouped[CATEGORY_MAP[raw_category]].append(
            {
                **row,
                "diagnostic_category": CATEGORY_MAP[raw_category],
                "document_filter": row.get("document_filter"),
            }
        )
    queries = []
    for category in sorted(grouped):
        rows = sorted(grouped[category], key=lambda item: (item["query_id"], item["query"]))
        queries.extend(rows[:limit_per_category])
    return {
        "dataset_version": f"{manifest['dataset_version']}-diagnostics",
        "query_count": len(queries),
        "categories": sorted({row["diagnostic_category"] for row in queries}),
        "queries": queries,
    }


def _build_retriever(config: dict, reranking_enabled: bool) -> Retriever:
    settings = get_settings()
    return Retriever(
        embeddings=get_embedding_service(),
        vectors=get_vector_repository(),
        lexical=get_lexical_repository(),
        min_score_threshold=settings.min_retrieval_score,
        enable_reranking=reranking_enabled,
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
    lexical = get_lexical_repository()
    with lexical.engine.begin() as conn:
        rows = conn.execute(
            __import__("sqlalchemy").text("SELECT chunk_id FROM chunks WHERE chunk_id = ANY(:ids)"),
            {"ids": expected_ids},
        ).fetchall()
    matched = {row[0] for row in rows}
    unmatched = set(expected_ids) - matched
    return {
        "expected_chunk_ids_total": len(expected_ids),
        "matched_chunk_ids": len(matched),
        "unmatched_chunk_ids": len(unmatched),
        "coverage": len(matched) / max(1, len(expected_ids)),
        "unmatched_ids_sample": sorted(unmatched)[:20],
    }


def _per_query_score(hit_at_10: float, reciprocal_rank: float) -> float:
    return (0.7 * hit_at_10) + (0.3 * reciprocal_rank)


def _evaluate_mode(mode: str, config: dict, queries: list[dict], reranking_enabled: bool) -> dict:
    retriever = _build_retriever(config, reranking_enabled=reranking_enabled)
    per_query = []
    metric_series = defaultdict(list)
    reranker_fallbacks = 0

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
        hit_at_10 = recall_at_k(set(ids[:10]), expected)
        reciprocal_rank = mean_reciprocal_rank(chunks, expected)
        ndcg = ndcg_at_k(chunks, expected, 20)
        metric_series["recall_at_5"].append(recall_at_k(set(ids[:5]), expected))
        metric_series["recall_at_10"].append(hit_at_10)
        metric_series["recall_at_20"].append(recall_at_k(set(ids[:20]), expected))
        metric_series["mrr"].append(reciprocal_rank)
        metric_series["ndcg"].append(ndcg)
        metric_series["latency_ms"].append(elapsed)
        if stats.reranker_fallback:
            reranker_fallbacks += 1

        per_query.append(
            {
                "query_id": row["query_id"],
                "query": row["query"],
                "diagnostic_category": row["diagnostic_category"],
                "expected_strategy": row["expected_strategy"],
                "gold_chunk_ids": row["gold_chunk_ids"],
                "gold_document_ids": row["gold_document_ids"],
                "latency_ms": round(elapsed, 3),
                "hit_at_10": round(hit_at_10, 6),
                "reciprocal_rank": round(reciprocal_rank, 6),
                "ndcg": round(ndcg, 6),
                "score": round(_per_query_score(hit_at_10, reciprocal_rank), 6),
                "reranker_fallback": bool(stats.reranker_fallback),
                "retrieved": [
                    {
                        "rank": index + 1,
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.metadata.document_id,
                    }
                    for index, chunk in enumerate(chunks[:10])
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
        "p50_latency_ms": statistics.median(latencies),
        "p95_latency_ms": sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)],
        "avg_query_score": sum(row["score"] for row in per_query) / len(per_query),
        "reranker_fallback_rate": reranker_fallbacks / len(queries),
    }
    return {"mode": mode, "metrics": metrics, "per_query": per_query}


def _pct(new: float, old: float) -> float:
    if old == 0:
        return 0.0 if new == 0 else 100.0
    return ((new - old) / old) * 100.0


def _group_rows_by_category(rows: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[row["diagnostic_category"]].append(row)
    return grouped


def _aggregate_rows(rows: list[dict]) -> dict:
    if not rows:
        return {
            "recall_at_10": 0.0,
            "mrr": 0.0,
            "ndcg": 0.0,
            "avg_query_score": 0.0,
            "reranker_fallback_rate": 0.0,
        }
    return {
        "recall_at_10": sum(float(row["hit_at_10"]) for row in rows) / len(rows),
        "mrr": sum(float(row["reciprocal_rank"]) for row in rows) / len(rows),
        "ndcg": sum(float(row["ndcg"]) for row in rows) / len(rows),
        "avg_query_score": sum(float(row["score"]) for row in rows) / len(rows),
        "reranker_fallback_rate": sum(1.0 if row["reranker_fallback"] else 0.0 for row in rows) / len(rows),
    }


def _category_metrics(results: dict[str, dict]) -> dict:
    categories = sorted({row["diagnostic_category"] for result in results.values() for row in result["per_query"]})
    breakdown: dict[str, dict] = {}
    for category in categories:
        breakdown[category] = {}
        for mode, result in results.items():
            grouped = _group_rows_by_category(result["per_query"])
            breakdown[category][mode] = _aggregate_rows(grouped[category])
    return breakdown


def _winner_summary(category_metrics: dict) -> dict:
    winners: dict[str, dict] = {}
    for category, mode_metrics in category_metrics.items():
        base_score = mode_metrics["vector_only"]["avg_query_score"]
        ranked = sorted(
            (
                (
                    mode,
                    metrics["avg_query_score"],
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
            "delta_vs_vector_pct": _pct(best[1], base_score),
        }
    return winners


def _relative_improvements(category_metrics: dict) -> dict:
    output: dict[str, dict] = {}
    for category, mode_metrics in category_metrics.items():
        base = mode_metrics["vector_only"]
        output[category] = {}
        for mode, metrics in mode_metrics.items():
            if mode == "vector_only":
                continue
            output[category][mode] = {
                "score_pct": _pct(metrics["avg_query_score"], base["avg_query_score"]),
                "mrr_pct": _pct(metrics["mrr"], base["mrr"]),
                "recall_at_10_pct": _pct(metrics["recall_at_10"], base["recall_at_10"]),
            }
    return output


def _query_winner_cases(results: dict[str, dict]) -> tuple[dict[str, list[dict]], dict[str, dict]]:
    by_query: dict[str, dict[str, dict]] = defaultdict(dict)
    for mode, result in results.items():
        for row in result["per_query"]:
            by_query[row["query_id"]][mode] = row

    mode_cases = {
        "vector_only": [],
        "vector_bm25": [],
        "vector_entity": [],
        "vector_bm25_entity_rrf": [],
    }
    query_winners: dict[str, dict] = {}
    for query_id, mode_rows in by_query.items():
        ranked = sorted(
            ((mode, float(row["score"]), float(row["reciprocal_rank"]), float(row["hit_at_10"])) for mode, row in mode_rows.items()),
            key=lambda item: (item[1], item[3], item[2]),
            reverse=True,
        )
        best_score = ranked[0][1]
        winners = [mode for mode, score, _, _ in ranked if abs(score - best_score) <= WINNER_EPSILON]
        query_winners[query_id] = {"winners": winners, "ranked": ranked}
        if len(winners) == 1 and winners[0] in mode_cases:
            row = mode_rows[winners[0]]
            mode_cases[winners[0]].append(
                {
                    "query_id": query_id,
                    "query": row["query"],
                    "diagnostic_category": row["diagnostic_category"],
                    "score": row["score"],
                    "mrr": row["reciprocal_rank"],
                    "recall_at_10": row["hit_at_10"],
                }
            )
    for rows in mode_cases.values():
        rows.sort(key=lambda item: (-float(item["score"]), item["query"]))
    return mode_cases, query_winners


def _mode_spread_summary(results: dict[str, dict]) -> dict[str, dict]:
    by_query: dict[str, dict[str, dict]] = defaultdict(dict)
    for mode, result in results.items():
        for row in result["per_query"]:
            by_query[row["query_id"]][mode] = row

    by_category: dict[str, list[dict]] = defaultdict(list)
    for mode_rows in by_query.values():
        any_row = next(iter(mode_rows.values()))
        scores = [float(row["score"]) for row in mode_rows.values()]
        by_category[any_row["diagnostic_category"]].append(
            {
                "query_id": any_row["query_id"],
                "query": any_row["query"],
                "spread": max(scores) - min(scores),
            }
        )

    summary: dict[str, dict] = {}
    for category, rows in by_category.items():
        rows.sort(key=lambda item: (-item["spread"], item["query"]))
        summary[category] = {
            "avg_spread": sum(item["spread"] for item in rows) / len(rows),
            "max_spread": max(item["spread"] for item in rows),
            "top_examples": rows[:5],
        }
    return summary


def _reranking_convergence(pre_winners: dict, post_winners: dict, pre_spread: dict, post_spread: dict, post_results: dict[str, dict]) -> dict:
    by_query_post = {
        row["query_id"]: row
        for result in post_results.values()
        for row in result["per_query"]
        if result["mode"] == "vector_only"
    }
    removed = []
    collapsed = 0
    for query_id, pre in pre_winners.items():
        post = post_winners[query_id]
        pre_unique = pre["winners"][0] if len(pre["winners"]) == 1 else None
        post_unique = post["winners"][0] if len(post["winners"]) == 1 else None
        if pre_unique is not None and pre_unique != "vector_only":
            if post_unique == "vector_only" or len(post["winners"]) > 1:
                collapsed += 1
                post_row = by_query_post.get(query_id)
                if post_row is not None:
                    removed.append(
                        {
                            "query_id": query_id,
                            "query": post_row["query"],
                            "diagnostic_category": post_row["diagnostic_category"],
                            "pre_winner": pre_unique,
                            "post_winners": post["winners"],
                        }
                    )
    avg_pre = sum(item["avg_spread"] for item in pre_spread.values()) / max(1, len(pre_spread))
    avg_post = sum(item["avg_spread"] for item in post_spread.values()) / max(1, len(post_spread))
    return {
        "collapsed_query_count": collapsed,
        "avg_pre_spread": avg_pre,
        "avg_post_spread": avg_post,
        "spread_delta": avg_post - avg_pre,
        "examples": removed[:12],
    }


def _write_report(
    diagnostics_manifest: dict,
    preflight: dict,
    pre_results: dict[str, dict],
    post_results: dict[str, dict],
    pre_winners: dict,
    post_winners: dict,
    pre_improvements: dict,
    post_improvements: dict,
    cases_pre: dict,
    cases_post: dict,
    pre_spread: dict,
    post_spread: dict,
    convergence: dict,
) -> None:
    lines = [
        "# Retrieval Diagnostics",
        "",
        f"- Dataset version: `{diagnostics_manifest['dataset_version']}`",
        f"- Queries evaluated: {diagnostics_manifest['query_count']}",
        f"- Categories: {', '.join(diagnostics_manifest['categories'])}",
        f"- Preflight coverage: {preflight['coverage']:.2%}",
        "",
        "## Category Winners Before Reranking",
    ]
    for category, winner in pre_winners.items():
        lines.append(
            f"- {category}: {winner['label']} | score={winner['score']:.4f} | "
            f"mrr={winner['mrr']:.4f} | recall@10={winner['recall_at_10']:.4f} | "
            f"delta_vs_vector={winner['delta_vs_vector_pct']:.2f}%"
        )
    lines.append("\n## Category Winners After Reranking")
    for category, winner in post_winners.items():
        lines.append(
            f"- {category}: {winner['label']} | score={winner['score']:.4f} | "
            f"mrr={winner['mrr']:.4f} | recall@10={winner['recall_at_10']:.4f} | "
            f"delta_vs_vector={winner['delta_vs_vector_pct']:.2f}%"
        )
    lines.append("\n## Relative Improvements Before Reranking")
    for category, improvements in pre_improvements.items():
        lines.append(f"\n### {category}")
        for mode, metrics in improvements.items():
            lines.append(
                f"- {MODE_LABELS[mode]}: score={metrics['score_pct']:.2f}% | "
                f"mrr={metrics['mrr_pct']:.2f}% | recall@10={metrics['recall_at_10_pct']:.2f}%"
            )
    lines.append("\n## Relative Improvements After Reranking")
    for category, improvements in post_improvements.items():
        lines.append(f"\n### {category}")
        for mode, metrics in improvements.items():
            lines.append(
                f"- {MODE_LABELS[mode]}: score={metrics['score_pct']:.2f}% | "
                f"mrr={metrics['mrr_pct']:.2f}% | recall@10={metrics['recall_at_10_pct']:.2f}%"
            )
    lines.append("\n## Cases Where Vector-Only Wins")
    if cases_post["vector_only"]:
        for row in cases_post["vector_only"][:10]:
            lines.append(f"- [{row['diagnostic_category']}] {row['query']} | score={row['score']}")
    else:
        lines.append("- None.")
    lines.append("\n## Cases Where BM25 Wins")
    if cases_post["vector_bm25"]:
        for row in cases_post["vector_bm25"][:10]:
            lines.append(f"- [{row['diagnostic_category']}] {row['query']} | score={row['score']}")
    else:
        lines.append("- None.")
    lines.append("\n## Cases Where Entity Retrieval Wins")
    if cases_post["vector_entity"]:
        for row in cases_post["vector_entity"][:10]:
            lines.append(f"- [{row['diagnostic_category']}] {row['query']} | score={row['score']}")
    else:
        lines.append("- None.")
    lines.append("\n## Cases Where RRF Wins")
    if cases_post["vector_bm25_entity_rrf"]:
        for row in cases_post["vector_bm25_entity_rrf"][:10]:
            lines.append(f"- [{row['diagnostic_category']}] {row['query']} | score={row['score']}")
    else:
        lines.append("- None.")
    lines.append("\n## Reranking Convergence")
    lines.append(f"- average_spread_before_rerank: {convergence['avg_pre_spread']:.4f}")
    lines.append(f"- average_spread_after_rerank: {convergence['avg_post_spread']:.4f}")
    lines.append(f"- spread_delta_after_minus_before: {convergence['spread_delta']:.4f}")
    lines.append(f"- collapsed_non_vector_wins: {convergence['collapsed_query_count']}")
    lines.append("\n## Cases Where Reranking Removes Differences")
    if convergence["examples"]:
        for row in convergence["examples"]:
            lines.append(
                f"- [{row['diagnostic_category']}] {row['query']} | pre={row['pre_winner']} | post={row['post_winners']}"
            )
    else:
        lines.append("- None detected.")
    lines.append("\n## Category Spread Before Reranking")
    for category, summary in pre_spread.items():
        lines.append(f"- {category}: avg_spread={summary['avg_spread']:.4f}, max_spread={summary['max_spread']:.4f}")
    lines.append("\n## Category Spread After Reranking")
    for category, summary in post_spread.items():
        lines.append(f"- {category}: avg_spread={summary['avg_spread']:.4f}, max_spread={summary['max_spread']:.4f}")
    lines.append("\n## Reranker Fallback Rate")
    post_vector = post_results["vector_only"]["metrics"]["reranker_fallback_rate"]
    post_bm25 = post_results["vector_bm25"]["metrics"]["reranker_fallback_rate"]
    post_entity = post_results["vector_entity"]["metrics"]["reranker_fallback_rate"]
    post_rrf = post_results["vector_bm25_entity_rrf"]["metrics"]["reranker_fallback_rate"]
    lines.append(f"- Vector Only: {post_vector:.2%}")
    lines.append(f"- Vector + BM25: {post_bm25:.2%}")
    lines.append(f"- Vector + Entity: {post_entity:.2%}")
    lines.append(f"- Vector + BM25 + Entity + RRF: {post_rrf:.2%}")

    Path("reports/retrieval_diagnostics.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run retrieval diagnostics with reranking analysis")
    parser.add_argument("--manifest", default="tests/evaluation/retrieval_stress_manifest.json")
    parser.add_argument("--limit-per-category", type=int, default=20)
    args = parser.parse_args()

    manifest = _load_manifest(Path(args.manifest))
    diagnostics_manifest = _build_diagnostic_sets(manifest, limit_per_category=args.limit_per_category)
    Path("tests/evaluation/retrieval_diagnostics_sets.json").write_text(
        json.dumps(diagnostics_manifest, indent=2), encoding="utf-8"
    )

    preflight = _preflight_validate(diagnostics_manifest["queries"])
    if preflight["unmatched_chunk_ids"] > 0:
        raise RuntimeError(
            "Diagnostics preflight failed: unmatched gold chunk IDs found. "
            f"coverage={preflight['coverage']:.2%}, unmatched={preflight['unmatched_chunk_ids']}"
        )

    pre_results = {}
    post_results = {}
    for mode, config in ABLATIONS:
        pre_results[mode] = _evaluate_mode(mode, config, diagnostics_manifest["queries"], reranking_enabled=False)
        post_results[mode] = _evaluate_mode(mode, config, diagnostics_manifest["queries"], reranking_enabled=True)

    pre_category_metrics = _category_metrics(pre_results)
    post_category_metrics = _category_metrics(post_results)
    pre_winners = _winner_summary(pre_category_metrics)
    post_winners = _winner_summary(post_category_metrics)
    pre_improvements = _relative_improvements(pre_category_metrics)
    post_improvements = _relative_improvements(post_category_metrics)
    cases_pre, pre_query_winners = _query_winner_cases(pre_results)
    cases_post, post_query_winners = _query_winner_cases(post_results)
    pre_spread = _mode_spread_summary(pre_results)
    post_spread = _mode_spread_summary(post_results)
    convergence = _reranking_convergence(pre_query_winners, post_query_winners, pre_spread, post_spread, post_results)

    payload = {
        "dataset_version": diagnostics_manifest["dataset_version"],
        "query_count": diagnostics_manifest["query_count"],
        "preflight": preflight,
        "pre_rerank_results": pre_results,
        "post_rerank_results": post_results,
        "pre_rerank_category_winners": pre_winners,
        "post_rerank_category_winners": post_winners,
        "pre_rerank_relative_improvements": pre_improvements,
        "post_rerank_relative_improvements": post_improvements,
        "convergence": convergence,
    }
    Path("reports/retrieval_diagnostics.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_report(
        diagnostics_manifest,
        preflight,
        pre_results,
        post_results,
        pre_winners,
        post_winners,
        pre_improvements,
        post_improvements,
        cases_pre,
        cases_post,
        pre_spread,
        post_spread,
        convergence,
    )


if __name__ == "__main__":
    main()
