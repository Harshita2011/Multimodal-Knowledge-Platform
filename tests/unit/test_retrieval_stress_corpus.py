import importlib.util
from pathlib import Path


def _load_module(path: str, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(path))
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_stress_manifest_meets_scale_and_categories():
    module = _load_module("scripts/build_retrieval_stress_corpus.py", "build_retrieval_stress_corpus")
    manifest = module.build_manifest()

    assert manifest["document_count"] >= 100
    assert manifest["query_count"] >= 500
    categories = {row["retrieval_category"] for row in manifest["queries"]}
    assert categories == {
        "BM25-Dominant",
        "Dense-Dominant",
        "Entity-Dominant",
        "Hybrid-Dominant",
        "Multi-Hop",
        "Ambiguous Queries",
        "Long Context",
        "Noisy Documents",
    }


def test_similarity_flag_detects_flat_benchmark():
    module = _load_module("scripts/run_retrieval_stress_ablation.py", "run_retrieval_stress_ablation")
    overall = {
        "vector_bm25": {"recall_at_10": 0.5, "mrr": 1.0, "ndcg": 1.2},
        "vector_entity": {"recall_at_10": 0.3, "mrr": 0.4, "ndcg": 0.9},
        "vector_bm25_entity": {"recall_at_10": 0.8, "mrr": 0.5, "ndcg": 1.1},
        "vector_bm25_entity_rrf": {"recall_at_10": 0.2, "mrr": 0.1, "ndcg": 0.6},
    }
    category_breakdown = {
        "BM25-Dominant": {
            "vector_only": {"mrr": 0.50, "recall_at_10": 0.50},
            "vector_bm25": {"mrr": 0.505, "recall_at_10": 0.505},
            "vector_entity": {"mrr": 0.504, "recall_at_10": 0.504},
            "vector_bm25_entity": {"mrr": 0.503, "recall_at_10": 0.503},
            "vector_bm25_entity_rrf": {"mrr": 0.502, "recall_at_10": 0.502},
        }
    }

    flag = module._benchmark_similarity_flag(overall, category_breakdown)

    assert flag["flagged"] is True
