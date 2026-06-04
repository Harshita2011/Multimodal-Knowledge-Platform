"""allow anonymous document ownership

Revision ID: 0005_documents_user_id_nullable
Revises: 0004_conversation_states_memory
Create Date: 2026-06-04
"""

from alembic import op

revision = "0005_documents_user_id_nullable"
down_revision = "0004_conversation_states_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("documents", "user_id", nullable=True)


def downgrade() -> None:
    op.alter_column("documents", "user_id", nullable=False)
