from app.rag.query_strategy import classify_query_intent, detect_doc_type, expand_queries, pick_profile


def test_query_intent_and_profile_selection():
    intent = classify_query_intent("Compare v1 and v2 features")
    profile = pick_profile(intent=intent, answer_mode="detailed_analysis", doc_type="technical_doc")
    assert intent == "comparison"
    assert profile.name == "DEEP"


def test_detect_doc_type_and_expansion():
    doc_type = detect_doc_type("Abstract Methodology Results Conclusion", "paper.pdf")
    expanded = expand_queries("security requirements")
    assert doc_type == "research_paper"
    assert any("authentication" in e for e in expanded)
