"""web vitals, and (added by later tasks) source provenance

Revision ID: 004
Revises: 003
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None

VITALS = ("LCP", "INP", "CLS", "TTFB", "FCP")


def _rls(*tables: str) -> None:
    names = ",".join(f"'{t}'" for t in tables)
    op.execute(f"""
        DO $$ DECLARE t text; BEGIN
          FOREACH t IN ARRAY ARRAY[{names}] LOOP
            EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', current_schema(), t);
          END LOOP;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            FOREACH t IN ARRAY ARRAY[{names}] LOOP
              EXECUTE format('REVOKE ALL ON TABLE %I.%I FROM anon', current_schema(), t);
            END LOOP;
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            FOREACH t IN ARRAY ARRAY[{names}] LOOP
              EXECUTE format('REVOKE ALL ON TABLE %I.%I FROM authenticated', current_schema(), t);
            END LOOP;
          END IF;
        END $$;
    """)


def upgrade() -> None:
    op.create_table(
        "web_vitals",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(6), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("route", sa.String(80), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("name in (" + ",".join(f"'{n}'" for n in VITALS) + ")", name="ck_vital_name"),
        sa.CheckConstraint("value >= 0 and value <= 600000", name="ck_vital_value"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vital_route_name", "web_vitals", ["route", "name"])
    op.create_table(
        "sources",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("homepage", sa.String(300), nullable=False),
        sa.Column("licence_terms_url", sa.String(300), nullable=False, server_default=""),
        sa.Column("api_terms_url", sa.String(300), nullable=False, server_default=""),
        sa.Column("robots_ok", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "source_assets",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("source_id", sa.UUID(), nullable=False),
        sa.Column("external_id", sa.String(300), nullable=False),
        sa.Column("url", sa.String(600), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("licence_id", sa.String(40), nullable=False),
        sa.Column("attribution_text", sa.Text(), nullable=False, server_default=""),
        sa.Column("author", sa.String(300), nullable=False, server_default=""),
        sa.Column("sha256", sa.String(64), nullable=False, server_default=""),
        sa.Column("bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("storage_path", sa.String(300)),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column("status", sa.String(10), nullable=False, server_default="pending"),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recheck_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewer_id", sa.UUID()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_id", "external_id", name="uq_asset_source_external"),
        sa.CheckConstraint("length(licence_id) > 0", name="ck_asset_licence"),
        sa.CheckConstraint("status in ('pending','approved','rejected','retired')", name="ck_asset_status"),
        sa.CheckConstraint("status <> 'approved' or length(attribution_text) > 0", name="ck_asset_attribution"),
    )
    op.create_index("ix_source_assets_source_id", "source_assets", ["source_id"])
    op.create_index("ix_asset_recheck", "source_assets", ["recheck_at"])
    op.create_table(
        "content_provenance",
        sa.Column("lesson_version_id", sa.UUID(), nullable=False),
        sa.Column("asset_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_version_id"], ["lesson_versions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["source_assets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("lesson_version_id", "asset_id"),
    )
    _rls("web_vitals", "sources", "source_assets", "content_provenance")
    # new question kinds: find_error (Mistake Detective)
    op.alter_column("items", "kind", type_=sa.String(24), existing_type=sa.String(12), existing_nullable=False)
    op.drop_constraint("ck_item_kind", "items", type_="check")
    op.create_check_constraint("ck_item_kind", "items", "kind in ('mcq','multi','truefalse','numeric','fill','match','find_error','label_diagram')")


def downgrade() -> None:
    op.execute("DELETE FROM items WHERE kind IN ('find_error','label_diagram')")
    op.drop_constraint("ck_item_kind", "items", type_="check")
    op.create_check_constraint("ck_item_kind", "items", "kind in ('mcq','multi','truefalse','numeric','fill','match')")
    op.alter_column("items", "kind", type_=sa.String(12), existing_type=sa.String(24), existing_nullable=False)
    op.drop_table("content_provenance")
    op.drop_table("source_assets")
    op.drop_table("sources")
    op.drop_table("web_vitals")
