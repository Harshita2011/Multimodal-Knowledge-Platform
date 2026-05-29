from pathlib import Path

from scripts.evaluate_retrieval import load_dataset


def test_evaluation_dataset_loads():
    cases = load_dataset(Path("tests/evaluation/retrieval_eval_dataset.json"))
    assert isinstance(cases, list)
    assert "query" in cases[0]
