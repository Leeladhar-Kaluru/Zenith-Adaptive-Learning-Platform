"""content pipeline jobs, lesson drafts and in-app notifications

Revision ID: 009
Revises: 008
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None
UUID = postgresql.UUID(as_uuid=True)
NOW = sa.func.now()


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("user_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.String(300), nullable=False, server_default=""),
        sa.Column("link", sa.String(200)),
        sa.Column("dedupe_key", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("read_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_notifications_user_time", "notifications", ["user_id", "created_at"])
    op.create_index("uq_notification_dedupe", "notifications", ["user_id", "dedupe_key"], unique=True)
    op.create_table(
        "ingest_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("status", sa.String(10), nullable=False, server_default="queued"),
        sa.Column("grade", sa.Integer),
        sa.Column("subject_id", sa.String(30), sa.ForeignKey("subjects.id")),
        sa.Column("concept_id", sa.String(120), sa.ForeignKey("concepts.id", ondelete="SET NULL")),
        sa.Column("topic", sa.String(120)),
        sa.Column("demand", sa.Integer, nullable=False, server_default="1"),
        sa.Column("asset_id", UUID, sa.ForeignKey("source_assets.id", ondelete="SET NULL")),
        sa.Column("result", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("error", sa.String(300)),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind in ('request','import','draft')", name="ck_job_kind"),
        sa.CheckConstraint("status in ('queued','running','done','failed','blocked')", name="ck_job_status"),
    )
    op.create_index("ix_ingest_jobs_status", "ingest_jobs", ["status", "kind"])
    op.create_table(
        "ingest_job_requesters",
        sa.Column("job_id", UUID, sa.ForeignKey("ingest_jobs.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("student_id", UUID, sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
    )
    op.create_table(
        "lesson_drafts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("ingest_jobs.id", ondelete="SET NULL")),
        sa.Column("asset_id", UUID, sa.ForeignKey("source_assets.id", ondelete="SET NULL")),
        sa.Column("grade", sa.Integer, nullable=False),
        sa.Column("subject_id", sa.String(30), sa.ForeignKey("subjects.id"), nullable=False),
        sa.Column("concept_id", sa.String(120), sa.ForeignKey("concepts.id", ondelete="SET NULL")),
        sa.Column("slug", sa.String(80), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("lesson", postgresql.JSONB, nullable=False),
        sa.Column("scorecard", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("score", sa.Float, nullable=False, server_default="0"),
        sa.Column("verdict", sa.String(10), nullable=False, server_default="review"),
        sa.Column("status", sa.String(12), nullable=False, server_default="ready"),
        sa.Column("model", sa.String(60)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=NOW),
        sa.CheckConstraint("verdict in ('review','rejected')", name="ck_draft_verdict"),
        sa.CheckConstraint("status in ('ready','exported','dismissed')", name="ck_draft_status"),
    )


def downgrade() -> None:
    for t in ("lesson_drafts", "ingest_job_requesters", "ingest_jobs", "notifications"):
        op.drop_table(t)
