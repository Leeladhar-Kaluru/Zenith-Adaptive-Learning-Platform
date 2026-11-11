"""class announcements

Revision ID: 005
Revises: 004
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("pinned", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_announcements_classroom_id", "announcements", ["classroom_id"])
    # Reached only through the API (which checks class membership). Browsers must never read it directly.
    op.execute("""
        DO $$ BEGIN
          EXECUTE format('ALTER TABLE %I.announcements ENABLE ROW LEVEL SECURITY', current_schema());
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON TABLE %I.announcements FROM anon', current_schema());
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            EXECUTE format('REVOKE ALL ON TABLE %I.announcements FROM authenticated', current_schema());
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_announcements_classroom_id", table_name="announcements")
    op.drop_table("announcements")
