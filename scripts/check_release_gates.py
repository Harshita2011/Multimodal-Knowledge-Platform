import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Check retrieval release gates from evaluation report JSON")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    report = json.loads(Path(args.report).read_text(encoding="utf-8"))
    m = report.get("metrics", {})
    failures: list[str] = []
    if m.get("recall_at_10", 0.0) < 0.85:
        failures.append("Recall@10 < 0.85")
    if m.get("mrr", 0.0) < 0.70:
        failures.append("MRR < 0.70")
    if m.get("citation_coverage", 0.0) < 0.95:
        failures.append("Citation Accuracy < 0.95")
    if m.get("grounding_score", 0.0) < 0.90:
        failures.append("Grounding Score < 0.90")
    if m.get("p95_latency_ms", 0.0) > 4000:
        failures.append("P95 latency > 4s")

    if failures:
        print(json.dumps({"status": "fail", "failures": failures}, indent=2))
        sys.exit(1)
    print(json.dumps({"status": "pass"}, indent=2))


if __name__ == "__main__":
    main()
