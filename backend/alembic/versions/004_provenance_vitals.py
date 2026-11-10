"""web vitals, and (added by later tasks) source provenance

Revision ID: 004
Revises: 003
"""
import sqlalchemy as sa
from alembic import op

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
    _rls("web_vitals")


def downgrade() -> None:
    op.drop_table("web_vitals")
