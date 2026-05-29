"""security hardening oauth state and session family

Revision ID: 0002_security_hardening
Revises: 0001_initial
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_security_hardening"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("session_family_id", sa.String(36), nullable=True))
    op.add_column("sessions", sa.Column("parent_session_id", sa.String(36), nullable=True))
    op.add_column("sessions", sa.Column("revoked_reason", sa.String(64), nullable=True))
    op.add_column("sessions", sa.Column("ip_address", sa.String(64), nullable=True))
    op.add_column("sessions", sa.Column("device_name", sa.String(255), nullable=True))
    op.create_index("ix_sessions_family", "sessions", ["session_family_id"])
    op.execute("UPDATE sessions SET session_family_id = id WHERE session_family_id IS NULL")

    op.create_table(
        "oauth_states",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("state", sa.String(255), nullable=False),
        sa.Column("nonce", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_oauth_state_state", "oauth_states", ["state"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_oauth_state_state", table_name="oauth_states")
    op.drop_table("oauth_states")
    op.drop_index("ix_sessions_family", table_name="sessions")
    op.drop_column("sessions", "device_name")
    op.drop_column("sessions", "ip_address")
    op.drop_column("sessions", "revoked_reason")
    op.drop_column("sessions", "parent_session_id")
    op.drop_column("sessions", "session_family_id")
