from scripts.analyze_retrieval_thresholds import analyze_thresholds


def test_threshold_analyzer_returns_recommendation(monkeypatch):
    def fake_eval(_cases):
        return {"metrics": {"precision_at_k": 0.8, "recall_at_k": 0.8, "mrr": 0.7, "citation_coverage": 1.0}}

    import scripts.analyze_retrieval_thresholds as mod
    monkeypatch.setattr(mod, "evaluate", lambda cases: fake_eval(cases))
    monkeypatch.setattr(mod, "load_dataset", lambda _path: [{"query": "q"}])

    out = analyze_thresholds(__import__("pathlib").Path("dummy.json"), [0.2, 0.3])
    assert "recommended" in out
