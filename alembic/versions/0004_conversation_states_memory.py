"""add conversation state memory table

Revision ID: 0004_conversation_states_memory
Revises: 0003_fts_entities_chunks
Create Date: 2026-06-04
"""

from alembic import op

revision = "0004_conversation_states_memory"
down_revision = "0003_fts_entities_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversation_states (
            conversation_id VARCHAR(36) PRIMARY KEY REFERENCES conversations(id),
            active_document_id VARCHAR(64),
            active_chunk_id VARCHAR(128),
            last_clicked_citation JSON,
            last_source_document VARCHAR(255),
            last_retrieval_mode VARCHAR(32),
            last_answer_mode VARCHAR(64),
            updated_at TIMESTAMPTZ NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.drop_table("conversation_states")
