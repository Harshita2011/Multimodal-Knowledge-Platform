from app.rag.query_strategy import (
    ConversationMemory,
    build_query_plan,
    classify_query_intent,
    detect_doc_type,
    expand_queries,
    normalize_answer_mode,
    pick_profile,
)


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


def test_query_plan_rewrites_document_follow_up():
    memory = ConversationMemory(
        active_document_id="doc-1",
        active_chunk_id="doc-1_p5_c0",
        last_clicked_citation={
            "document_id": "doc-1",
            "filename": "Distributed.pdf",
            "page_number": 5,
            "chunk_id": "doc-1_p5_c0",
            "snippet": "Example snippet",
        },
        last_source_document="Distributed.pdf",
    )
    plan = build_query_plan("Explain detailed", memory=memory)
    assert plan.retrieval_mode == "DOCUMENT_MODE"
    assert plan.answer_mode == "DETAILED_EXPLANATION"
    assert "Distributed.pdf" in plan.query
    assert plan.document_filter == "doc-1"


def test_normalize_answer_mode_and_multi_doc_detection():
    assert normalize_answer_mode("executive_summary") == "SUMMARY"
    assert normalize_answer_mode(None, query="compare these documents") == "COMPARISON"
    plan = build_query_plan("compare these documents", memory=None)
    assert plan.retrieval_mode == "MULTI_DOCUMENT_MODE"
    assert plan.answer_mode == "COMPARISON"
