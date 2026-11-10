"""009_zenith_library_rewards_mastery

Revision ID: 009
Revises: 008
Create Date: 2026-11-06 14:30:00.000000

Adds curriculum library support, concept DAG, BKT mastery tracking,
student gamification/rewards, diagnostic sessions, persistent tutor threads,
and content requests. Enforces Row-Level Security (RLS) on all new tables.
"""
from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # 1. Alter learning_paths for Curriculum Library
    # -------------------------------------------------------------------------
    op.add_column(
        "learning_paths",
        sa.Column("is_library", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "learning_paths",
        sa.Column("library_slug", sa.String(120), nullable=True),
    )
    op.add_column(
        "learning_paths",
        sa.Column("library_status", sa.String(50), nullable=False, server_default="draft"),
    )
    op.add_column(
        "learning_paths",
        sa.Column(
            "board_id",
            sa.String(50),
            sa.ForeignKey("curriculum_boards.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_learning_paths_library_slug",
        "learning_paths",
        ["library_slug"],
        unique=True,
        postgresql_where=sa.text("is_library IS TRUE"),
    )

    # -------------------------------------------------------------------------
    # 2. Concepts & Curriculum DAG Tables
    # -------------------------------------------------------------------------
    op.create_table(
        "concepts",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("slug", sa.String(120), unique=True, nullable=False, index=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("grade", sa.Integer(), nullable=False, index=True),
        sa.Column(
            "subject_id",
            sa.String(50),
            sa.ForeignKey("subjects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("keywords", sa.JSON(), nullable=True),
        sa.Column("p_l0", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("p_t", sa.Float(), nullable=False, server_default="0.15"),
        sa.Column("p_g", sa.Float(), nullable=False, server_default="0.20"),
        sa.Column("p_s", sa.Float(), nullable=False, server_default="0.10"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "concept_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "from_concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "to_concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("relationship", sa.String(50), nullable=False, server_default="prerequisite"),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("from_concept_id", "to_concept_id", name="uq_concept_edge_from_to"),
    )

    op.create_table(
        "concept_chapters",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("chapter_order", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("concept_id", "path_id", name="uq_concept_chapter_concept_path"),
    )

    # -------------------------------------------------------------------------
    # 3. Student Enrollment & Resource Progress
    # -------------------------------------------------------------------------
    op.create_table(
        "library_enrollments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.UniqueConstraint("student_id", "path_id", name="uq_library_enrollment_student_path"),
    )

    op.create_table(
        "resource_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "path_lesson_id",
            UUID(as_uuid=True),
            sa.ForeignKey("path_lessons.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="not_started"),
        sa.Column("completion_pct", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("time_spent_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_position_json", sa.JSON(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("student_id", "path_lesson_id", name="uq_resource_progress_student_lesson"),
    )

    # -------------------------------------------------------------------------
    # 4. Bayesian Knowledge Tracing (BKT) Tables
    # -------------------------------------------------------------------------
    op.create_table(
        "bkt_states",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("p_know", sa.Float(), nullable=False, server_default="0.25"),
        sa.Column("total_opportunities", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mastery_band", sa.String(50), nullable=False, server_default="not_enough_evidence"),
        sa.Column("is_gap", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("gap_signal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("student_id", "concept_id", name="uq_bkt_state_student_concept"),
    )

    op.create_table(
        "bkt_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("opportunity_number", sa.Integer(), nullable=False),
        sa.Column("correct", sa.Boolean(), nullable=False),
        sa.Column("prior_p_know", sa.Float(), nullable=False),
        sa.Column("post_p_know", sa.Float(), nullable=False),
        sa.Column("attempt_id", UUID(as_uuid=True), nullable=True),
        sa.Column("hint_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -------------------------------------------------------------------------
    # 5. Gamification, Streaks, XP & Badges
    # -------------------------------------------------------------------------
    op.create_table(
        "student_rewards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), unique=True, nullable=False, index=True),
        sa.Column("total_xp", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("zenith_coins", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("current_level", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("current_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_active_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "reward_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("xp_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("coins_awarded", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("idempotency_key", sa.String(150), unique=True, nullable=False, index=True),
        sa.Column("meta_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon_url", sa.String(300), nullable=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("criteria_json", sa.JSON(), nullable=False),
        sa.Column("xp_bonus", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "student_badges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "badge_id",
            sa.String(100),
            sa.ForeignKey("badges.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("awarded_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("idempotency_key", sa.String(150), unique=True, nullable=False),
        sa.UniqueConstraint("student_id", "badge_id", name="uq_student_badge_student_badge"),
    )

    # -------------------------------------------------------------------------
    # 6. Adaptive Diagnostics
    # -------------------------------------------------------------------------
    op.create_table(
        "diagnostic_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.String(50), nullable=False, server_default="in_progress"),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_pct", sa.Float(), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "diagnostic_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            UUID(as_uuid=True),
            sa.ForeignKey("diagnostic_sessions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("item_index", sa.Integer(), nullable=False),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("is_prerequisite_probe", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("question_json", sa.JSON(), nullable=False),
        sa.Column("student_response", sa.JSON(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -------------------------------------------------------------------------
    # 7. Grounded Tutor Threads & Messages
    # -------------------------------------------------------------------------
    op.create_table(
        "tutor_threads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column(
            "path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "concept_id",
            sa.String(100),
            sa.ForeignKey("concepts.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "tutor_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "thread_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tutor_threads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("sender", sa.String(20), nullable=False),  # student | assistant | system
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="delivered"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -------------------------------------------------------------------------
    # 8. Content Requests & Publication Events
    # -------------------------------------------------------------------------
    op.create_table(
        "content_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("subject", sa.String(100), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.Column("topic", sa.String(200), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="submitted"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "library_publication_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "path_id",
            UUID(as_uuid=True),
            sa.ForeignKey("learning_paths.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("publisher_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("version_tag", sa.String(50), nullable=False),
        sa.Column("manifest_hash", sa.String(100), nullable=False),
        sa.Column("changes_summary", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    # -------------------------------------------------------------------------
    # 9. Enable Row-Level Security (RLS) on all 17 new tables
    # -------------------------------------------------------------------------
    # Ensure auth schema stub exists if running outside Supabase
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'auth') THEN
                CREATE SCHEMA auth;
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM pg_proc p JOIN pg_namespace n ON p.pronamespace = n.oid 
                WHERE n.nspname = 'auth' AND p.proname = 'uid'
            ) THEN
                CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS 'SELECT NULL::uuid;';
            END IF;
        END $$;
    """)

    all_tables = [
        "concepts",
        "concept_edges",
        "concept_chapters",
        "library_enrollments",
        "resource_progress",
        "bkt_states",
        "bkt_events",
        "student_rewards",
        "reward_events",
        "badges",
        "student_badges",
        "diagnostic_sessions",
        "diagnostic_items",
        "tutor_threads",
        "tutor_messages",
        "content_requests",
        "library_publication_events",
    ]

    for tbl in all_tables:
        op.execute(f'ALTER TABLE "{tbl}" ENABLE ROW LEVEL SECURITY;')

    # Public catalog read policies
    public_catalog_tables = ["concepts", "concept_edges", "concept_chapters", "badges", "library_publication_events"]
    for tbl in public_catalog_tables:
        op.execute(f"""
            CREATE POLICY {tbl}_read_policy ON "{tbl}"
            FOR SELECT TO authenticated
            USING (true);
        """)

    # Student-isolated policies (student_id direct match, wrapped in SELECT for caching)
    student_owned_tables = [
        "library_enrollments",
        "resource_progress",
        "bkt_states",
        "bkt_events",
        "student_rewards",
        "reward_events",
        "student_badges",
        "diagnostic_sessions",
        "tutor_threads",
        "content_requests",
    ]
    for tbl in student_owned_tables:
        op.execute(f"""
            CREATE POLICY {tbl}_student_policy ON "{tbl}"
            FOR ALL TO authenticated
            USING ((SELECT auth.uid()) = student_id)
            WITH CHECK ((SELECT auth.uid()) = student_id);
        """)

    # Subordinate tables (diagnostic_items and tutor_messages)
    op.execute("""
        CREATE POLICY diagnostic_items_student_policy ON diagnostic_items
        FOR ALL TO authenticated
        USING (EXISTS (
            SELECT 1 FROM diagnostic_sessions
            WHERE diagnostic_sessions.id = diagnostic_items.session_id
              AND diagnostic_sessions.student_id = (SELECT auth.uid())
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM diagnostic_sessions
            WHERE diagnostic_sessions.id = diagnostic_items.session_id
              AND diagnostic_sessions.student_id = (SELECT auth.uid())
        ));
    """)

    op.execute("""
        CREATE POLICY tutor_messages_student_policy ON tutor_messages
        FOR ALL TO authenticated
        USING (EXISTS (
            SELECT 1 FROM tutor_threads
            WHERE tutor_threads.id = tutor_messages.thread_id
              AND tutor_threads.student_id = (SELECT auth.uid())
        ))
        WITH CHECK (EXISTS (
            SELECT 1 FROM tutor_threads
            WHERE tutor_threads.id = tutor_messages.thread_id
              AND tutor_threads.student_id = (SELECT auth.uid())
        ));
    """)


def downgrade() -> None:
    all_tables = [
        "library_publication_events",
        "content_requests",
        "tutor_messages",
        "tutor_threads",
        "diagnostic_items",
        "diagnostic_sessions",
        "student_badges",
        "badges",
        "reward_events",
        "student_rewards",
        "bkt_events",
        "bkt_states",
        "resource_progress",
        "library_enrollments",
        "concept_chapters",
        "concept_edges",
        "concepts",
    ]
    for tbl in all_tables:
        op.drop_table(tbl)

    op.drop_index("ix_learning_paths_library_slug", table_name="learning_paths")
    op.drop_column("learning_paths", "board_id")
    op.drop_column("learning_paths", "library_status")
    op.drop_column("learning_paths", "library_slug")
    op.drop_column("learning_paths", "is_library")
