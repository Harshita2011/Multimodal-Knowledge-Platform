import json
from pathlib import Path

from sqlalchemy import text

from app.api.dependencies import get_embedding_service, get_lexical_repository, get_vector_repository
from app.models.domain.entities import ChunkMetadata, DocumentChunk
from app.rag.scopes import BENCHMARK_RETRIEVAL_USER_ID
from app.utils.time import utc_now


def _load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_owner(engine, now) -> str:
    with engine.begin() as conn:
        owner_id = BENCHMARK_RETRIEVAL_USER_ID
        conn.execute(
            text(
                """
                INSERT INTO users (id, email, name, is_active, created_at, updated_at)
                VALUES (:id, :email, :name, TRUE, :created_at, :updated_at)
                ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = EXCLUDED.updated_at
                """
            ),
            {
                "id": owner_id,
                "email": "retrieval-stress@example.com",
                "name": "Retrieval Stress",
                "created_at": now,
                "updated_at": now,
            },
        )
        return owner_id


def _upsert_document(conn, owner_id: str, document: dict, chunk_count: int, now) -> None:
    conn.execute(
        text(
            """
            INSERT INTO documents (id, user_id, filename, storage_path, status, page_count, chunk_count, deleted_at, created_at, updated_at)
            VALUES (:id, :user_id, :filename, :storage_path, 'ingested', :page_count, :chunk_count, NULL, :created_at, :updated_at)
            ON CONFLICT (id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            filename = EXCLUDED.filename,
            storage_path = EXCLUDED.storage_path,
            status = EXCLUDED.status,
            page_count = EXCLUDED.page_count,
            chunk_count = EXCLUDED.chunk_count,
            deleted_at = NULL,
            updated_at = EXCLUDED.updated_at
            """
        ),
        {
            "id": document["document_id"],
            "user_id": owner_id,
            "filename": document["filename"],
            "storage_path": f"{document['document_id']}_{document['filename']}",
            "page_count": int(document["page_count"]),
            "chunk_count": chunk_count,
            "created_at": now,
            "updated_at": now,
        },
    )


def _to_domain_chunks(document: dict, owner_id: str, now) -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    for raw in document["chunks"]:
        metadata = ChunkMetadata(
            document_id=document["document_id"],
            filename=document["filename"],
            page_number=int(raw["page_number"]),
            chunk_id=raw["chunk_id"],
            ingestion_timestamp=now,
            owner_user_id=owner_id,
            workspace_id=owner_id,
            doc_type=document["doc_type"],
            heading=raw.get("heading", ""),
            section_path=raw.get("section_path", raw.get("heading", "")),
            entities=list(raw.get("entities", [])),
        )
        chunks.append(
            DocumentChunk(
                chunk_id=raw["chunk_id"],
                document_id=document["document_id"],
                page_number=int(raw["page_number"]),
                text=raw["text"],
                metadata=metadata,
            )
        )
    return chunks


def main() -> None:
    manifest = _load_manifest(Path("tests/evaluation/retrieval_stress_manifest.json"))
    embeddings = get_embedding_service()
    vectors = get_vector_repository()
    lexical = get_lexical_repository()
    engine = lexical.engine
    now = utc_now()
    owner_id = _ensure_owner(engine, now)

    all_chunks: list[DocumentChunk] = []
    for document in manifest["documents"]:
        vectors.delete_document(document["document_id"])
        lexical.delete_document(document["document_id"])
        with engine.begin() as conn:
            _upsert_document(conn, owner_id, document, len(document["chunks"]), now)
        all_chunks.extend(_to_domain_chunks(document, owner_id, now))

    lexical.upsert_chunks(all_chunks)
    vector_embeddings = embeddings.embed_texts([chunk.text for chunk in all_chunks])
    vectors.upsert_chunks(all_chunks, vector_embeddings)
    print(f"Seeded {len(manifest['documents'])} documents and {len(all_chunks)} chunks.")


if __name__ == "__main__":
    main()
