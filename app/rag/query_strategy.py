from dataclasses import dataclass
import re
from typing import Literal


RetrievalProfileName = Literal["FAST", "BALANCED", "DEEP"]


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
    if answer_mode in {"research_report", "detailed_analysis"} or intent in {"analytical", "comparison", "timeline"}:
        return PROFILES["DEEP"]
    if doc_type in {"research_paper", "contract", "technical_doc"}:
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
