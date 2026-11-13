"""job queue columns (retry, lock, log) and worker heartbeats, for the background worker

Revision ID: 010
Revises: 009
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ingest_jobs", sa.Column("run_after", sa.DateTime(timezone=True)))
    op.add_column("ingest_jobs", sa.Column("locked_by", sa.String(60)))
    op.add_column("ingest_jobs", sa.Column("locked_at", sa.DateTime(timezone=True)))
    op.add_column("ingest_jobs", sa.Column("max_attempts", sa.Integer, nullable=False, server_default="3"))
    op.add_column("ingest_jobs", sa.Column("log", postgresql.JSONB, nullable=False, server_default="[]"))
    op.create_table(
        "worker_heartbeats",
        sa.Column("name", sa.String(60), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.String(40), nullable=False, server_default=""),
        sa.Column("stats", postgresql.JSONB, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("worker_heartbeats")
    for c in ("log", "max_attempts", "locked_at", "locked_by", "run_after"):
        op.drop_column("ingest_jobs", c)
