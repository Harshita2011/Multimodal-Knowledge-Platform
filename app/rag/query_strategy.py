from dataclasses import dataclass
import re
from typing import Literal


RetrievalProfileName = Literal["FAST", "BALANCED", "DEEP"]
RetrievalMode = Literal["DOCUMENT_MODE", "MULTI_DOCUMENT_MODE", "GLOBAL_MODE"]
AnswerMode = Literal["SUMMARY", "EXPLANATION", "DETAILED_EXPLANATION", "COMPARISON", "RESEARCH", "EXTRACTION"]


@dataclass(slots=True)
class ConversationMemory:
    active_document_id: str | None = None
    active_chunk_id: str | None = None
    last_clicked_citation: dict | None = None
    last_source_document: str | None = None
    last_retrieval_mode: str | None = None
    last_answer_mode: str | None = None


@dataclass(slots=True)
class QueryPlan:
    query: str
    answer_mode: AnswerMode
    retrieval_mode: RetrievalMode
    document_filter: str | None
    active_document_id: str | None
    active_chunk_id: str | None
    source_document: str | None
    rewritten: bool = False
    rewrite_reason: str | None = None


@dataclass(slots=True)
class RetrievalProfile:
    name: RetrievalProfileName
    vector_top_k: int
    bm25_top_k: int
    entity_top_k: int
    rerank_top_k: int


PROFILES: dict[RetrievalProfileName, RetrievalProfile] = {
    "FAST": RetrievalProfile(name="FAST", vector_top_k=20, bm25_top_k=20, entity_top_k=10, rerank_top_k=5),
    "BALANCED": RetrievalProfile(name="BALANCED", vector_top_k=50, bm25_top_k=50, entity_top_k=20, rerank_top_k=10),
    "DEEP": RetrievalProfile(name="DEEP", vector_top_k=100, bm25_top_k=100, entity_top_k=40, rerank_top_k=20),
}

_DOC_TYPE_HINTS: dict[str, tuple[str, ...]] = {
    "research_paper": ("abstract", "method", "results", "conclusion", "references"),
    "contract": ("clause", "obligation", "penalty", "definitions", "liability"),
    "technical_doc": ("api", "endpoint", "parameter", "example", "implementation"),
    "meeting_notes": ("decision", "action item", "next steps", "owner"),
    "presentation": ("slide", "agenda", "key takeaways", "summary"),
}


def classify_query_intent(query: str) -> str:
    q = query.lower()
    if any(k in q for k in ("compare", "difference", "vs", "versus")):
        return "comparison"
    if any(k in q for k in ("summarize", "summary", "overview")):
        return "summarization"
    if any(k in q for k in ("timeline", "when", "before", "after")):
        return "timeline"
    if any(k in q for k in ("why", "reason", "impact", "analyze", "analysis")):
        return "analytical"
    if any(k in q for k in ("cite", "citation", "source")):
        return "citation_lookup"
    return "factual"


def normalize_answer_mode(raw: str | None, query: str | None = None) -> AnswerMode:
    if raw:
        normalized = raw.strip().lower().replace(" ", "_")
        mapping: dict[str, AnswerMode] = {
            "summary": "SUMMARY",
            "summarize": "SUMMARY",
            "executive_summary": "SUMMARY",
            "overview": "SUMMARY",
            "direct": "EXPLANATION",
            "explanation": "EXPLANATION",
            "explain": "EXPLANATION",
            "detailed_analysis": "DETAILED_EXPLANATION",
            "detailed_explanation": "DETAILED_EXPLANATION",
            "research_report": "RESEARCH",
            "research": "RESEARCH",
            "comparison": "COMPARISON",
            "compare": "COMPARISON",
            "extraction": "EXTRACTION",
            "extract": "EXTRACTION",
        }
        if normalized in mapping:
            return mapping[normalized]
    if query:
        q = query.lower()
        if any(k in q for k in ("compare", "difference", "vs", "versus")):
            return "COMPARISON"
        if any(k in q for k in ("summarize", "summary", "overview")):
            return "SUMMARY"
        if any(k in q for k in ("extract", "list", "find", "show me", "what are the")):
            return "EXTRACTION"
        if any(k in q for k in ("research", "across documents", "all documents", "broader")):
            return "RESEARCH"
        if any(k in q for k in ("explain detailed", "go deeper", "in detail", "detailed", "what does this mean", "explain this")):
            return "DETAILED_EXPLANATION"
    return "EXPLANATION"


def detect_retrieval_mode(query: str, answer_mode: AnswerMode, memory: ConversationMemory | None = None) -> RetrievalMode:
    q = query.lower()
    if any(k in q for k in ("compare", "difference", "versus", "across all documents", "across documents", "multiple documents", "all documents")):
        return "MULTI_DOCUMENT_MODE"
    if answer_mode == "COMPARISON" or answer_mode == "RESEARCH":
        return "MULTI_DOCUMENT_MODE" if answer_mode == "COMPARISON" else "GLOBAL_MODE"
    if any(k in q for k in ("explain this", "explain detailed", "what does this mean", "summarize this", "go deeper", "this section", "this paper", "this document")):
        return "DOCUMENT_MODE"
    if memory and (memory.active_document_id or memory.last_clicked_citation or memory.last_source_document):
        if any(k in q for k in ("explain", "summarize", "detail", "deeper", "this", "that section", "the section", "it")):
            return "DOCUMENT_MODE"
    return "GLOBAL_MODE"


def rewrite_follow_up_query(query: str, retrieval_mode: RetrievalMode, memory: ConversationMemory | None = None) -> tuple[str, bool, str | None]:
    if retrieval_mode != "DOCUMENT_MODE" or memory is None:
        return query, False, None
    citation = memory.last_clicked_citation or {}
    document_name = citation.get("filename") or memory.last_source_document
    page = citation.get("page_number")
    chunk_id = citation.get("chunk_id") or memory.active_chunk_id
    if not document_name:
        return query, False, None
    focus = f"{document_name}"
    if page:
        focus += f" page {page}"
    if chunk_id:
        focus += f" ({chunk_id})"
    cleaned = query.strip().rstrip("?")
    if cleaned.lower() in {"explain detailed", "explain this", "summarize this", "what does this mean", "go deeper", "explain"}:
        return f"Explain the section from {focus} in detail.", True, "follow_up_memory"
    if any(k in cleaned.lower() for k in ("explain", "summarize", "detail", "deeper", "mean")):
        return f"{cleaned}. Focus on {focus}.", True, "follow_up_memory"
    return f"{cleaned}. Focus on {focus}.", True, "follow_up_memory"


def build_query_plan(
    query: str,
    *,
    explicit_answer_mode: str | None = None,
    explicit_document_filter: str | None = None,
    memory: ConversationMemory | None = None,
) -> QueryPlan:
    answer_mode = normalize_answer_mode(explicit_answer_mode, query=query)
    retrieval_mode = detect_retrieval_mode(query, answer_mode, memory=memory)
    memory_document_id = None
    if memory:
        memory_document_id = memory.active_document_id or (memory.last_clicked_citation or {}).get("document_id")
    document_filter = explicit_document_filter or (memory_document_id if retrieval_mode == "DOCUMENT_MODE" else None)
    rewritten_query, rewritten, reason = rewrite_follow_up_query(query, retrieval_mode, memory=memory)
    source_document = None
    if memory:
        source_document = memory.last_source_document or (memory.last_clicked_citation or {}).get("filename")
    active_document_id = None
    if memory:
        active_document_id = memory.active_document_id or (memory.last_clicked_citation or {}).get("document_id") or explicit_document_filter
    else:
        active_document_id = explicit_document_filter
    return QueryPlan(
        query=rewritten_query,
        answer_mode=answer_mode,
        retrieval_mode=retrieval_mode,
        document_filter=document_filter,
        active_document_id=active_document_id,
        active_chunk_id=memory.active_chunk_id if memory else None,
        source_document=source_document,
        rewritten=rewritten,
        rewrite_reason=reason,
    )


def detect_doc_type(text: str, filename: str = "") -> str:
    haystack = f"{filename} {text}".lower()
    if any(k in haystack for k in ("abstract", "methodology", "results", "conclusion")):
        return "research_paper"
    if any(k in haystack for k in ("hereinafter", "agreement", "obligation", "penalty", "clause")):
        return "contract"
    if any(k in haystack for k in ("endpoint", "api", "parameter", "request", "response")):
        return "technical_doc"
    if any(k in haystack for k in ("action items", "meeting notes", "attendees", "decisions")):
        return "meeting_notes"
    if filename.lower().endswith(".pptx") or "slide" in haystack:
        return "presentation"
    if any(k in haystack for k in ("education", "skills", "projects", "experience")):
        return "resume"
    return "general"


def pick_profile(intent: str, answer_mode: str | None, doc_type: str | None) -> RetrievalProfile:
    normalized = normalize_answer_mode(answer_mode)
    if normalized in {"RESEARCH", "COMPARISON"} or intent in {"analytical", "comparison", "timeline"}:
        return PROFILES["DEEP"]
    if normalized in {"SUMMARY", "DETAILED_EXPLANATION"} or doc_type in {"research_paper", "contract", "technical_doc"}:
        return PROFILES["BALANCED"]
    return PROFILES["FAST"]


def expand_queries(query: str) -> list[str]:
    terms = {t.lower() for t in re.findall(r"\w+", query) if len(t) >= 3}
    synonyms = {
        "security": ["authentication", "authorization", "access control", "encryption", "compliance"],
        "kubernetes": ["k8s", "cluster", "container orchestration"],
        "api": ["endpoint", "request", "response", "parameters"],
    }
    expanded: set[str] = {query}
    for term in list(terms):
        for syn in synonyms.get(term, []):
            expanded.add(syn)
    expanded.add(" ".join(sorted(terms)))
    return [q for q in expanded if q.strip()]


def heading_bias_score(doc_type: str | None, heading: str | None, section_path: str | None) -> float:
    if not doc_type:
        return 0.0
    hay = f"{heading or ''} {section_path or ''}".lower()
    hints = _DOC_TYPE_HINTS.get(doc_type, ())
    hits = sum(1 for h in hints if h in hay)
    return min(0.2, 0.05 * hits)
