import argparse
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.core.settings import get_settings
from scripts.evaluate_retrieval import evaluate, load_dataset


def analyze_thresholds(dataset_path: Path, thresholds: list[float]) -> dict:
    settings = get_settings()
    cases = load_dataset(dataset_path)
    original = settings.min_retrieval_score
    results: list[dict] = []
    for threshold in thresholds:
        settings.min_retrieval_score = threshold
        report = evaluate(cases)
        metrics = report["metrics"]
        results.append({
            "threshold": threshold,
            "precision_at_k": metrics["precision_at_k"],
            "recall_at_k": metrics["recall_at_k"],
            "mrr": metrics["mrr"],
            "citation_coverage": metrics["citation_coverage"],
        })
    settings.min_retrieval_score = original

    recall_floor = settings.threshold_recall_floor
    eligible = [r for r in results if r["recall_at_k"] >= recall_floor]
    recommended = max(eligible or results, key=lambda r: (r["precision_at_k"], r["mrr"], -r["threshold"]))
    return {
        "metadata": {
            "recall_floor": recall_floor,
            "thresholds": thresholds,
            "dataset_size": len(cases),
        },
        "results": results,
        "recommended": recommended,
    }


def write_summary(report: dict, out_md: Path) -> None:
    rec = report["recommended"]
    lines = [
        "# Retrieval Threshold Summary",
        "",
        f"Recall floor: {report['metadata']['recall_floor']}",
        f"Recommended threshold: {rec['threshold']:.2f}",
        f"Precision@K: {rec['precision_at_k']:.4f}",
        f"Recall@K: {rec['recall_at_k']:.4f}",
        f"MRR: {rec['mrr']:.4f}",
        f"Citation Coverage: {rec['citation_coverage']:.4f}",
    ]
    out_md.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate threshold sweep analysis")
    parser.add_argument("--dataset", default="tests/evaluation/retrieval_eval_dataset.json")
    parser.add_argument("--thresholds", default="0.20,0.25,0.30,0.35,0.40,0.45")
    args = parser.parse_args()

    values = [float(v.strip()) for v in args.thresholds.split(",") if v.strip()]
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)

    analysis = analyze_thresholds(Path(args.dataset), values)
    (out_dir / "retrieval_threshold_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    write_summary(analysis, out_dir / "retrieval_threshold_summary.md")


if __name__ == "__main__":
    main()
