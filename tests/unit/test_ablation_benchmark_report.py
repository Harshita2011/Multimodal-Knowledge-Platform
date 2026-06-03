import importlib.util
from pathlib import Path


def _load_module():
    module_path = Path("scripts/run_ablation_retrieval_benchmark.py")
    spec = importlib.util.spec_from_file_location("run_ablation_retrieval_benchmark", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_top_improvements_empty_when_mrr_does_not_change():
    module = _load_module()

    base_rows = [
        {"query_id": "q1", "query": "alpha", "reciprocal_rank": 0.0},
        {"query_id": "q2", "query": "beta", "reciprocal_rank": 0.0},
    ]
    candidate_rows = [
        {"query_id": "q1", "query": "alpha", "reciprocal_rank": 0.0},
        {"query_id": "q2", "query": "beta", "reciprocal_rank": 0.0},
    ]

    assert module._top_improvements(base_rows, candidate_rows) == []


def test_append_query_section_reports_none_when_empty():
    module = _load_module()

    summary: list[str] = []
    module._append_query_section(summary, "Top Queries Improved by BM25", [])

    assert summary == [
        "\n## Top Queries Improved by BM25",
        "- None detected in this run.",
    ]


def test_has_retrieval_gain_ignores_latency_only_changes():
    module = _load_module()

    assert module._has_retrieval_gain(
        {
            "recall_at_10": 0.0,
            "mrr": 0.0,
            "citation_accuracy": 0.0,
            "p50_latency_ms": -6.0,
            "p95_latency_ms": 4.0,
        }
    ) is False
