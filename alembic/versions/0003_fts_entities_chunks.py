"""add chunks lexical index and entity linking

Revision ID: 0003_fts_entities_chunks
Revises: 0002_security_hardening
Create Date: 2026-06-01
"""

from alembic import op
import sqlalchemy as sa

revision = "0003_fts_entities_chunks"
down_revision = "0002_security_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            id SERIAL PRIMARY KEY,
            chunk_id VARCHAR(128) UNIQUE NOT NULL,
            document_id VARCHAR(64) NOT NULL REFERENCES documents(id),
            filename VARCHAR(255) NOT NULL,
            page_number INTEGER NOT NULL,
            text TEXT NOT NULL,
            heading VARCHAR(255) NOT NULL DEFAULT '',
            section_path VARCHAR(512) NOT NULL DEFAULT '',
            doc_type VARCHAR(64) NOT NULL DEFAULT 'general',
            entities_text TEXT NOT NULL DEFAULT '',
            metadata_json JSON NOT NULL DEFAULT '{}',
            ingestion_timestamp TIMESTAMPTZ NOT NULL,
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_document_id ON chunks(document_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_doc_type ON chunks(doc_type)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_heading ON chunks(heading)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_page_number ON chunks(page_number)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS entities (
            id SERIAL PRIMARY KEY,
            value VARCHAR(255) NOT NULL,
            normalized_value VARCHAR(255) NOT NULL,
            entity_type VARCHAR(64) NOT NULL DEFAULT 'technology',
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_entities_normalized_type UNIQUE (normalized_value, entity_type)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_entities_norm ON entities(normalized_value)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chunk_entities (
            id SERIAL PRIMARY KEY,
            chunk_id_ref INTEGER NOT NULL REFERENCES chunks(id),
            entity_id INTEGER NOT NULL REFERENCES entities(id),
            created_at TIMESTAMPTZ NOT NULL,
            CONSTRAINT uq_chunk_entity UNIQUE (chunk_id_ref, entity_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunk_entities_chunk ON chunk_entities(chunk_id_ref)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunk_entities_entity ON chunk_entities(entity_id)")

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunks_tsv
        ON chunks
        USING GIN (
            to_tsvector(
                'english',
                coalesce(text, '') || ' ' || coalesce(heading, '') || ' ' || coalesce(section_path, '') || ' ' || coalesce(entities_text, '')
            )
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_text_trgm ON chunks USING GIN (text gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_chunks_heading_trgm ON chunks USING GIN (heading gin_trgm_ops)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chunks_heading_trgm")
    op.execute("DROP INDEX IF EXISTS ix_chunks_text_trgm")
    op.execute("DROP INDEX IF EXISTS ix_chunks_tsv")
    op.drop_index("ix_chunk_entities_entity", table_name="chunk_entities")
    op.drop_index("ix_chunk_entities_chunk", table_name="chunk_entities")
    op.drop_table("chunk_entities")
    op.drop_index("ix_entities_norm", table_name="entities")
    op.drop_table("entities")
    op.drop_index("ix_chunks_page_number", table_name="chunks")
    op.drop_index("ix_chunks_heading", table_name="chunks")
    op.drop_index("ix_chunks_doc_type", table_name="chunks")
    op.drop_index("ix_chunks_document_id", table_name="chunks")
    op.drop_table("chunks")
