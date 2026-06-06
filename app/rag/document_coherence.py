from collections import defaultdict
from dataclasses import dataclass

from app.models.domain.entities import RetrievedChunk
from app.rag.query_strategy import RetrievalMode


@dataclass(slots=True)
class DocumentCoherenceResult:
    chunks: list[RetrievedChunk]
    document_scores: dict[str, float]
    document_distribution: dict[str, float]
    chunk_distribution: dict[str, int]
    dropped_documents: list[str]
    dropped_chunks: list[str]
    dominant_document_id: str | None


class DocumentCoherenceFilter:
    def __init__(self, min_doc_share: float = 0.2, max_documents: int = 3, within_doc_keep_ratio: float = 0.7):
        self.min_doc_share = min_doc_share
        self.max_documents = max_documents
        self.within_doc_keep_ratio = within_doc_keep_ratio

    def _score_documents(self, chunks: list[RetrievedChunk]) -> dict[str, float]:
        scores: dict[str, float] = defaultdict(float)
        for chunk in chunks:
            scores[chunk.metadata.document_id] += float(chunk.score)
        return dict(scores)

    def filter(
        self,
        chunks: list[RetrievedChunk],
        *,
        retrieval_mode: RetrievalMode,
        active_document_id: str | None = None,
        explicit_document_filter: str | None = None,
        top_k: int | None = None,
        answer_mode: str | None = None,
    ) -> DocumentCoherenceResult:
        if not chunks:
            return DocumentCoherenceResult([], {}, {}, {}, [], [], None)

        grouped: dict[str, list[RetrievedChunk]] = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.metadata.document_id].append(chunk)

        doc_scores = self._score_documents(chunks)
        ordered_docs = sorted(doc_scores.items(), key=lambda item: (-item[1], item[0]))
        dominant_document_id = ordered_docs[0][0] if ordered_docs else None

        if explicit_document_filter and explicit_document_filter in grouped:
            selected_doc_ids = [explicit_document_filter]
            dominant_document_id = explicit_document_filter
        elif retrieval_mode == "DOCUMENT_MODE":
            if active_document_id and active_document_id in grouped:
                selected_doc_ids = [active_document_id]
                dominant_document_id = active_document_id
            else:
                selected_doc_ids = [dominant_document_id] if dominant_document_id else []
        elif retrieval_mode == "MULTI_DOCUMENT_MODE":
            top_score = ordered_docs[0][1] if ordered_docs else 0.0
            threshold = max(self.min_doc_share, top_score * 0.2)
            selected_doc_ids = [doc_id for doc_id, score in ordered_docs if score >= threshold][: self.max_documents]
        else:
            top_score = ordered_docs[0][1] if ordered_docs else 0.0
            threshold = max(self.min_doc_share, top_score * 0.25)
            selected_doc_ids = [doc_id for doc_id, score in ordered_docs if score >= threshold][: self.max_documents]

        selected_doc_ids = [doc_id for doc_id in selected_doc_ids if doc_id in grouped]
        if not selected_doc_ids and dominant_document_id:
            selected_doc_ids = [dominant_document_id]

        kept: list[RetrievedChunk] = []
        dropped_chunks: list[str] = []

        # Determine minimum chunks to preserve based on query type
        keep_min_chunks = 1
        if answer_mode == "DETAILED_EXPLANATION":
            keep_min_chunks = 5
        elif answer_mode in ["SUMMARY", "EXPLANATION"]:
            keep_min_chunks = 3

        for doc_id in selected_doc_ids:
            doc_chunks = sorted(grouped[doc_id], key=lambda c: (-c.score, c.chunk_id))
            if not doc_chunks:
                continue
            top_score = float(doc_chunks[0].score)
            cutoff = max(0.25, top_score * self.within_doc_keep_ratio)
            retained = [chunk for chunk in doc_chunks if float(chunk.score) >= cutoff]

            # Enforce minimum chunk counts
            if len(retained) < keep_min_chunks:
                retained = doc_chunks[:keep_min_chunks]

            if not retained:
                retained = [doc_chunks[0]]
            kept.extend(retained)
            dropped_chunks.extend([chunk.chunk_id for chunk in doc_chunks if chunk not in retained])

        dropped_documents = [doc_id for doc_id in grouped.keys() if doc_id not in selected_doc_ids]
        kept = sorted(kept, key=lambda c: (-c.score, c.chunk_id))
        if top_k is not None and len(kept) > top_k:
            kept = kept[:top_k]

        selected_scores: dict[str, float] = defaultdict(float)
        selected_counts: dict[str, int] = defaultdict(int)
        for chunk in kept:
            selected_scores[chunk.metadata.document_id] += float(chunk.score)
            selected_counts[chunk.metadata.document_id] += 1

        total = sum(selected_scores.values()) or 1.0
        document_distribution = {doc_id: round(score / total, 4) for doc_id, score in sorted(selected_scores.items(), key=lambda item: (-item[1], item[0]))}
        return DocumentCoherenceResult(
            chunks=kept,
            document_scores={doc_id: round(score, 4) for doc_id, score in sorted(selected_scores.items(), key=lambda item: (-item[1], item[0]))},
            document_distribution=document_distribution,
            chunk_distribution=dict(sorted(selected_counts.items(), key=lambda item: (-item[1], item[0]))),
            dropped_documents=sorted(dropped_documents),
            dropped_chunks=sorted(set(dropped_chunks)),
            dominant_document_id=dominant_document_id,
        )
