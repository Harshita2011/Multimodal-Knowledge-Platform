import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare baseline and v1.1 benchmark reports")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", default="benchmark_comparison.json")
    args = parser.parse_args()

    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    cand = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    out = {"baseline": base.get("metrics", {}), "candidate": cand.get("metrics", {}), "delta": {}}
    for key, b in out["baseline"].items():
        c = out["candidate"].get(key)
        if isinstance(b, (int, float)) and isinstance(c, (int, float)):
            out["delta"][key] = c - b
    Path(args.output).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
