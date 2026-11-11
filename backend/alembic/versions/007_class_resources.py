"""class resources: documents and links a teacher shares with a class

Revision ID: 007
Revises: 006
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "class_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("classroom_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="SET NULL")),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("note", sa.String(500), nullable=False, server_default=""),
        sa.Column("url", sa.String(500)),
        sa.Column("attachment", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind in ('file','link')", name="ck_resource_kind"),
    )
    op.create_index("ix_class_resources_classroom_id", "class_resources", ["classroom_id"])
    # Reached only through the API, which checks class membership. Browsers get no direct table access.
    op.execute("""
        DO $$ BEGIN
          EXECUTE format('ALTER TABLE %I.class_resources ENABLE ROW LEVEL SECURITY', current_schema());
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN EXECUTE format('REVOKE ALL ON TABLE %I.class_resources FROM anon', current_schema()); END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN EXECUTE format('REVOKE ALL ON TABLE %I.class_resources FROM authenticated', current_schema()); END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_index("ix_class_resources_classroom_id", table_name="class_resources")
    op.drop_table("class_resources")
