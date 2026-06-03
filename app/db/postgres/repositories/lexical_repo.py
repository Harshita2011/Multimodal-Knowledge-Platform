from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.models.domain.entities import ChunkMetadata, DocumentChunk, RetrievedChunk
from app.rag.text_normalizer import expand_aliases, normalize_query_text, simple_stem


class LexicalPgRepository:
    def __init__(self, engine: Engine):
        self.engine = engine

    def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        with self.engine.begin() as conn:
            for c in chunks:
                md = c.metadata.model_dump(mode="json")
                conn.execute(
                    text(
                        """
                        INSERT INTO chunks
                        (chunk_id, document_id, filename, page_number, text, heading, section_path, doc_type, entities_text, metadata_json, ingestion_timestamp, updated_at)
                        VALUES
                        (:chunk_id, :document_id, :filename, :page_number, :body, :heading, :section_path, :doc_type, :entities_text, CAST(:metadata_json AS jsonb), :ingestion_timestamp, :updated_at)
                        ON CONFLICT (chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        filename = EXCLUDED.filename,
                        page_number = EXCLUDED.page_number,
                        text = EXCLUDED.text,
                        heading = EXCLUDED.heading,
                        section_path = EXCLUDED.section_path,
                        doc_type = EXCLUDED.doc_type,
                        entities_text = EXCLUDED.entities_text,
                        metadata_json = EXCLUDED.metadata_json,
                        updated_at = EXCLUDED.updated_at
                        """
                    ),
                    {
                        "chunk_id": c.chunk_id,
                        "document_id": c.document_id,
                        "filename": c.metadata.filename,
                        "page_number": c.page_number,
                        "body": c.text,
                        "heading": c.metadata.heading,
                        "section_path": c.metadata.section_path,
                        "doc_type": c.metadata.doc_type,
                        "entities_text": ",".join(c.metadata.entities),
                        "metadata_json": __import__("json").dumps(md),
                        "ingestion_timestamp": c.metadata.ingestion_timestamp,
                        "updated_at": datetime.utcnow(),
                    },
                )

            conn.execute(text("DELETE FROM chunk_entities WHERE chunk_id_ref IN (SELECT id FROM chunks WHERE document_id = :doc_id)"), {"doc_id": chunks[0].document_id})
            for c in chunks:
                for raw_entity in c.metadata.entities:
                    norm = normalize_query_text(raw_entity)
                    entity_type = _entity_type(raw_entity)
                    conn.execute(
                        text(
                            """
                            INSERT INTO entities (value, normalized_value, entity_type, created_at)
                            VALUES (:value, :norm, :etype, :created)
                            ON CONFLICT (normalized_value, entity_type) DO UPDATE SET value = EXCLUDED.value
                            """
                        ),
                        {"value": raw_entity, "norm": norm, "etype": entity_type, "created": datetime.utcnow()},
                    )
                    conn.execute(
                        text(
                            """
                            INSERT INTO chunk_entities (chunk_id_ref, entity_id, created_at)
                            SELECT c.id, e.id, :created
                            FROM chunks c, entities e
                            WHERE c.chunk_id = :chunk_id AND e.normalized_value = :norm AND e.entity_type = :etype
                            ON CONFLICT (chunk_id_ref, entity_id) DO NOTHING
                            """
                        ),
                        {"chunk_id": c.chunk_id, "norm": norm, "etype": entity_type, "created": datetime.utcnow()},
                    )

    def delete_document(self, document_id: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("DELETE FROM chunk_entities WHERE chunk_id_ref IN (SELECT id FROM chunks WHERE document_id = :doc_id)"), {"doc_id": document_id})
            conn.execute(text("DELETE FROM chunks WHERE document_id = :doc_id"), {"doc_id": document_id})

    def search_bm25(self, query: str, top_k: int, document_filter: str | None = None) -> list[RetrievedChunk]:
        q = normalize_query_text(query)
        stmt = """
            SELECT chunk_id, document_id, filename, page_number, text, metadata_json,
                   ts_rank_cd(
                     to_tsvector('english', coalesce(text,'') || ' ' || coalesce(heading,'') || ' ' || coalesce(section_path,'') || ' ' || coalesce(entities_text,'')),
                     websearch_to_tsquery('english', :q)
                   ) as score
            FROM chunks
            WHERE (:doc_id IS NULL OR document_id = :doc_id)
              AND (
                to_tsvector('english', coalesce(text,'') || ' ' || coalesce(heading,'') || ' ' || coalesce(section_path,'') || ' ' || coalesce(entities_text,''))
                @@ websearch_to_tsquery('english', :q)
                OR similarity(text, :q) > 0.2
                OR similarity(heading, :q) > 0.2
              )
            ORDER BY score DESC
            LIMIT :k
        """
        with self.engine.begin() as conn:
            rows = conn.execute(text(stmt), {"q": q, "doc_id": document_filter, "k": top_k}).mappings().all()
        return [_row_to_chunk(r, "bm25") for r in rows]

    def search_entities(self, query: str, top_k: int, document_filter: str | None = None) -> tuple[list[RetrievedChunk], list[str]]:
        norm = normalize_query_text(query)
        toks = [simple_stem(t) for t in norm.split() if len(t) >= 2]
        expanded = expand_aliases(toks)
        if not expanded:
            return [], []
        with self.engine.begin() as conn:
            rows = conn.execute(
                text(
                    """
                    SELECT c.chunk_id, c.document_id, c.filename, c.page_number, c.text, c.metadata_json,
                           COUNT(*)::float AS score
                    FROM entities e
                    JOIN chunk_entities ce ON ce.entity_id = e.id
                    JOIN chunks c ON c.id = ce.chunk_id_ref
                    WHERE (:doc_id IS NULL OR c.document_id = :doc_id)
                      AND e.normalized_value = ANY(:terms)
                    GROUP BY c.chunk_id, c.document_id, c.filename, c.page_number, c.text, c.metadata_json
                    ORDER BY score DESC
                    LIMIT :k
                    """
                ),
                {"terms": expanded, "k": top_k, "doc_id": document_filter},
            ).mappings().all()
        return ([_row_to_chunk(r, "entity") for r in rows], expanded)


def _row_to_chunk(row: Any, source: str) -> RetrievedChunk:
    md = row.get("metadata_json", {}) or {}
    chunk_id = row["chunk_id"]
    metadata = ChunkMetadata(
        document_id=row["document_id"],
        filename=row["filename"],
        page_number=int(row["page_number"]),
        chunk_id=chunk_id,
        ingestion_timestamp=datetime.fromisoformat(md.get("ingestion_timestamp")) if md.get("ingestion_timestamp") else datetime.utcnow(),
        source_type=md.get("source_type", "pdf"),
        modality=md.get("modality", "text"),
        doc_type=md.get("doc_type", "general"),
        section_path=md.get("section_path", ""),
        heading=md.get("heading", ""),
        block_type=md.get("block_type", "paragraph"),
        entities=md.get("entities", []),
    )
    score = float(row.get("score") or 0.0)
    if source == "bm25":
        score = score / (1.0 + score)
    return RetrievedChunk(chunk_id=chunk_id, score=max(0.0, min(1.0, score)), metadata=metadata, text=row["text"])


def _entity_type(raw_entity: str) -> str:
    e = raw_entity.lower()
    if any(ch.isdigit() for ch in e):
        return "versions"
    if any(k in e for k in ("inc", "corp", "llc", "ltd")):
        return "organizations"
    if " " in raw_entity and raw_entity[0].isupper():
        return "people"
    if any(k in e for k in ("kubernetes", "python", "javascript", "postgres", "docker", "fastapi", "model")):
        return "technologies"
    return "products"
