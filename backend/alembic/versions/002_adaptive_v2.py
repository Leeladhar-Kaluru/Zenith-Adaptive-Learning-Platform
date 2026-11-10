"""adaptive v2: concept levels, interaction events, generated items

Revision ID: 002
Revises: 001
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None

KINDS = ("lesson_open", "section_view", "dwell", "hint_open", "answer_change", "sim_change", "sim_reset", "skip", "tutor_open")
STATUS = ("draft", "in_review", "changes_requested", "approved", "published", "archived")


def upgrade() -> None:
    op.create_table(
        "concept_levels",
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("concept_id", sa.String(120), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("streak_up", sa.Integer(), nullable=False),
        sa.Column("streak_down", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("level between 1 and 5", name="ck_level_range"),
        sa.ForeignKeyConstraint(["student_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["concept_id"], ["concepts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("student_id", "concept_id"),
    )
    op.create_table(
        "interaction_events",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("student_id", sa.UUID(), nullable=False),
        sa.Column("client_event_id", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("target_id", sa.String(120), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ms", sa.Integer(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("kind in (" + ",".join(f"'{k}'" for k in KINDS) + ")", name="ck_interaction_kind"),
        sa.ForeignKeyConstraint(["student_id"], ["profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("student_id", "client_event_id", name="uq_interaction_client_event"),
    )
    op.create_index("ix_interaction_student_time", "interaction_events", ["student_id", "occurred_at"])
    op.create_index("ix_interaction_target", "interaction_events", ["student_id", "target_id"])
    for col, typ in (("template_id", sa.String(60)), ("template_version", sa.Integer()), ("template_seed", sa.Integer()), ("level", sa.Integer())):
        op.add_column("items", sa.Column(col, typ, nullable=True))
    op.create_check_constraint("ck_item_level", "items", "level is null or level between 1 and 5")
    op.create_index("uq_item_generated", "items", ["template_id", "template_version", "template_seed", "level"], unique=True,
                    postgresql_where=sa.text("origin = 'generated'"))
    op.drop_constraint("ck_item_status", "items", type_="check")
    op.create_check_constraint("ck_item_status", "items", "status in (" + ",".join(f"'{s}'" for s in STATUS) + ",'generated')")
    op.execute("""
        DO $$ DECLARE t text; BEGIN
          FOREACH t IN ARRAY ARRAY['concept_levels','interaction_events'] LOOP
            EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY', current_schema(), t);
          END LOOP;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
            EXECUTE format('REVOKE ALL ON TABLE %I.concept_levels, %I.interaction_events FROM anon', current_schema(), current_schema());
          END IF;
          IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
            EXECUTE format('REVOKE ALL ON TABLE %I.concept_levels, %I.interaction_events FROM authenticated', current_schema(), current_schema());
          END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_constraint("ck_item_status", "items", type_="check")
    op.create_check_constraint("ck_item_status", "items", "status in (" + ",".join(f"'{s}'" for s in STATUS) + ")")
    op.drop_index("uq_item_generated", table_name="items")
    op.drop_constraint("ck_item_level", "items", type_="check")
    for col in ("level", "template_seed", "template_version", "template_id"):
        op.drop_column("items", col)
    op.drop_table("interaction_events")
    op.drop_table("concept_levels")
